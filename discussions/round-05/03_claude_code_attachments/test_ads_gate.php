<?php
// php test_ads_gate.php /path/to/AdsGate.php  — fixture tests for ads-gate-v2 (no CS-Cart, no network).
require $argv[1];
use SonataMerchant\AdsGate;
$c = ['account_id' => '5831333799', 'content_language' => 'sk', 'feed_label' => 'SK', 'state_dir' => sys_get_temp_dir().'/x/catalog-state'];
$now = time(); $iso = gmdate('c', $now - 3600);
$ix = function ($list) { $o = []; foreach ($list as $e) { $o[is_array($e) ? $e['id'] : $e] = $e; } return $o; };
$reg = function ($hold = [], $review = [], $ok = []) use ($ix, $iso) { return ['ok' => true, 'generated_at' => $iso, 'hold' => $ix($hold), 'review' => $ix($review), 'ok_items' => $ix($ok)]; };
$pol = function ($hold = []) use ($iso) { return ['ok' => true, 'generated_at' => $iso, 'hold' => $hold]; };
$row = function ($id, $root, $title, $type = 'X > Y') { return ['id' => (string)$id, 'main_root_id' => $root, 'main_category_id' => $root, 'title' => $title, 'product_type' => $type, 'link' => 'https://x/'.$id, 'price' => '10.00 EUR']; };
$ID = function ($id) use ($c) { return AdsGate::identity($c, $id); };
$T = []; $fail = 0;
$t = function ($name, $got, $exp) use (&$T, &$fail) { $ok = $got[0] === $exp; if (!$ok) { $fail++; } $T[] = sprintf('%-4s %-78s -> %s (%s)', $ok ? 'PASS' : 'FAIL', $name, $got[0], $got[1]); };

$safe = $row(1001, 1965, 'Euromex podložné sklíčka 50 ks');
$t('new safe ID in a safe root -> ok', AdsGate::decide($safe, $c, ['register' => $reg(), 'policy' => $pol()]), 'ads_ok');
$t('calibration slide (kalibračné sklíčko) is not a weapon word -> ok', AdsGate::decide($row(1002, 1965, 'Kalibračné sklíčko Levenhuk MED'), $c, ['register' => $reg(), 'policy' => $pol()]), 'ads_ok');
$t('weapon wording in a SAFE root (predsádka na puškohľad) -> review', AdsGate::decide($row(1003, 5825, 'Predsádka na puškohľad 42 mm'), $c, ['register' => $reg(), 'policy' => $pol()]), 'ads_review');
$t('astro finder with ambiguous title (kolimátorový hľadáčik) -> review', AdsGate::decide($row(1004, 1969, 'Baader Sky Surfer V – kolimátorový hľadáčik s červeným bodom'), $c, ['register' => $reg(), 'policy' => $pol()]), 'ads_review');
$t('risk root (thermal 1974) without manual decision -> review', AdsGate::decide($row(1005, 1974, 'Pulsar Axion 2 XG35'), $c, ['register' => $reg(), 'policy' => $pol()]), 'ads_review');
$t('unknown / new root category -> review', AdsGate::decide($row(1006, 9999, 'Nový produkt'), $c, ['register' => $reg(), 'policy' => $pol()]), 'ads_review');
$t('missing data (empty product_type) -> review', AdsGate::decide(array_merge($safe, ['product_type' => '']), $c, ['register' => $reg(), 'policy' => $pol()]), 'ads_review');
$okE = ['id' => $ID(1005), 'fingerprint' => AdsGate::fingerprint($row(1005, 1974, 'Pulsar Axion 2 XG35')), 'author' => 'owner', 'reason' => 'observation device', 'evidence' => 'card checked', 'date' => '2026-11-26'];
$t('risk root WITH manual ok and matching fingerprint -> ok', AdsGate::decide($row(1005, 1974, 'Pulsar Axion 2 XG35'), $c, ['register' => $reg([], [], [$okE]), 'policy' => $pol()]), 'ads_ok');
$t('manual ok invalidated by changed title/role -> review', AdsGate::decide($row(1005, 1974, 'Pulsar Axion 2 XG35 s montážou na zbraň'), $c, ['register' => $reg([], [], [$okE]), 'policy' => $pol()]), 'ads_review');
$t('new Google policy code AFTER manual ok -> hold', AdsGate::decide($row(1005, 1974, 'Pulsar Axion 2 XG35'), $c, ['register' => $reg([], [], [$okE]), 'policy' => $pol([$ID(1005) => ['other_weapons_policy_violation']])]), 'ads_hold');
$t('manual hold beats manual ok', AdsGate::decide($row(1005, 1974, 'Pulsar Axion 2 XG35'), $c, ['register' => $reg([['id' => $ID(1005)]], [], [$okE]), 'policy' => $pol()]), 'ads_hold');
$t('policy hold on a safe-root product -> hold', AdsGate::decide($safe, $c, ['register' => $reg(), 'policy' => $pol([$ID(1001) => ['guns_parts_policy_violation']])]), 'ads_hold');
$t('same item_id held in ANOTHER Merchant identity does not leak -> ok', AdsGate::decide($safe, $c, ['register' => $reg([['id' => '755641187~ONLINE~sk~SHOP~1001']]), 'policy' => $pol(['755641187~ONLINE~sk~SHOP~1001' => ['x_policy_violation']])]), 'ads_ok');
$t('register expired/broken -> review (fail closed)', AdsGate::decide($safe, $c, ['register' => ['ok' => false, 'why' => 'expired'], 'policy' => $pol()]), 'ads_review');
$t('policy snapshot stale -> review (fail closed)', AdsGate::decide($safe, $c, ['register' => $reg(), 'policy' => ['ok' => false, 'why' => 'expired']]), 'ads_review');
$t('policy hold still applies when register is broken', AdsGate::decide($safe, $c, ['register' => ['ok' => false, 'why' => 'invalid'], 'policy' => $pol([$ID(1001) => ['guns_parts_policy_violation']])]), 'ads_hold');

// loader: version, timestamps, expiry
$rf = new ReflectionMethod(AdsGate::class, 'load'); $rf->setAccessible(true);
$tmp = tempnam(sys_get_temp_dir(), 'g');
$chk = function ($name, $json, $maxAge, $expOk) use ($rf, $tmp, $now, &$T, &$fail) { file_put_contents($tmp, $json); $r = $rf->invoke(null, $tmp, $maxAge, $now); $ok = $r['ok'] === $expOk; if (!$ok) { $fail++; } $T[] = sprintf('%-4s %-78s -> ok=%s %s', $ok ? 'PASS' : 'FAIL', $name, var_export($r['ok'], true), $r['why'] ?? ''); };
$chk('loader: valid v2 file', json_encode(['version' => 2, 'generated_at' => gmdate('c', $now - 60)]), 3600, true);
$chk('loader: unversioned v1 file rejected', json_encode(['hold' => [], 'ok' => []]), 3600, false);
$chk('loader: expired file rejected', json_encode(['version' => 2, 'generated_at' => gmdate('c', $now - 7200)]), 3600, false);
$chk('loader: future timestamp rejected', json_encode(['version' => 2, 'generated_at' => gmdate('c', $now + 7200)]), 3600, false);
$chk('loader: broken JSON rejected', '{not json', 3600, false);
unlink($tmp);
echo implode(PHP_EOL, $T), PHP_EOL, count($T) - $fail, '/', count($T), ' PASS', PHP_EOL;
exit($fail ? 1 : 0);
