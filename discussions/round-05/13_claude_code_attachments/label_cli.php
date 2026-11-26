<?php
// php label_cli.php AdsGate.php <dir> <offerId> [nowOffsetSeconds] - prints the label of a synthetic safe-root product.
require $argv[1];
$c = ['account_id' => '999000111', 'content_language' => 'sk', 'feed_label' => 'SK', 'state_dir' => $argv[2].'/catalog-state'];
$row = ['id' => $argv[3], 'main_root_id' => 1965, 'main_category_id' => 1965, 'title' => 'Glass slides', 'product_type' => 'Science', 'link' => 'https://example.invalid/p', 'price' => '25.00 EUR'];
$off = (int)($argv[4] ?? 0);
if ($off && method_exists('SonataMerchant\AdsGate', 'context')) { echo SonataMerchant\AdsGate::decide($row, $c, SonataMerchant\AdsGate::context($c, time() + $off))[0], "\n"; exit; }
if ($off) { // v2 has no injectable clock: age the files instead
  foreach (['ads-review.json', 'ads-policy.json'] as $f) { $p = $argv[2].'/'.$f; if (is_file($p)) { $d = json_decode(file_get_contents($p), true); $d['generated_at'] = gmdate('c', strtotime($d['generated_at']) - $off); file_put_contents($p, json_encode($d)); } }
}
echo SonataMerchant\AdsGate::label($row, $c), "\n";
