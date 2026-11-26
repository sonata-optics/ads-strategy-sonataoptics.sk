<?php
// php test_ads_gate_v31.php AdsGate.php - extra checks for v3.1 (move 7): release proof, migration binding, transaction
// order, previous-snapshot binding for coverage, duplicates hold-wins, unverified products, empty final page.
require $argv[1];
use SonataMerchant\AdsGate;
$d = sys_get_temp_dir().'/g31_'.getmypid(); @mkdir($d); @mkdir($d.'/catalog-state');
$c = ['account_id' => '999000111', 'content_language' => 'sk', 'feed_label' => 'SK', 'state_dir' => $d.'/catalog-state'];
$ctx = ['account_id' => '999000111', 'content_language' => 'sk', 'feed_label' => 'SK', 'channel' => 'ONLINE'];
$now = time(); $n = 0; $fail = 0;
$t = function ($name, $got, $want) use (&$n, &$fail) { $n++; $ok = $got === $want; if (!$ok) { $fail++; } echo ($ok ? 'PASS' : 'FAIL')." $name expected=".json_encode($want).' actual='.json_encode($got)."\n"; };
$reset = function () { foreach (['reg', 'pol', 'stats'] as $p) { $x = new ReflectionProperty(AdsGate::class, $p); $x->setAccessible(true); $x->setValue(null, $p === 'stats' ? [] : null); } };
$put = function ($f, $x) { file_put_contents($f, json_encode($x)); };
$get = function ($f) { return json_decode((string)@file_get_contents($f), true); };
$clean = function () use ($d, $reset) { $reset(); foreach (glob($d.'/*') as $f) { if (is_file($f)) { unlink($f); } } };
$reg3 = ['version' => 3, 'generated_at' => gmdate('c', $now), 'context' => $ctx, 'hold' => [], 'review' => [], 'ok' => []];
$pol3 = ['version' => 3, 'generated_at' => gmdate('c', $now), 'context' => $ctx, 'complete' => true, 'products_read' => 1200, 'hold' => (object)[]];
$row = function ($id) { return ['id' => $id, 'main_root_id' => 1965, 'main_category_id' => 1965, 'title' => 'Glass slides', 'product_type' => 'Science', 'link' => 'https://example.invalid/p', 'price' => '25 EUR']; };
$mk = function ($n, $issues = [], $drop = []) { $o = []; for ($i = 0; $i < $n; $i++) { $id = 'P'.$i; if (in_array($id, $drop, true)) { continue; } $o[] = ['name' => 'accounts/999000111/products/sk~SK~'.$id, 'offerId' => $id, 'feedLabel' => 'SK', 'contentLanguage' => 'sk', 'productStatus' => ['itemLevelIssues' => $issues[$id] ?? []]]; } return $o; };
$client = function ($pages) { return new class($pages) { private $p; private $i = 0; function __construct($p) { $this->p = $p; } function request($u) { return $this->p[min($this->i++, count($this->p) - 1)]; } }; };
$throws = function ($fn) { try { $fn(); return false; } catch (\Throwable $e) { return true; } };
$ID = function ($o) use ($c) { return AdsGate::identity($c, $o); };
$pf = $d.'/ads-policy.json'; $sf = $d.'/ads-policy-holds.json'; $rf = $d.'/ads-review.json';

