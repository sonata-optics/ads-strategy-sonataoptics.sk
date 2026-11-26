<?php
namespace SonataMerchant;

/**
 * Ads admission gate for custom_label_4, rule version ads-gate-v3.1 (2026-11-26, Claude Code, round 5 move 7).
 * REPOSITORY PATCH ONLY - not deployed. v3 + fixes for ChatGPT move-6 adversarial checks (R5-CHATGPT-12/13).
 *
 * Decision order (first match wins):
 *   1 manual hold (register, also expired/invalid register)            -> ads_hold
 *   2 Google policy hold: current snapshot, expired snapshot, sticky   -> ads_hold
 *   3 product unverified in the last sweep (malformed status)          -> ads_review
 *   4 required fields missing/invalid                                  -> ads_review (blocks manual ok too)
 *   5 register invalid/expired/unbound                                 -> ads_review
 *   6 policy snapshot invalid/expired/incomplete/unbound               -> ads_review
 *   7 manual review (also when a manual ok exists = conflict)          -> ads_review
 *   8 manual ok: complete entry + fingerprint matches                  -> ads_ok, otherwise ads_review
 *   9 risk root / risk title / unknown root                            -> ads_review
 *  10 safe root                                                        -> ads_ok
 *
 * Schema: register and policy snapshot must be version 3 and carry `context` equal to the running Merchant context.
 * Version-2 files are accepted for normal decisions ONLY with explicit migration binding $c['legacy_v2_bind'] === true
 * (one-time deploy step; holds from v2 files are always read, fail-closed).
 * Runtime: CS-Cart cron, one process per hour (catalog_run) and per day (policy_sweep). The context cache is still
 * re-validated: entries older than CACHE_TTL or evaluated with another clock value are reloaded.
 * policySweep commit: both files staged as tmp first; sticky store renamed first (holds only grow or are released by a
 * complete verified sweep), snapshot second. A failure before the sticky rename leaves both old files; a failure between
 * the renames leaves new sticky + old snapshot, whose holds are still read (fail-closed union).
 */
final class AdsGate
{
    const RULES = 'ads-gate-v3.1';
    const SCHEMA = 3;
    const SAFE_ROOTS = [6183, 1970, 5883, 1969, 1968, 1724, 1971, 1963, 1984, 1976, 1960, 1964, 5877, 1978, 6054, 6160, 6161,
                        5827, 5825, 5197, 1965, 5979, 1721, 5983, 1718, 5288, 1958, 1962];
    const RISK_ROOTS = [1975, 5826, 1722, 5196, 1974, 5831, 6184, 5127, 5829, 4767, 5828, 5870, 5995];
    const RISK_TITLE = '/(?<![\p{L}\d])(zbra[nň]\p{L}*|pušk\p{L}*|pusk\p{L}*|guľovnic\p{L}*|gulovnic\p{L}*|vzduchovk\p{L}*|picatinny|weaver|tlmi[čc]\p{L}*|clip[- ]?on|predsádk\p{L}*|predsadk\p{L}*|kolimátor\p{L}*|red ?dot|rifle|weapon|airsoft|nábo[jň]\p{L}*|kalibr(?!ác|ač)\p{L}*)/u';
    const REGISTER_MAX_AGE = 30 * 86400;
    const POLICY_MAX_AGE = 3 * 86400;
    const CACHE_TTL = 300;
    const OK_ENTRY_FIELDS = ['id', 'fingerprint', 'author', 'reason', 'evidence', 'date'];
    const MIN_PRODUCTS = 1000;
    const MAX_COVERAGE_DROP = 0.10;
    const MAX_UNVERIFIED_SHARE = 0.005;   // >0.5 % malformed product statuses -> whole sweep rejected
    const PAGE_KEYS = ['products', 'nextPageToken'];

    private static $reg = null; private static $pol = null; private static $stats = [];

