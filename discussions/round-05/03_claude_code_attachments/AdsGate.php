<?php
namespace SonataMerchant;

/**
 * Ads admission gate for custom_label_4, rule version ads-gate-v2 (2026-11-26, Claude Code, round 5 move 3).
 * Positive contract (R5-CHATGPT-01): a product is ads_ok ONLY if its main category root is on the SAFE list,
 * no risk signal applies, the policy snapshot is fresh and does not flag it, and no manual hold exists.
 * Everything unknown, new, stale or ambiguous -> ads_review. Known policy problem or manual hold -> ads_hold.
 * Order: manual hold > Google policy hold > (manual ok with matching fingerprint) > risk/unknown review > safe ok.
 * Fail closed: unreadable/unversioned/expired register or policy snapshot -> ads_review for everything not on hold.
 * Inputs (outside webroot, 0600): ads-review.json (register v2), ads-policy.json (daily sweep of Merchant API statuses).
 */
final class AdsGate
{
    const RULES = 'ads-gate-v2';
    // Root category IDs (CS-Cart company 25) whose products may pass the automatic pre-check.
    const SAFE_ROOTS = [6183, 1970, 5883, 1969, 1968, 1724, 1971, 1963, 1984, 1976, 1960, 1964, 5877, 1978, 6054, 6160, 6161,
                        5827, 5825, 5197, 1965, 5979, 1721, 5983, 1718, 5288, 1958, 1962];
    // Roots that always need an explicit per-product decision (weapon-adjacent or dual use).
    const RISK_ROOTS = [1975, 5826, 1722, 5196, 1974, 5831, 6184, 5127, 5829, 4767, 5828, 5870, 5995];
    const RISK_TITLE = '/(?<![\p{L}\d])(zbra[nň]\p{L}*|pušk\p{L}*|pusk\p{L}*|guľovnic\p{L}*|gulovnic\p{L}*|vzduchovk\p{L}*|picatinny|weaver|tlmi[čc]\p{L}*|clip[- ]?on|predsádk\p{L}*|predsadk\p{L}*|kolimátor\p{L}*|red ?dot|rifle|weapon|airsoft|nábo[jň]\p{L}*|kalibr(?!ác|ač)\p{L}*)/u';
    const REGISTER_MAX_AGE = 30 * 86400;
    const POLICY_MAX_AGE = 3 * 86400;

    private static $reg = null; private static $pol = null; private static $stats = [];

