<?php
// php test_ads_gate_v3.php /path/to/AdsGate.php - extra regression tests for ads-gate-v3 (no CS-Cart, no network, temp dir only).
// Covers ChatGPT move-4 static audit: context cache, stale/sticky holds, schema, manual-ok validity, pagination, duplicates,
// foreign account, coverage drop, partial snapshot, atomic write, explicit release.
require $argv[1];
use SonataMerchant\AdsGate;
$dir = sys_get_temp_dir().'/ads_gate_v3_'.getmypid(); @mkdir($dir); @mkdir($dir.'/a'); @mkdir($dir.'/a/catalog-state'); @mkdir($dir.'/b'); @mkdir($dir.'/b/catalog-state');
$now = time();
$ctxA = ['account_id' => '999000111', 'content_language' => 'sk', 'feed_label' => 'SK', 'state_dir' => $dir.'/a/catalog-state'];
$ctxB = ['account_id' => '999000222', 'content_language' => 'sk', 'feed_label' => 'SK', 'state_dir' => $dir.'/b/catalog-state'];
$n = 0; $fails = 0;
$t = function ($name, $got, $exp) use (&$n, &$fails) { $n++; $ok = $got === $exp; if (!$ok) { $fails++; } printf("%s %s: expected=%s actual=%s\n", $ok ? 'PASS' : 'FAIL', $name, var_export($exp, true), var_export($got, true)); };
$reset = function () { foreach (['reg', 'pol', 'stats'] as $p) { $x = new ReflectionProperty(AdsGate::class, $p); $x->setAccessible(true); $x->setValue(null, $p === 'stats' ? [] : null); } };
$put = function ($file, $data) { file_put_contents($file, json_encode($data)); };
$row = function ($id, $root = 1965, $title = 'Podložné sklíčka 50 ks') { return ['id' => (string)$id, 'main_root_id' => $root, 'main_category_id' => $root, 'title' => $title, 'product_type' => 'Mikroskopy > Príslušenstvo', 'link' => 'https://www.example.invalid/p/'.$id, 'price' => '12.90 EUR']; };
$reg = function ($c, $hold = [], $review = [], $ok = [], $age = 60) use ($now) { return ['version' => 3, 'generated_at' => gmdate('c', $now - $age), 'context' => ['account_id' => $c['account_id'], 'content_language' => 'sk', 'feed_label' => 'SK', 'channel' => 'ONLINE'], 'hold' => $hold, 'review' => $review, 'ok' => $ok]; };
$pol = function ($c, $hold = [], $age = 60, $complete = true) use ($now) { return ['version' => 3, 'generated_at' => gmdate('c', $now - $age), 'context' => ['account_id' => $c['account_id'], 'content_language' => 'sk', 'feed_label' => 'SK', 'channel' => 'ONLINE'], 'complete' => $complete, 'products_read' => 5000, 'hold' => (object)$hold]; };
$files = function ($c) { $d = dirname($c['state_dir']); return [$d.'/ads-review.json', $d.'/ads-policy.json', $d.'/ads-policy-holds.json']; };
$label = function ($c, $r) use ($reset) { return AdsGate::label($r, $c); };