    public static function identity(array $c, $offerId)
    {
        return $c['account_id'].'~ONLINE~'.$c['content_language'].'~'.$c['feed_label'].'~'.$offerId;
    }
    public static function fingerprint(array $row)
    {
        return substr(hash('sha256', implode('|', [
            mb_strtolower(trim((string)($row['title'] ?? '')), 'UTF-8'),
            (string)($row['product_type'] ?? ''),
            (string)($row['main_category_id'] ?? ''),
            (string)($row['main_root_id'] ?? ''),
        ])), 0, 16);
    }
    private static function files(array $c)
    {
        $dir = dirname((string)$c['state_dir']);
        $pol = $c['ads_policy_file'] ?? $dir.'/ads-policy.json';
        $n = function ($p) { $r = realpath(dirname($p)); return ($r !== false ? $r : dirname($p)).'/'.basename($p); };
        return ['reg' => $n($c['ads_review_file'] ?? $dir.'/ads-review.json'), 'pol' => $n($pol),
                'sticky' => $n($c['ads_policy_holds_file'] ?? preg_replace('/\.json$/', '', $pol).'-holds.json'),
                'summary' => $dir.'/catalog-state/ads-gate-summary.json'];
    }
    private static function contextKey(array $c)
    {
        $f = self::files($c);
        return implode('|', [$c['account_id'] ?? '', $c['content_language'] ?? '', $c['feed_label'] ?? '', 'ONLINE',
            $f['reg'], $f['pol'], $f['sticky'], empty($c['legacy_v2_bind']) ? 'v3only' : 'v2bound']);
    }
    private static function ctxOf(array $c)
    {
        return ['account_id' => (string)$c['account_id'], 'content_language' => (string)$c['content_language'], 'feed_label' => (string)$c['feed_label'], 'channel' => 'ONLINE'];
    }

    /** Generic loader: [ok, why, data]. Versions 2..3 only; expired files keep data (holds are never weakened by age). */
    private static function load($file, $maxAge, $now)
    {
        if (!is_file($file)) { return ['ok' => false, 'why' => 'missing', 'data' => null]; }
        $d = json_decode((string)file_get_contents($file), true);
        if (!is_array($d) || !is_int($d['version'] ?? null) || $d['version'] < 2 || !is_string($d['generated_at'] ?? null)) {
            return ['ok' => false, 'why' => 'invalid_or_unversioned', 'data' => null];
        }
        if ($d['version'] > self::SCHEMA) { return ['ok' => false, 'why' => 'unsupported_version', 'data' => null]; }
        $t = strtotime($d['generated_at']);
        if (!$t || $t > $now + 300) { return ['ok' => false, 'why' => 'bad_or_future_timestamp', 'data' => null]; }
        if ($now - $t > $maxAge) { return ['ok' => false, 'why' => 'expired', 'data' => $d]; }
        return ['ok' => true, 'why' => '', 'data' => $d];
    }
    private static function isList($v) { return is_array($v) && ($v === [] || array_keys($v) === range(0, count($v) - 1)); }
    private static function isMap($v) { return is_array($v) && ($v === [] || !self::isList($v)); }
    /** v3 must carry the exact context; v2 only with explicit migration binding. */
    private static function bound(array $d, array $c)
    {
        if (($d['version'] ?? 0) === 2) { return !empty($c['legacy_v2_bind']) && !isset($d['context']); }
        return ($d['version'] ?? 0) === self::SCHEMA && ($d['context'] ?? null) === self::ctxOf($c);
    }
    private static function holdsOf($d, array $c)
    {
        $o = [];
        if (!is_array($d) || !self::isMap($d['hold'] ?? null)) { return $o; }
        $prefix = self::identity($c, '');
        foreach ($d['hold'] as $id => $codes) { if (strpos((string)$id, $prefix) === 0) { $o[(string)$id] = array_values((array)$codes); } }
        return $o;
    }