// 1 migration binding: live v2 register/policy are used only with explicit legacy_v2_bind
$clean(); $put($rf, ['version' => 2, 'generated_at' => gmdate('c'), 'hold' => [], 'review' => [], 'ok' => []]); $put($pf, ['version' => 2, 'generated_at' => gmdate('c'), 'hold' => (object)[]]);
$t('v2 pair without binding -> review', AdsGate::label($row('A'), $c), 'ads_review');
$reset(); $cb = $c + ['legacy_v2_bind' => true];
$t('v2 pair with explicit legacy_v2_bind -> ok', AdsGate::label($row('A'), $cb), 'ads_ok');
$reset(); $put($pf, ['version' => 2, 'generated_at' => gmdate('c'), 'hold' => [$ID('A') => ['x_policy_violation']]]);
$t('v2 hold applies even without binding', AdsGate::label($row('A'), $c), 'ads_hold');
// 2 first v3 sweep after v2: v2 holds migrate into sticky; product seen clean -> released with log; unseen -> kept
$clean(); $put($pf, ['version' => 2, 'generated_at' => gmdate('c', $now - 5 * 86400), 'hold' => [$ID('P1') => ['a_policy_violation'], $ID('ZZ') => ['b_policy_violation']]]);
AdsGate::policySweep($c, $client([[200, ['products' => $mk(1200)]]]), $now);
$st = $get($sf);
$t('migrated v2 hold seen clean is released and logged', [isset($st['hold'][$ID('P1')]), $st['released'][0]['id'] ?? null], [false, $ID('P1')]);
$t('migrated v2 hold not seen is kept', isset($st['hold'][$ID('ZZ')]), true);
// 3 duplicates: one copy flagged, one clean -> hold wins
$clean(); $p = $mk(1200); $p[] = ['name' => 'accounts/999000111/products/sk~SK~P7', 'offerId' => 'P7', 'feedLabel' => 'SK', 'contentLanguage' => 'sk', 'productStatus' => ['itemLevelIssues' => [['code' => 'x_policy_violation', 'severity' => 'DEMOTED']]]];
AdsGate::policySweep($c, $client([[200, ['products' => $p]]]), $now);
$t('duplicate with conflicting states -> hold wins', isset($get($pf)['hold'][$ID('P7')]), true);
$t('duplicates counted in snapshot', $get($pf)['duplicates'], 1);
// 4 unverified product without prior hold -> review at label time, snapshot still complete
$clean(); $put($rf, $reg3); $p = $mk(1200); unset($p[3]['productStatus']);
AdsGate::policySweep($c, $client([[200, ['products' => $p]]]), $now); $reset();
$t('unverified status -> review', AdsGate::label($row('P3'), $c), 'ads_review');
$t('other products ok with complete snapshot', AdsGate::label($row('P4'), $c), 'ads_ok');
// 5 too many malformed statuses -> whole sweep rejected
$clean(); $p = $mk(1200); for ($i = 0; $i < 10; $i++) { $p[$i]['productStatus'] = 'x'; }
$t('>0.5% malformed statuses -> exception', $throws(function () use ($c, $client, $p, $now) { AdsGate::policySweep($c, $client([[200, ['products' => $p]]]), $now); }), true);
// 6 coverage check uses only a complete snapshot of the same context
$clean(); $put($pf, ['version' => 3, 'generated_at' => gmdate('c'), 'context' => ['account_id' => '1', 'content_language' => 'sk', 'feed_label' => 'SK', 'channel' => 'ONLINE'], 'complete' => true, 'products_read' => 9999, 'hold' => (object)[]]);
$t('foreign-context previous snapshot does not block (and is not trusted)', $throws(function () use ($c, $client, $mk, $now) { AdsGate::policySweep($c, $client([[200, ['products' => $mk(1200)]]]), $now); }), false);
$put($pf, $pol3); $p = $get($pf); $p['products_read'] = 2000; $put($pf, $p);
$t('same-context complete snapshot 2000 -> 1200 rejected', $throws(function () use ($c, $client, $mk, $now) { AdsGate::policySweep($c, $client([[200, ['products' => $mk(1200)]]]), $now); }), true);
// 7 empty final page (no products, no token) after data is a valid end; non-final empty page is not
$clean();
$t('empty final page {} after data accepted', $throws(function () use ($c, $client, $mk, $now) { AdsGate::policySweep($c, $client([[200, ['products' => $mk(1200), 'nextPageToken' => 'T']], [200, []]]), $now); }), false);
$clean();
$t('empty page with nextPageToken rejected', $throws(function () use ($c, $client, $mk, $now) { AdsGate::policySweep($c, $client([[200, ['products' => $mk(600), 'nextPageToken' => 'T']], [200, ['nextPageToken' => 'U']], [200, ['products' => $mk(600)]]]), $now); }), true);
$clean();
$t('first page without products rejected', $throws(function () use ($c, $client, $now) { AdsGate::policySweep($c, $client([[200, []]]), $now); }), true);
$t('product without name rejected (Merchant API always returns name)', $throws(function () use ($c, $client, $mk, $now) { $p = $mk(1200); unset($p[9]['name']); AdsGate::policySweep($c, $client([[200, ['products' => $p]]]), $now); }), true);
// 8 transaction: snapshot stage failure leaves both old files
$clean(); $put($pf, $pol3); $put($sf, ['version' => 3, 'generated_at' => gmdate('c'), 'context' => $ctx, 'hold' => [$ID('P0') => ['x_policy_violation']]]);
$beforeP = file_get_contents($pf); $beforeS = file_get_contents($sf);
$bad = $c; $bad['ads_policy_file'] = $d.'/missing-dir/ads-policy.json'; $bad['ads_policy_holds_file'] = $sf;
$t('snapshot stage failure -> exception', $throws(function () use ($bad, $client, $mk, $now) { AdsGate::policySweep($bad, $client([[200, ['products' => $mk(1200)]]]), $now); }), true);
$t('sticky untouched after failed snapshot stage', file_get_contents($sf) === $beforeS, true);
$t('no tmp leftovers', count(glob($d.'/*.tmp.*')), 0);
// 9 unreadable sticky store is never silently rebuilt (would lose holds)
$clean(); file_put_contents($sf, '{broken');
$t('unreadable sticky -> exception', $throws(function () use ($c, $client, $mk, $now) { AdsGate::policySweep($c, $client([[200, ['products' => $mk(1200)]]]), $now); }), true);
// 10 cache reload within one process after files change (TTL) and clock going backwards
$clean(); $put($rf, $reg3); $put($pf, $pol3); $reset();
AdsGate::context($c, $now); $p = $pol3; $p['hold'] = [$ID('Q') => ['x_policy_violation']]; $put($pf, $p);
$t('within TTL cache is reused', AdsGate::decide($row('Q'), $c, AdsGate::context($c, $now + 10))[0], 'ads_ok');
$t('after TTL file change is visible', AdsGate::decide($row('Q'), $c, AdsGate::context($c, $now + 400))[0], 'ads_hold');

echo ($n - $fail)."/$n PASS\n";
$reset(); foreach (glob($d.'/catalog-state/*') as $f) { unlink($f); } @rmdir($d.'/catalog-state'); foreach (glob($d.'/*') as $f) { is_file($f) && unlink($f); } @rmdir($d);
exit($fail ? 1 : 0);