    public static function identity(array $c, $offerId)
    {
        return $c['account_id'].'~ONLINE~'.$c['content_language'].'~'.$c['feed_label'].'~'.$offerId;
    }
    public static function fingerprint(array $row)
    {
        return substr(hash('sha256', mb_strtolower(trim((string)($row['title'] ?? '')), 'UTF-8').'|'.(string)($row['product_type'] ?? '').'|'.(string)($row['main_category_id'] ?? '')), 0, 16);
    }
    private static function load($file, $maxAge, $now)
    {
        if (!is_file($file)) { return ['ok' => false, 'why' => 'missing']; }
        $d = json_decode((string)file_get_contents($file), true);
        if (!is_array($d) || ($d['version'] ?? 0) < 2 || empty($d['generated_at'])) { return ['ok' => false, 'why' => 'invalid_or_unversioned']; }
        $t = strtotime($d['generated_at']);
        if (!$t || $t > $now + 300) { return ['ok' => false, 'why' => 'bad_or_future_timestamp']; }
        if ($now - $t > $maxAge) { return ['ok' => false, 'why' => 'expired']; }
        $d['ok'] = true; return $d;
    }
    /** Pure decision for tests: $ctx = [register, policy, now]. Returns [label, reason]. */
    public static function decide(array $row, array $c, array $ctx)
    {
        $reg = $ctx['register']; $pol = $ctx['policy'];
        $id = self::identity($c, $row['id']);
        if (!empty($reg['ok']) && isset($reg['hold'][$id])) { return ['ads_hold', 'manual_hold']; }
        if (!empty($pol['ok']) && isset($pol['hold'][$id])) { return ['ads_hold', 'google_policy:'.implode(',', (array)$pol['hold'][$id])]; }
        if (empty($reg['ok'])) { return ['ads_review', 'register_'.($reg['why'] ?? 'unavailable')]; }
        if (empty($pol['ok'])) { return ['ads_review', 'policy_snapshot_'.($pol['why'] ?? 'unavailable')]; }
        if (isset($reg['ok_items'][$id])) {
            $e = $reg['ok_items'][$id];
            if (($e['fingerprint'] ?? '') === self::fingerprint($row)) { return ['ads_ok', 'manual_ok:'.($e['author'] ?? '?')]; }
            return ['ads_review', 'manual_ok_invalidated_by_change'];
        }
        if (isset($reg['review'][$id])) { return ['ads_review', 'manual_review'];}
        $root = (int)($row['main_root_id'] ?? 0);
        if (in_array($root, self::RISK_ROOTS, true)) { return ['ads_review', 'risk_root:'.$root]; }
        if (preg_match(self::RISK_TITLE, mb_strtolower((string)($row['title'] ?? ''), 'UTF-8'), $m)) { return ['ads_review', 'risk_title:'.$m[0]]; }
        foreach (['title', 'product_type', 'link', 'price'] as $k) { if (trim((string)($row[$k] ?? '')) === '') { return ['ads_review', 'missing_'.$k]; } }
        if (!in_array($root, self::SAFE_ROOTS, true)) { return ['ads_review', 'unknown_root:'.$root]; }
        return ['ads_ok', 'safe_root:'.$root];
    }
    public static function label(array $row, array $c)
    {
        $now = time();
        if (self::$reg === null) {
            $dir = dirname($c['state_dir']);
            $r = self::load($c['ads_review_file'] ?? $dir.'/ads-review.json', self::REGISTER_MAX_AGE, $now);
            if ($r['ok']) {
                $idx = static function ($list) { $o = []; foreach ((array)$list as $e) { $o[is_array($e) ? (string)$e['id'] : (string)$e] = is_array($e) ? $e : true; } return $o; };
                $r['hold'] = $idx($r['hold'] ?? []); $r['review'] = $idx($r['review'] ?? []); $r['ok_items'] = $idx($r['ok'] ?? []);
            }
            self::$reg = $r;
            $p = self::load($c['ads_policy_file'] ?? $dir.'/ads-policy.json', self::POLICY_MAX_AGE, $now);
            if ($p['ok']) { $p['hold'] = (array)($p['hold'] ?? []); }
            self::$pol = $p;
            register_shutdown_function([__CLASS__, 'summary'], $dir.'/catalog-state/ads-gate-summary.json');
        }
        list($label, $why) = self::decide($row, $c, ['register' => self::$reg, 'policy' => self::$pol, 'now' => $now]);
        $k = $label.'|'.preg_replace('/:.*/', '', $why);
        self::$stats[$k] = (self::$stats[$k] ?? 0) + 1;
        return $label;
    }
    public static function summary($file)
    {
        if (!self::$stats) { return; }
        $out = ['rules' => self::RULES, 'evaluated_at' => gmdate('c'), 'register' => ['ok' => self::$reg['ok'] ?? false, 'why' => self::$reg['why'] ?? '', 'generated_at' => self::$reg['generated_at'] ?? null],
                'policy' => ['ok' => self::$pol['ok'] ?? false, 'why' => self::$pol['why'] ?? '', 'generated_at' => self::$pol['generated_at'] ?? null, 'hold_count' => count((array)(self::$pol['hold'] ?? []))],
                'counts' => self::$stats];
        @file_put_contents($file, json_encode($out, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE), LOCK_EX);
    }
    /** Daily sweep: read every product status from Merchant API; any Shopping/free-listing DISAPPROVED issue whose code
     *  mentions policy -> hold. Writes ads-policy.json atomically. Failure leaves the old file to expire (fail closed). */
    public static function policySweep(array $c, $client)
    {
        $base = 'https://merchantapi.googleapis.com/products/v1/accounts/'.$c['account_id'].'/products?pageSize=1000';
        $hold = []; $seen = 0; $token = ''; $pages = 0;
        do {
            list($http, $body) = $client->request($base.($token !== '' ? '&pageToken='.rawurlencode($token) : ''));
            if ($http !== 200 || !is_array($body)) { throw new \RuntimeException('Policy sweep HTTP '.$http.' on page '.$pages); }
            foreach ($body['products'] ?? [] as $p) {
                if (($p['feedLabel'] ?? '') !== $c['feed_label'] || ($p['contentLanguage'] ?? '') !== $c['content_language']) { continue; }
                $seen++;
                foreach ($p['productStatus']['itemLevelIssues'] ?? [] as $i) {
                    $code = (string)($i['code'] ?? '');
                    $ctx = (string)($i['reportingContext'] ?? '');
                    if (stripos($code, 'policy') !== false && ($i['severity'] ?? '') === 'DISAPPROVED' && in_array($ctx, ['SHOPPING_ADS', 'FREE_LISTINGS', ''], true)) {
                        $hold[self::identity($c, $p['offerId'])][$code] = true;
                    }
                }
            }
            $token = (string)($body['nextPageToken'] ?? ''); $pages++;
            if ($pages > 200) { throw new \RuntimeException('Policy sweep: too many pages'); }
        } while ($token !== '');
        if ($seen < 1000) { throw new \RuntimeException('Policy sweep: only '.$seen.' products read; not replacing snapshot'); }
        $out = ['version' => 2, 'generated_at' => gmdate('c'), 'source' => 'Merchant API products.list productStatus', 'products_read' => $seen,
                'hold' => array_map('array_keys', $hold)];
        $file = $c['ads_policy_file'] ?? dirname($c['state_dir']).'/ads-policy.json';
        $tmp = $file.'.tmp'; $old = umask(0077);
        file_put_contents($tmp, json_encode($out, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE), LOCK_EX); rename($tmp, $file); umask($old);
        return ['products_read' => $seen, 'hold' => count($hold), 'pages' => $pages];
    }
}