    public static function normalizeRegister(array $l, array $c, $now)
    {
        $out = ['ok' => false, 'why' => $l['why'], 'hold' => [], 'review' => [], 'ok_items' => []];
        $d = $l['data'];
        if (!is_array($d)) { return $out; }
        $prefix = self::identity($c, '');
        $idx = function ($list, $needFields) use ($prefix, $now) {
            $o = [];
            foreach ((array)$list as $e) {
                $id = is_array($e) ? (string)($e['id'] ?? '') : (string)$e;
                if ($id === '' || strpos($id, $prefix) !== 0) { continue; }
                if ($needFields) {
                    foreach (self::OK_ENTRY_FIELDS as $f) { if (!is_array($e) || trim((string)($e[$f] ?? '')) === '') { $e = null; break; } }
                    if ($e === null) { $o[$id] = ['invalid' => true]; continue; }
                    $t = strtotime((string)$e['date']);
                    if (!$t || $t > $now + 86400 || $now - $t > self::REGISTER_MAX_AGE) { $o[$id] = ['invalid' => true]; continue; }
                }
                $o[$id] = is_array($e) ? $e : ['id' => $id];
            }
            return $o;
        };
        if (self::isList($d['hold'] ?? null)) { $out['hold'] = $idx($d['hold'], false); }   // holds read regardless of age/binding
        foreach (['hold', 'review', 'ok'] as $k) { if (!array_key_exists($k, $d) || !self::isList($d[$k])) { $out['why'] = 'schema_'.$k; return $out; } }
        if (!self::bound($d, $c)) { $out['why'] = 'unbound_context_or_version'; return $out; }
        if (!$l['ok']) { return $out; }
        $out['review'] = $idx($d['review'], false);
        $out['ok_items'] = $idx($d['ok'], true);
        $out['ok'] = true; $out['why'] = '';
        return $out;
    }
    /** Policy snapshot + sticky store -> [ok, why, hold, unverified]. Holds from any readable file stay (union). */
    public static function normalizePolicy(array $l, array $sticky, array $c)
    {
        $out = ['ok' => false, 'why' => $l['why'], 'hold' => [], 'unverified' => []];
        foreach ([$sticky['data'] ?? null, $l['data']] as $d) { $out['hold'] += self::holdsOf($d, $c); }
        $d = $l['data'];
        if (is_array($d) && self::isList($d['unverified'] ?? null)) { foreach ($d['unverified'] as $id) { if (is_string($id)) { $out['unverified'][$id] = true; } } }
        if (!$l['ok'] || !is_array($d)) { return $out; }
        if (!array_key_exists('hold', $d) || !self::isMap($d['hold'])) { $out['why'] = 'schema_hold'; return $out; }
        if (!self::bound($d, $c)) { $out['why'] = 'unbound_context_or_version'; return $out; }
        if ($d['version'] === self::SCHEMA && (($d['complete'] ?? null) !== true || !is_int($d['products_read'] ?? null) || $d['products_read'] <= 0)) {
            $out['why'] = 'incomplete_snapshot'; return $out;
        }
        $out['ok'] = true; $out['why'] = '';
        return $out;
    }
    public static function missingField(array $row)
    {
        foreach (['id', 'title', 'product_type'] as $k) { if (trim((string)($row[$k] ?? '')) === '') { return 'missing_'.$k; } }
        $link = (string)($row['link'] ?? '');
        if (!filter_var($link, FILTER_VALIDATE_URL) || strtolower((string)parse_url($link, PHP_URL_SCHEME)) !== 'https') { return 'invalid_link'; }
        if (!preg_match('/^\s*(\d+(?:[.,]\d{1,2})?)\s*([A-Z]{3})\s*$/', (string)($row['price'] ?? ''), $m) || (float)str_replace(',', '.', $m[1]) <= 0) { return 'invalid_price'; }
        return '';
    }

