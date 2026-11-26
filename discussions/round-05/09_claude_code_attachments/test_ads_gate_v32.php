<?php
// php test_ads_gate_v32.php AdsGate.php - checks for R5-CHATGPT-16/17/18 (move 9), beyond ChatGPT's test_adversarial_08.php.
require $argv[1];
use SonataMerchant\AdsGate;
$d = sys_get_temp_dir().'/g32_'.getmypid(); @mkdir($d); @mkdir($d.'/catalog-state');
$c = ['account_id' => '999000111', 'content_language' => 'sk', 'feed_label' => 'SK', 'state_dir' => $d.'/catalog-state'];
$ctx = ['account_id' => '999000111', 'content_language' => 'sk', 'feed_label' => 'SK', 'channel' => 'ONLINE'];
$now = time(); $n = 0; $fail = 0;
$t = function ($name, $got, $want) use (&$n, &$fail) { $n++; $ok = $got === $want; if (!$ok) { $fail++; } echo ($ok ? 'PASS' : 'FAIL')." $name expected=".json_encode($want).' actual='.json_encode($got)."\n"; };
$reset = function () { foreach (['reg', 'pol', 'stats'] as $p) { $x = new ReflectionProperty(AdsGate::class, $p); $x->setAccessible(true); $x->setValue(null, $p === 'stats' ? [] : null); } };
$put = function ($f, $x) { file_put_contents($f, json_encode($x)); };
$clean = function () use ($d, $reset) { $reset(); foreach (glob($d.'/*') as $f) { if (is_file($f)) { unlink($f); } } };
$reg3 = ['version' => 3, 'generated_at' => gmdate('c', $now), 'context' => $ctx, 'hold' => [], 'review' => [], 'ok' => []];
$pol3 = ['version' => 3, 'generated_at' => gmdate('c', $now), 'context' => $ctx, 'complete' => true, 'products_read' => 1200, 'hold' => (object)[]];
$row = function ($id) { return ['id' => $id, 'main_root_id' => 1965, 'main_category_id' => 1965, 'title' => 'Glass slides', 'product_type' => 'Science', 'link' => 'https://example.invalid/p', 'price' => '25 EUR']; };
$mk = function ($n, $issues = []) { $o = []; for ($i = 0; $i < $n; $i++) { $id = 'P'.$i; $o[] = ['name' => 'accounts/999000111/products/sk~SK~'.$id, 'offerId' => $id, 'feedLabel' => 'SK', 'contentLanguage' => 'sk', 'productStatus' => ['itemLevelIssues' => $issues[$id] ?? []]]; } return $o; };
$client = function ($pages) { return new class($pages) { private $p; private $i = 0; function __construct($p) { $this->p = $p; } function request($u) { return $this->p[min($this->i++, count($this->p) - 1)]; } }; };
$throws = function ($fn) { try { $fn(); return false; } catch (\Throwable $e) { return true; } };
$ID = function ($o) use ($c) { return AdsGate::identity($c, $o); };
$pf = $d.'/ads-policy.json'; $sf = $d.'/ads-policy-holds.json'; $rf = $d.'/ads-review.json';

// R5-16 sticky integrity
$clean(); $put($rf, $reg3); $put($pf, $pol3);
$t('absent sticky (first migration) is allowed', AdsGate::label($row('A'), $c), 'ads_ok');
$clean(); $put($rf, $reg3); $put($pf, $pol3); $put($sf, ['version' => 3, 'generated_at' => gmdate('c'), 'context' => array_merge($ctx, ['feed_label' => 'CZ']), 'hold' => (object)[]]);
$t('sticky of another context -> review', AdsGate::label($row('A'), $c), 'ads_review');
$clean(); $put($rf, $reg3); $put($pf, $pol3); $put($sf, ['version' => 2, 'generated_at' => gmdate('c'), 'hold' => (object)[]]);
$t('sticky v2 -> review', AdsGate::label($row('A'), $c), 'ads_review');
$clean(); $put($rf, $reg3); $put($pf, $pol3); $put($sf, ['version' => 3, 'generated_at' => gmdate('c'), 'context' => $ctx, 'hold' => ['a', 'b']]);
$t('sticky hold as list -> review', AdsGate::label($row('A'), $c), 'ads_review');
$clean(); $put($rf, $reg3); $p = $pol3; $p['hold'] = [$ID('H') => ['x_policy_violation']]; $put($pf, $p); file_put_contents($sf, '{broken');
$t('corrupt sticky: snapshot hold still applies', AdsGate::label($row('H'), $c), 'ads_hold');
$t('corrupt sticky: clean product -> review', AdsGate::label($row('A'), $c), 'ads_review');
$clean(); $put($pf, $pol3); $put($sf, ['version' => 3, 'generated_at' => gmdate('c'), 'context' => array_merge($ctx, ['account_id' => '1']), 'hold' => (object)[]]);
$t('sweep refuses to rebuild a sticky of another context', $throws(function () use ($c, $client, $mk, $now) { AdsGate::policySweep($c, $client([[200, ['products' => $mk(1200)]]]), $now); }), true);
// R5-17 flags with malformed siblings, both orders
foreach ([[['code' => 'x_policy_violation'], 'broken'], ['broken', ['code' => 'x_policy_violation']], [['code' => 'x_policy_violation'], ['code' => '']]] as $k => $issues) {
    $clean(); $put($rf, $reg3); AdsGate::policySweep($c, $client([[200, ['products' => $mk(1200, ['P0' => $issues])]]]), $now); $reset();
    $t("flag kept with malformed sibling, variant $k", AdsGate::label($row('P0'), $c), 'ads_hold');
}
$clean(); $put($rf, $reg3); $put($sf, ['version' => 3, 'generated_at' => gmdate('c'), 'context' => $ctx, 'hold' => [$ID('P1') => ['y_policy_violation']]]);
AdsGate::policySweep($c, $client([[200, ['products' => $mk(1200, ['P1' => ['broken']])]]]), $now); $reset();
$t('clean-but-unverified status does not release a known hold', AdsGate::label($row('P1'), $c), 'ads_hold');
// R5-18 strict boolean binding
$v2 = function () use ($clean, $put, $rf, $pf) { $clean(); $put($rf, ['version' => 2, 'generated_at' => gmdate('c'), 'hold' => [], 'review' => [], 'ok' => []]); $put($pf, ['version' => 2, 'generated_at' => gmdate('c'), 'hold' => (object)[]]); };
foreach (['false', 'true', 1, '1', 'yes'] as $bad) { $v2(); $t('legacy_v2_bind='.json_encode($bad).' rejected', AdsGate::label($row('A'), $c + ['legacy_v2_bind' => $bad]), 'ads_review'); }
$v2(); $t('legacy_v2_bind=true accepted', AdsGate::label($row('A'), $c + ['legacy_v2_bind' => true]), 'ads_ok');

echo ($n - $fail)."/$n PASS\n";
$reset(); foreach (glob($d.'/catalog-state/*') as $f) { unlink($f); } @rmdir($d.'/catalog-state'); foreach (glob($d.'/*') as $f) { is_file($f) && unlink($f); } @rmdir($d);
exit($fail ? 1 : 0);