// 1 context cache: same offer, two Merchant contexts with different holds -> different labels in ONE process
list($ra, $pa) = $files($ctxA); list($rb, $pb) = $files($ctxB);
$put($ra, $reg($ctxA)); $put($pa, $pol($ctxA, [AdsGate::identity($ctxA, '1') => ['guns_parts_policy_violation']]));
$put($rb, $reg($ctxB)); $put($pb, $pol($ctxB));
$reset();
$t('context A hold', $label($ctxA, $row(1)), 'ads_hold');
$t('context B same offer not leaked (separate cache)', $label($ctxB, $row(1)), 'ads_ok');
// 2 stale snapshot: no hold -> review, known hold -> hold
$put($pa, $pol($ctxA, [AdsGate::identity($ctxA, '1') => ['x_policy_violation']], 5 * 86400)); $reset();
$t('stale snapshot keeps known hold', $label($ctxA, $row(1)), 'ads_hold');
$t('stale snapshot -> other products review', $label($ctxA, $row(2)), 'ads_review');
// 3 sticky store survives broken snapshot
$put($pa, ['broken' => true]); $put(dirname($ctxA['state_dir']).'/ads-policy-holds.json', ['version' => 3, 'generated_at' => gmdate('c', $now - 99 * 86400), 'hold' => [AdsGate::identity($ctxA, '3') => ['y_policy_violation']]]); $reset();
$t('sticky hold survives broken snapshot', $label($ctxA, $row(3)), 'ads_hold');
$t('broken snapshot -> review', $label($ctxA, $row(4)), 'ads_review');
@unlink(dirname($ctxA['state_dir']).'/ads-policy-holds.json');
// 4 schema: list instead of map, missing complete flag in v3
$put($pa, ['version' => 3, 'generated_at' => gmdate('c', $now - 60), 'complete' => true, 'products_read' => 5000, 'hold' => ['a', 'b']]); $reset();
$t('hold as list -> schema error -> review', $label($ctxA, $row(5)), 'ads_review');
$p = $pol($ctxA); unset($p['complete']); $put($pa, $p); $reset();
$t('v3 snapshot without complete flag -> review', $label($ctxA, $row(5)), 'ads_review');
$p = $pol($ctxA); $p['context']['feed_label'] = 'CZ'; $put($pa, $p); $reset();
$t('snapshot of another feed -> review', $label($ctxA, $row(5)), 'ads_review');
$r0 = $reg($ctxA); unset($r0['review']); $put($ra, $r0); $put($pa, $pol($ctxA)); $reset();
$t('register without review list -> review', $label($ctxA, $row(5)), 'ads_review');
// 5 manual ok validity
$risk = $row(6, 1974, 'Pulsar Merger LRF XT50 termovízny binokulár');
$e = ['id' => AdsGate::identity($ctxA, '6'), 'fingerprint' => AdsGate::fingerprint($risk), 'author' => 'owner', 'reason' => 'observation binocular', 'evidence' => 'card + Merchant status', 'date' => gmdate('Y-m-d', $now)];
$put($ra, $reg($ctxA, [], [], [$e])); $reset();
$t('complete manual ok on risk root -> ok (full load path)', $label($ctxA, $risk), 'ads_ok');
$e2 = $e; unset($e2['evidence']); $put($ra, $reg($ctxA, [], [], [$e2])); $reset();
$t('manual ok without evidence -> review', $label($ctxA, $risk), 'ads_review');
$e3 = $e; $e3['date'] = gmdate('Y-m-d', $now - 40 * 86400); $put($ra, $reg($ctxA, [], [], [$e3])); $reset();
$t('manual ok older than 30 days -> review', $label($ctxA, $risk), 'ads_review');
$e4 = $e; $e4['id'] = '755641187~ONLINE~sk~SHOP~6'; $put($ra, $reg($ctxA, [], [], [$e4])); $reset();
$t('manual ok of another Merchant identity ignored -> review', $label($ctxA, $risk), 'ads_review');
$put($ra, $reg($ctxA, [], [], [$e])); $reset();
$t('manual ok + price 0 -> review', $label($ctxA, array_merge($risk, ['price' => '0.00 EUR'])), 'ads_review');
$reset();
$t('manual ok + http link -> review', $label($ctxA, array_merge($risk, ['link' => 'http://www.example.invalid/p/6'])), 'ads_review');
$reset();
$t('manual ok + changed main root -> review', $label($ctxA, array_merge($risk, ['main_root_id' => 5127])), 'ads_review');
$put($ra, $reg($ctxA, [['id' => AdsGate::identity($ctxA, '6')]], [], [$e], 40 * 86400)); $reset();
$t('expired register still applies its manual hold', $label($ctxA, $risk), 'ads_hold');

