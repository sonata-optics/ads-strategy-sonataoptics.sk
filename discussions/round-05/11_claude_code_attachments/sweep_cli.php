<?php
// php sweep_cli.php AdsGate.php <dir> <flaggedOfferId> - v3.2 policySweep with a fake Merchant client (1200 products, one flagged).
require $argv[1];
$c = ['account_id' => '999000111', 'content_language' => 'sk', 'feed_label' => 'SK', 'state_dir' => $argv[2].'/catalog-state'];
$p = []; for ($i = 0; $i < 1200; $i++) { $p[] = ['name' => 'accounts/999000111/products/sk~SK~P'.$i, 'offerId' => 'P'.$i, 'feedLabel' => 'SK', 'contentLanguage' => 'sk', 'productStatus' => ['itemLevelIssues' => []]]; }
$p[] = ['name' => 'accounts/999000111/products/sk~SK~'.$argv[3], 'offerId' => $argv[3], 'feedLabel' => 'SK', 'contentLanguage' => 'sk', 'productStatus' => ['itemLevelIssues' => [['code' => 'new_policy_violation', 'severity' => 'DISAPPROVED']]]];
$cl = new class($p) { private $p; function __construct($p) { $this->p = $p; } function request($u) { return [200, ['products' => $this->p]]; } };
echo json_encode(SonataMerchant\AdsGate::policySweep($c, $cl)), "\n";