    public static function decide(array $row, array $c, array $ctx)
    {
        $reg = $ctx['register']; $pol = $ctx['policy'];
        $id = self::identity($c, (string)($row['id'] ?? ''));
        if (isset($reg['hold'][$id])) { return ['ads_hold', 'manual_hold']; }
        if (isset($pol['hold'][$id])) { return ['ads_hold', 'google_policy:'.implode(',', (array)$pol['hold'][$id])]; }
        if (isset($pol['unverified'][$id])) { return ['ads_review', 'policy_status_unverified']; }
        if (($miss = self::missingField($row)) !== '') { return ['ads_review', $miss]; }
        if (empty($reg['ok'])) { return ['ads_review', 'register_'.($reg['why'] ?? 'unavailable')]; }
        if (empty($pol['ok'])) { return ['ads_review', 'policy_snapshot_'.($pol['why'] ?? 'unavailable')]; }
        if (isset($reg['review'][$id])) { return ['ads_review', isset($reg['ok_items'][$id]) ? 'manual_conflict_review_wins' : 'manual_review']; }
        if (isset($reg['ok_items'][$id])) {
            $e = $reg['ok_items'][$id];
            if (!empty($e['invalid'])) { return ['ads_review', 'manual_ok_incomplete_or_expired']; }
            foreach (self::OK_ENTRY_FIELDS as $f) { if (trim((string)($e[$f] ?? '')) === '') { return ['ads_review', 'manual_ok_missing_'.$f]; } }
            if (($e['fingerprint'] ?? '') === self::fingerprint($row)) { return ['ads_ok', 'manual_ok:'.$e['author']]; }
            return ['ads_review', 'manual_ok_invalidated_by_change'];
        }
        $root = (int)($row['main_root_id'] ?? 0);
        if (in_array($root, self::RISK_ROOTS, true)) { return ['ads_review', 'risk_root:'.$root]; }
        if (preg_match(self::RISK_TITLE, mb_strtolower((string)($row['title'] ?? ''), 'UTF-8'), $m)) { return ['ads_review', 'risk_title:'.$m[0]]; }
        if (!in_array($root, self::SAFE_ROOTS, true)) { return ['ads_review', 'unknown_root:'.$root]; }
        return ['ads_ok', 'safe_root:'.$root];
    }

    public static function context(array $c, $now = null)
    {
        $now = $now ?? time();
        $k = self::contextKey($c);
        $cached = is_array(self::$reg) && isset(self::$reg[$k]) ? self::$reg[$k] : null;
        if ($cached === null || ($now - $cached['_loaded_at']) > self::CACHE_TTL || $now < $cached['_loaded_at']) {
            $f = self::files($c);
            self::$reg = (array)self::$reg; self::$pol = (array)self::$pol; self::$stats = (array)self::$stats;
            self::$reg[$k] = self::normalizeRegister(self::load($f['reg'], self::REGISTER_MAX_AGE, $now), $c, $now) + ['_loaded_at' => $now];
            self::$pol[$k] = self::normalizePolicy(self::load($f['pol'], self::POLICY_MAX_AGE, $now), self::load($f['sticky'], PHP_INT_MAX, $now), $c);
            if (!isset(self::$stats[$k])) {
                if (!self::$stats) { register_shutdown_function([__CLASS__, 'summary']); }
                self::$stats[$k] = ['file' => $f['summary'], 'counts' => []];
            }
        }
        return ['register' => self::$reg[$k], 'policy' => self::$pol[$k], 'key' => $k];
    }
    public static function label(array $row, array $c)
    {
        $ctx = self::context($c);
        list($label, $why) = self::decide($row, $c, $ctx);
        $s = $label.'|'.preg_replace('/:.*/', '', $why);
        self::$stats[$ctx['key']]['counts'][$s] = (self::$stats[$ctx['key']]['counts'][$s] ?? 0) + 1;
        return $label;
    }
    public static function summary()
    {
        foreach ((array)self::$stats as $k => $s) {
            if (empty($s['counts'])) { continue; }
            $r = self::$reg[$k] ?? []; $p = self::$pol[$k] ?? []; $x = explode('|', $k);
            try {
                self::writeAtomic($s['file'], ['rules' => self::RULES, 'evaluated_at' => gmdate('c'), 'context' => $x[0].'~'.$x[1].'~'.$x[2],
                    'register' => ['ok' => $r['ok'] ?? false, 'why' => $r['why'] ?? ''],
                    'policy' => ['ok' => $p['ok'] ?? false, 'why' => $p['why'] ?? '', 'hold_count' => count($p['hold'] ?? []), 'unverified' => count($p['unverified'] ?? [])],
                    'counts' => $s['counts']]);
            } catch (\RuntimeException $e) { error_log('AdsGate summary: '.$e->getMessage()); }
        }
    }
    /** Stage JSON into a tmp file next to the target; returns tmp path. Throws on any failure. */
    private static function stage($file, array $data)
    {
        $json = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        if ($json === false) { throw new \RuntimeException('json_encode failed for '.basename($file)); }
        $tmp = $file.'.tmp.'.getmypid(); $old = umask(0077);
        $n = @file_put_contents($tmp, $json, LOCK_EX);
        umask($old);
        if ($n !== strlen($json)) { @unlink($tmp); throw new \RuntimeException('write failed: '.basename($tmp)); }
        return $tmp;
    }
    private static function commit($tmp, $file)
    {
        if (!@rename($tmp, $file)) { @unlink($tmp); throw new \RuntimeException('rename failed: '.basename($file)); }
    }
    public static function writeAtomic($file, array $data) { self::commit(self::stage($file, $data), $file); return true; }

