<?php
// php test_price_band.php - boundary tests for the proposed Catalog::priceBand (copied verbatim from the patch).
function priceBand($price){ if (!is_numeric($price) || $price <= 0) { return 'p_invalid'; } $p=round((float)$price,2);
 if ($p<20) { return 'p_lt20'; } if ($p<50) { return 'p_20_49'; } if ($p<200) { return 'p_50_199'; } if ($p<500) { return 'p_200_499'; }
 if ($p<1500) { return 'p_500_1499'; } if ($p<3000) { return 'p_1500_2999'; } if ($p<5000) { return 'p_3000_4999'; } return 'p_5000_plus'; }
$cases=[[0,'p_invalid'],[-1,'p_invalid'],['x','p_invalid'],[0.01,'p_lt20'],[19.99,'p_lt20'],[19.994,'p_lt20'],[19.995,'p_20_49'],[20,'p_20_49'],[20.00,'p_20_49'],
 [49.99,'p_20_49'],[50,'p_50_199'],[199.99,'p_50_199'],[200,'p_200_499'],[4999.99,'p_3000_4999'],[5000,'p_5000_plus']];
$f=0; foreach($cases as [$in,$exp]){ $got=priceBand($in); $ok=$got===$exp; $f+=!$ok; printf("%s %s -> %s (exp %s)\n",$ok?'PASS':'FAIL',var_export($in,true),$got,$exp); }
echo (count($cases)-$f).'/'.count($cases)." PASS\n"; exit($f?1:0);
