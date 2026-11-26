<?php
namespace SonataMerchant { function rename($a,$b) { if (($GLOBALS['failRenameTo']??null)===$b) return false; return \rename($a,$b); } }
namespace {

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


$clean(); $put($rf,$reg3); $put($pf,$pol3); file_put_contents($sf,'{broken');
$t('corrupt existing sticky must fail closed', AdsGate::label($row('A'),$c), 'ads_review');
$clean(); $put($rf,$reg3); $p=$mk(1200); $p[0]['productStatus']['itemLevelIssues']=[['code'=>'x_policy_violation'], 'broken'];
AdsGate::policySweep($c,$client([[200,['products'=>$p]]]),$now); $reset();
$t('known policy flag survives malformed sibling',AdsGate::label($row('P0'),$c),'ads_hold');
$clean(); $put($rf,['version'=>2,'generated_at'=>gmdate('c'),'hold'=>[],'review'=>[],'ok'=>[]]); $put($pf,['version'=>2,'generated_at'=>gmdate('c'),'hold'=>(object)[]]);
$t('string false is not explicit migration approval',AdsGate::label($row('A'),$c+['legacy_v2_bind'=>'false']),'ads_review');
echo "$fail/$n adversarial failures\n";

$clean(); $put($rf,$reg3); $put($pf,$pol3); $put($sf,['version'=>3,'generated_at'=>gmdate('c'),'context'=>$ctx,'hold'=>(object)[]]);
$old=file_get_contents($pf); $GLOBALS['failRenameTo']=$pf;
$failed=$throws(function()use($c,$client,$mk,$now){AdsGate::policySweep($c,$client([[200,['products'=>$mk(1200,['P0'=>[['code'=>'x_policy_violation']]])]]]),$now);});
unset($GLOBALS['failRenameTo']); $reset();
$t('second rename failure throws',$failed,true);
$t('second rename failure preserves old snapshot',file_get_contents($pf)===$old,true);
$t('new hold survives interrupted pair commit',AdsGate::label($row('P0'),$c),'ads_hold');
echo ($n-$fail)."/$n adversarial PASS; $fail FAIL\n";
}
