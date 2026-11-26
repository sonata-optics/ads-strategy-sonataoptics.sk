<?php
// READ-ONLY. php8.1 ~/z_ro_cats_removed.php REMOVED_IDS_FILE OUT_JSON
// Dumps SK (company 25) category tree (id, parent, path, status, name) and, for offer IDs that disappeared from
// Merchant between 15.11 and 25.11, their current CS-Cart state (exists, status, price, main category). No writes.
list(, $in, $out) = array_pad($argv, 3, '');
$_SERVER['argv'] = array('admin_stromes.php'); define('AREA', 'A'); define('ACCOUNT_TYPE', 'admin'); define('NO_SESSION', true);
chdir('/home/smartshomeby/www'); require './init.php';
$cats = db_get_array('SELECT c.category_id, c.parent_id, c.id_path, c.status, d.category FROM ?:categories c JOIN ?:category_descriptions d ON d.category_id=c.category_id AND d.lang_code=?s WHERE c.company_id=?i', 'sk', 25);
$ids = array_values(array_filter(array_map('intval', preg_split('/\s+/', (string)@file_get_contents($in)))));
$rem = [];
foreach (array_chunk($ids, 500) as $ch) {
    $rows = db_get_hash_array('SELECT p.product_id, p.status, p.company_id, pp.price FROM ?:products p LEFT JOIN ?:product_prices pp ON pp.product_id=p.product_id AND pp.lower_limit=1 AND pp.usergroup_id=0 WHERE p.product_id IN (?n)', 'product_id', $ch);
    $main = db_get_hash_single_array('SELECT product_id, category_id FROM ?:products_categories WHERE product_id IN (?n) AND link_type=?s', ['product_id', 'category_id'], $ch, 'M');
    foreach ($ch as $id) {
        $r = $rows[$id] ?? null;
        $rem[] = ['id' => $id, 'exists' => $r ? 1 : 0, 'status' => $r['status'] ?? '', 'company_id' => $r['company_id'] ?? '', 'price' => $r['price'] ?? '', 'main_category' => $main[$id] ?? ''];
    }
}
file_put_contents($out, json_encode(['categories' => $cats, 'removed' => $rem], JSON_UNESCAPED_UNICODE));
echo count($cats), " categories, ", count($rem), " removed ids\n";