    public static function isPolicyFlag(array $i)
    {
        $code = strtolower((string)($i['code'] ?? ''));
        if (strpos($code, 'policy_violation') !== false) { return true; }
        return strpos($code, 'policy') !== false && ($i['severity'] ?? '') === 'DISAPPROVED';
    }
    /** Validates one product status. Returns [verified(bool), flags(array code=>true)]. */
    private static function statusOf(array $p)
    {
        if (!isset($p['productStatus']) || !is_array($p['productStatus']) || self::isList($p['productStatus']) && $p['productStatus'] !== []) { return [false, []]; }
        $issues = $p['productStatus']['itemLevelIssues'] ?? [];
        if (!self::isList($issues)) { return [false, []]; }
        $flags = [];
        foreach ($issues as $i) {
            if (!is_array($i) || !is_string($i['code'] ?? null) || $i['code'] === '') { return [false, []]; }
            if (self::isPolicyFlag($i)) { $flags[$i['code']] = true; }
        }
        return [true, $flags];
    }

    /**
     * Daily sweep for ONE context. Rejected (exception, nothing written) on: HTTP error, unknown page keys, non-final page
     * without products, repeated token, product without offerId, foreign account, >0.5 % malformed statuses, fewer than
     * MIN_PRODUCTS unique products, or coverage drop >10 % against the last COMPLETE snapshot of the SAME context.
     * Release of a known hold only for a product seen in this sweep with a verified status and no policy flag.
     * Known holds = sticky store + previous snapshot (any version, migration) + this sweep.
     */
    public static function policySweep(array $c, $client, $now = null)
    {
        $now = $now ?? time();
        $f = self::files($c);
        $base = 'https://merchantapi.googleapis.com/products/v1/accounts/'.$c['account_id'].'/products?pageSize=1000';
        $seen = []; $flags = []; $unver = []; $token = ''; $pages = 0; $tokens = []; $foreign = 0; $rows = 0; $dups = 0;
        do {
            list($http, $body) = $client->request($base.($token !== '' ? '&pageToken='.rawurlencode($token) : ''));
            if ($http !== 200 || !is_array($body)) { throw new \RuntimeException('Policy sweep HTTP '.$http.' on page '.$pages); }
            if (array_diff(array_keys($body), self::PAGE_KEYS)) { throw new \RuntimeException('Policy sweep: unknown keys on page '.$pages); }
            if (isset($body['products']) && (!self::isList($body['products']) || $body['products'] === [])) { throw new \RuntimeException('Policy sweep: bad products on page '.$pages); }
            if (!isset($body['products']) && ($pages === 0 || isset($body['nextPageToken']))) { throw new \RuntimeException('Policy sweep: page '.$pages.' without products'); }
            if (isset($body['nextPageToken']) && (!is_string($body['nextPageToken']) || $body['nextPageToken'] === '')) { throw new \RuntimeException('Policy sweep: bad page token'); }
            foreach ($body['products'] ?? [] as $p) {
                $rows++;
                if (!is_array($p) || !is_string($p['offerId'] ?? null) || $p['offerId'] === '') { throw new \RuntimeException('Policy sweep: product without offerId on page '.$pages); }
                if (!is_string($p['name'] ?? null) || strpos($p['name'], 'accounts/'.$c['account_id'].'/') !== 0) { $foreign++; continue; }
                if (($p['feedLabel'] ?? '') !== $c['feed_label'] || ($p['contentLanguage'] ?? '') !== $c['content_language']) { continue; }
                $id = self::identity($c, $p['offerId']);
                if (isset($seen[$id])) { $dups++; }
                $seen[$id] = true;
                list($ok, $fl) = self::statusOf($p);
                if (!$ok) { $unver[$id] = true; continue; }
                foreach ($fl as $code => $_) { $flags[$id][$code] = true; }   // duplicates: hold wins (union)
            }
            $token = (string)($body['nextPageToken'] ?? ''); $pages++;
            if ($token !== '' && isset($tokens[$token])) { throw new \RuntimeException('Policy sweep: repeated page token'); }
            $tokens[$token] = true;
            if ($pages > 200) { throw new \RuntimeException('Policy sweep: too many pages'); }
        } while ($token !== '');
        $n = count($seen);
        if ($foreign > 0) { throw new \RuntimeException('Policy sweep: '.$foreign.' products without own account name'); }
        if ($n < self::MIN_PRODUCTS) { throw new \RuntimeException('Policy sweep: only '.$n.' unique products read'); }
        if (count($unver) > self::MAX_UNVERIFIED_SHARE * $n) { throw new \RuntimeException('Policy sweep: '.count($unver).' malformed product statuses'); }
        $prevL = self::load($f['pol'], PHP_INT_MAX, $now); $prev = $prevL['data'];
        if (is_array($prev) && ($prev['complete'] ?? null) === true && self::bound($prev, $c) && is_int($prev['products_read'] ?? null)
            && $n < (1 - self::MAX_COVERAGE_DROP) * $prev['products_read']) {
            throw new \RuntimeException('Policy sweep: coverage dropped from '.$prev['products_read'].' to '.$n);
        }
        $context = self::ctxOf($c);
        $snapHold = array_map('array_keys', $flags);
        $stL = self::load($f['sticky'], PHP_INT_MAX, $now); $st = $stL['data'];
        if (is_file($f['sticky']) && !is_array($st)) { throw new \RuntimeException('Policy sweep: sticky store unreadable; refusing to rebuild it'); }
        $known = self::holdsOf($st, $c) + self::holdsOf($prev, $c);   // migration: prior snapshot holds join the sticky set
        $log = is_array($st) && self::isList($st['released'] ?? null) ? $st['released'] : [];
        $stHold = $known; $released = 0;
        foreach ($known as $id => $codes) {
            if (isset($seen[$id]) && !isset($unver[$id]) && !isset($snapHold[$id])) { $log[] = ['id' => $id, 'codes' => $codes, 'released_at' => gmdate('c', $now)]; unset($stHold[$id]); $released++; }
        }
        foreach ($snapHold as $id => $codes) { $stHold[$id] = $codes; }
        // Unverified products that were held stay held via $stHold; unverified products without hold get review via snapshot list.
        $tmpSticky = self::stage($f['sticky'], ['version' => self::SCHEMA, 'generated_at' => gmdate('c', $now), 'context' => $context,
            'hold' => (object)$stHold, 'released' => array_slice($log, -500)]);
        try {
            $tmpSnap = self::stage($f['pol'], ['version' => self::SCHEMA, 'generated_at' => gmdate('c', $now), 'context' => $context, 'complete' => true,
                'source' => 'Merchant API products.list productStatus', 'products_read' => $n, 'rows' => $rows, 'pages' => $pages, 'duplicates' => $dups,
                'hold' => (object)$snapHold, 'unverified' => array_keys($unver)]);
        } catch (\RuntimeException $e) { @unlink($tmpSticky); throw $e; }
        try { self::commit($tmpSticky, $f['sticky']); } catch (\RuntimeException $e) { @unlink($tmpSnap); throw $e; }
        self::commit($tmpSnap, $f['pol']);
        return ['products_read' => $n, 'hold' => count($snapHold), 'sticky_hold' => count($stHold), 'released' => $released, 'unverified' => count($unver), 'pages' => $pages];
    }
}