// 6 policySweep
$mk = function ($n, $prefix = 'P', $name = true, $issuesFor = []) use ($ctxA) {
    $o = [];
    for ($i = 0; $i < $n; $i++) {
        $p = ['offerId' => $prefix.$i, 'feedLabel' => 'SK', 'contentLanguage' => 'sk', 'productStatus' => ['itemLevelIssues' => $issuesFor[$prefix.$i] ?? []]];
        if ($name) { $p['name'] = 'accounts/'.$ctxA['account_id'].'/products/sk~SK~'.$prefix.$i; }
        $o[] = $p;
    }
    return $o;
};
$client = function ($pages) { return new class($pages) { private $p; private $i = 0; function __construct($p) { $this->p = $p; } function request($u) { return $this->p[min($this->i++, count($this->p) - 1)]; } }; };
$throws = function ($fn) { try { $fn(); return 'no_exception'; } catch (\RuntimeException $x) { return 'exception'; } };
@unlink($pa); @unlink(dirname($ctxA['state_dir']).'/ads-policy-holds.json');
$t('repeated page token -> exception', $throws(function () use ($ctxA, $client, $mk) { AdsGate::policySweep($ctxA, $client([[200, ['products' => $mk(600), 'nextPageToken' => 'T1']], [200, ['products' => $mk(600, 'Q'), 'nextPageToken' => 'T1']]])); }), 'exception');
$t('duplicates counted once (2x600 same ids) -> exception < 1000 unique', $throws(function () use ($ctxA, $client, $mk) { AdsGate::policySweep($ctxA, $client([[200, ['products' => $mk(600), 'nextPageToken' => 'T1']], [200, ['products' => $mk(600)]]])); }), 'exception');
$t('products not a list -> exception', $throws(function () use ($ctxA, $client) { AdsGate::policySweep($ctxA, $client([[200, ['products' => ['x' => 1]]]])); }), 'exception');
$t('foreign account in response -> exception', $throws(function () use ($ctxA, $client, $mk) { $p = $mk(1200); $p[5]['name'] = 'accounts/123/products/sk~SK~P5'; AdsGate::policySweep($ctxA, $client([[200, ['products' => $p]]])); }), 'exception');
$t('HTTP error on page 2 -> exception', $throws(function () use ($ctxA, $client, $mk) { AdsGate::policySweep($ctxA, $client([[200, ['products' => $mk(600), 'nextPageToken' => 'T1']], [500, null]])); }), 'exception');
$t('no snapshot written by failed sweeps', is_file($pa), false);
$demoted = ['P0' => [['code' => 'new_policy_violation', 'severity' => 'DEMOTED', 'reportingContext' => 'SHOPPING_ADS']], 'P1' => [['code' => 'guns_parts_policy_violation', 'severity' => 'DISAPPROVED', 'reportingContext' => 'FREE_LISTINGS']], 'P2' => [['code' => 'image_too_small', 'severity' => 'DEMOTED']]];
$res = AdsGate::policySweep($ctxA, $client([[200, ['products' => $mk(1200, 'P', true, $demoted)]]]));
$out = json_decode(file_get_contents($pa), true);
$t('complete sweep: DEMOTED *_policy_violation -> hold', isset($out['hold'][AdsGate::identity($ctxA, 'P0')]), true);
$t('complete sweep: DISAPPROVED policy -> hold', isset($out['hold'][AdsGate::identity($ctxA, 'P1')]), true);
$t('non-policy issue is not a hold', isset($out['hold'][AdsGate::identity($ctxA, 'P2')]), false);
$t('snapshot marked complete with unique count', [$out['complete'], $out['products_read'], $out['version']], [true, 1200, 3]);
$t('coverage drop >10% -> exception', $throws(function () use ($ctxA, $client, $mk) { AdsGate::policySweep($ctxA, $client([[200, ['products' => $mk(1050)]]])); }), 'exception');
$t('previous snapshot unchanged after partial sweep', json_decode(file_get_contents($pa), true)['products_read'], 1200);
$clean = ['P1' => [['code' => 'guns_parts_policy_violation', 'severity' => 'DISAPPROVED']]];
$p = $mk(1150, 'P', true, $clean);
AdsGate::policySweep($ctxA, $client([[200, ['products' => $p]]]));
$st = json_decode(file_get_contents(dirname($ctxA['state_dir']).'/ads-policy-holds.json'), true);
$t('complete sweep releases P0 (seen clean) with log', [isset($st['hold'][AdsGate::identity($ctxA, 'P0')]), $st['released'][0]['id'] ?? ''], [false, AdsGate::identity($ctxA, 'P0')]);
$t('P1 still held', isset($st['hold'][AdsGate::identity($ctxA, 'P1')]), true);
$st['hold'][AdsGate::identity($ctxA, 'GONE')] = ['z_policy_violation']; $put(dirname($ctxA['state_dir']).'/ads-policy-holds.json', $st);
AdsGate::policySweep($ctxA, $client([[200, ['products' => $p]]]));
$st = json_decode(file_get_contents(dirname($ctxA['state_dir']).'/ads-policy-holds.json'), true);
$t('hold of a product not seen in sweep stays sticky', isset($st['hold'][AdsGate::identity($ctxA, 'GONE')]), true);
$put($ra, $reg($ctxA)); $reset();
$t('sticky GONE hold applies at label time', $label($ctxA, $row('GONE')), 'ads_hold');
// 7 atomic write
$t('writeAtomic into missing dir -> exception', $throws(function () use ($dir) { AdsGate::writeAtomic($dir.'/nope/x.json', ['a' => 1]); }), 'exception');
$t('no tmp leftovers', count(glob($dir.'/a/*.tmp.*')), 0);
// 8 per-context summary
$reset(); $label($ctxA, $row(1)); $label($ctxB, $row(1)); AdsGate::summary();
$t('summary written per context', [is_file($ctxA['state_dir'].'/ads-gate-summary.json'), is_file($ctxB['state_dir'].'/ads-gate-summary.json')], [true, true]);

echo ($n - $fails).'/'.$n." PASS\n";
$reset();
foreach (['a', 'b'] as $s) { array_map('unlink', glob($dir.'/'.$s.'/catalog-state/*')); @rmdir($dir.'/'.$s.'/catalog-state'); array_map('unlink', glob($dir.'/'.$s.'/*')); @rmdir($dir.'/'.$s); }
@rmdir($dir);
exit($fails ? 1 : 0);
