<?php
namespace SonataMerchant;

/**
 * Ads admission gate for custom_label_4, rule version ads-gate-v3 (2026-11-26, Claude Code, round 5 move 5).
 * REPOSITORY PATCH ONLY - not deployed. Fixes the 7 regressions found by ChatGPT in move 4 (R5-CHATGPT-08/09) and the
 * static-audit items (schema, context cache, pagination, coverage, atomic write, partial snapshot).
 *
 * Decision order (first match wins):
 *   1 manual hold (register)                                  -> ads_hold
 *   2 Google policy hold, fresh OR stale (sticky)             -> ads_hold
 *   3 required fields missing/invalid (title, type, https link, positive price) -> ads_review   (also blocks manual ok)
 *   4 register invalid/expired/wrong context                  -> ads_review
 *   5 policy snapshot invalid/expired/incomplete              -> ads_review
 *   6 manual review (also when a manual ok exists = conflict)  -> ads_review
 *   7 manual ok: complete entry + fingerprint matches          -> ads_ok, otherwise ads_review
 *   8 risk root / risk title / unknown root                    -> ads_review
 *   9 safe root                                                -> ads_ok
 * Sticky hold: a hold seen in ANY policy snapshot (also expired) and in ads-policy-holds.json keeps the product on hold until a
 * later COMPLETE sweep for the same context no longer reports it (explicit release, logged with timestamp).
 */
final class AdsGate
{
    const RULES = 'ads-gate-v3';
    const SCHEMA = 3;
    const SAFE_ROOTS = [6183, 1970, 5883, 1969, 1968, 1724, 1971, 1963, 1984, 1976, 1960, 1964, 5877, 1978, 6054, 6160, 6161,
                        5827, 5825, 5197, 1965, 5979, 1721, 5983, 1718, 5288, 1958, 1962];
    const RISK_ROOTS = [1975, 5826, 1722, 5196, 1974, 5831, 6184, 5127, 5829, 4767, 5828, 5870, 5995];
    const RISK_TITLE = '/(?<![\p{L}\d])(zbra[nň]\p{L}*|pušk\p{L}*|pusk\p{L}*|guľovnic\p{L}*|gulovnic\p{L}*|vzduchovk\p{L}*|picatinny|weaver|tlmi[čc]\p{L}*|clip[- ]?on|predsádk\p{L}*|predsadk\p{L}*|kolimátor\p{L}*|red ?dot|rifle|weapon|airsoft|nábo[jň]\p{L}*|kalibr(?!ác|ač)\p{L}*)/u';
    const REGISTER_MAX_AGE = 30 * 86400;
    const POLICY_MAX_AGE = 3 * 86400;
    const OK_ENTRY_FIELDS = ['id', 'fingerprint', 'author', 'reason', 'evidence', 'date'];
    const MIN_PRODUCTS = 1000;          // absolute floor for a sweep to count as complete
    const MAX_COVERAGE_DROP = 0.10;     // a sweep reading >10 % fewer unique products than the last complete one is partial

    // Caches keyed by context (merchant|lang|feed|channel|files). Tests may reset them to null.
    private static $reg = null; private static $pol = null; private static $stats = [];

    public static function identity(array $c, $offerId)
    {
        return $c['account_id'].'~ONLINE~'.$c['content_language'].'~'.$c['feed_label'].'~'.$offerId;
    }
    /** Fingerprint covers everything a manual decision depends on: title, product type, main category AND its root. */
    public static function fingerprint(array $row)
    {
        return substr(hash('sha256', implode('|', [
            mb_strtolower(trim((string)($row['title'] ?? '')), 'UTF-8'),
            (string)($row['product_type'] ?? ''),
            (string)($row['main_category_id'] ?? ''),
            (string)($row['main_root_id'] ?? ''),
        ])), 0, 16);
    }
    private static function contextKey(array $c)
    {
        $dir = dirname((string)($c['state_dir'] ?? ''));
        return implode('|', [$c['account_id'] ?? '', $c['content_language'] ?? '', $c['feed_label'] ?? '', 'ONLINE',
            $c['ads_review_file'] ?? $dir.'/ads-review.json', $c['ads_policy_file'] ?? $dir.'/ads-policy.json']);
    }
    private static function files(array $c)
    {
        $dir = dirname((string)$c['state_dir']);
        $pol = $c['ads_policy_file'] ?? $dir.'/ads-policy.json';
        return ['reg' => $c['ads_review_file'] ?? $dir.'/ads-review.json', 'pol' => $pol,
                'sticky' => $c['ads_policy_holds_file'] ?? preg_replace('/\.json$/', '', $pol).'-holds.json',
                'summary' => $dir.'/catalog-state/ads-gate-summary.json'];
    }

    /** Generic loader. Never mixes payload keys with the status: returns [ok, why, data]. Expired files keep data (for sticky holds). */
    private static function load($file, $maxAge, $now)
    {
        if (!is_file($file)) { return ['ok' => false, 'why' => 'missing', 'data' => null]; }
        $d = json_decode((string)file_get_contents($file), true);
        if (!is_array($d) || !is_int($d['version'] ?? null) || $d['version'] < 2 || !is_string($d['generated_at'] ?? null)) {
            return ['ok' => false, 'why' => 'invalid_or_unversioned', 'data' => null];
        }
        $t = strtotime($d['generated_at']);
        if (!$t || $t > $now + 300) { return ['ok' => false, 'why' => 'bad_or_future_timestamp', 'data' => null]; }
        if ($now - $t > $maxAge) { return ['ok' => false, 'why' => 'expired', 'data' => $d]; }
        return ['ok' => true, 'why' => '', 'data' => $d];
    }
    private static function isList($v) { return is_array($v) && ($v === [] || array_keys($v) === range(0, count($v) - 1)); }
    private static function ctxMatches(array $d, array $c)
    {
        // v3 files carry their context; v2 files (no context) are accepted only for the default context they were written for.
        if (!isset($d['context'])) { return ($d['version'] ?? 0) === 2; }
        $x = $d['context'];
        return is_array($x) && (string)($x['account_id'] ?? '') === (string)$c['account_id'] && ($x['content_language'] ?? '') === $c['content_language']
            && ($x['feed_label'] ?? '') === $c['feed_label'] && ($x['channel'] ?? 'ONLINE') === 'ONLINE';
    }

    /** Register -> normalized [ok, why, hold, review, ok_items]. Strict: all three lists must exist and be lists. */
    public static function normalizeRegister(array $l, array $c, $now)
    {
        $out = ['ok' => false, 'why' => $l['why'], 'hold' => [], 'review' => [], 'ok_items' => []];
        $d = $l['data'];
        if (!is_array($d)) { return $out; }
        foreach (['hold', 'review', 'ok'] as $k) { if (!array_key_exists($k, $d) || !self::isList($d[$k])) { $out['why'] = 'schema_'.$k; return $out; } }
        $prefix = self::identity($c, '');
        $idx = function ($list, $needFields) use ($prefix, $now) {
            $o = [];
            foreach ($list as $e) {
                $id = is_array($e) ? (string)($e['id'] ?? '') : (string)$e;
                if ($id === '' || strpos($id, $prefix) !== 0) { continue; }            // other Merchant/feed/language: ignore
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
        // Holds are read even from an expired register (a hold never weakens by age).
        $out['hold'] = $idx($d['hold'], false);
        if (!self::ctxMatches($d, $c)) { $out['why'] = 'context_mismatch'; return $out; }
        if (!$l['ok']) { return $out; }
        $out['review'] = $idx($d['review'], false);
        $out['ok_items'] = $idx($d['ok'], true);
        $out['ok'] = true; $out['why'] = '';
        return $out;
    }
    /** Policy snapshot + sticky store -> normalized [ok, why, hold]. Holds from expired/incomplete snapshots stay. */
    public static function normalizePolicy(array $l, array $sticky, array $c)
    {
        $out = ['ok' => false, 'why' => $l['why'], 'hold' => []];
        $prefix = self::identity($c, '');
        $validHold = function ($d) { return is_array($d) && array_key_exists('hold', $d) && is_array($d['hold']) && ($d['hold'] === [] || !self::isList($d['hold'])); };
        foreach ([$sticky['data'] ?? null, $l['data']] as $d) {
            if (!$validHold($d)) { continue; }
            foreach ($d['hold'] as $id => $codes) { if (strpos((string)$id, $prefix) === 0) { $out['hold'][$id] = (array)$codes; } }
        }
        $d = $l['data'];
        if (!$l['ok'] || !is_array($d)) { return $out; }
        if (!$validHold($d)) { $out['why'] = 'schema_hold'; return $out; }
        if (($d['version'] ?? 0) >= 3 && (empty($d['complete']) || !is_int($d['products_read'] ?? null))) { $out['why'] = 'incomplete_snapshot'; return $out; }
        if (!self::ctxMatches($d, $c)) { $out['why'] = 'context_mismatch'; return $out; }
        $out['ok'] = true; $out['why'] = '';
        return $out;
    }
    /** Required fields for ANY ok (automatic or manual). */
    public static function missingField(array $row)
    {
        foreach (['id', 'title', 'product_type'] as $k) { if (trim((string)($row[$k] ?? '')) === '') { return 'missing_'.$k; } }
        $link = (string)($row['link'] ?? '');
        if (!filter_var($link, FILTER_VALIDATE_URL) || strtolower((string)parse_url($link, PHP_URL_SCHEME)) !== 'https') { return 'invalid_link'; }
        if (!preg_match('/^\s*(\d+(?:[.,]\d{1,2})?)\s*([A-Z]{3})\s*$/', (string)($row['price'] ?? ''), $m) || (float)str_replace(',', '.', $m[1]) <= 0) { return 'invalid_price'; }
        return '';
    }

    /** Pure decision for tests: $ctx = [register, policy] in normalized form. Returns [label, reason]. */
    public static function decide(array $row, array $c, array $ctx)
    {
        $reg = $ctx['register']; $pol = $ctx['policy'];
        $id = self::identity($c, (string)($row['id'] ?? ''));
        if (isset($reg['hold'][$id])) { return ['ads_hold', 'manual_hold']; }
        if (isset($pol['hold'][$id])) { return ['ads_hold', 'google_policy:'.implode(',', (array)$pol['hold'][$id])]; }
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
        if (!is_array(self::$reg) || !isset(self::$reg[$k])) {
            $f = self::files($c);
            self::$reg = (array)self::$reg; self::$pol = (array)self::$pol;
            self::$reg[$k] = self::normalizeRegister(self::load($f['reg'], self::REGISTER_MAX_AGE, $now), $c, $now);
            $sticky = self::load($f['sticky'], PHP_INT_MAX, $now);
            self::$pol[$k] = self::normalizePolicy(self::load($f['pol'], self::POLICY_MAX_AGE, $now), $sticky, $c);
            if (count(self::$reg) === 1) { register_shutdown_function([__CLASS__, 'summary']); }
            self::$stats[$k] = ['file' => $f['summary'], 'counts' => []];
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
            $r = self::$reg[$k] ?? []; $p = self::$pol[$k] ?? [];
            $out = ['rules' => self::RULES, 'evaluated_at' => gmdate('c'), 'context' => explode('|', $k)[0].'~'.explode('|', $k)[1].'~'.explode('|', $k)[2],
                    'register' => ['ok' => $r['ok'] ?? false, 'why' => $r['why'] ?? ''],
                    'policy' => ['ok' => $p['ok'] ?? false, 'why' => $p['why'] ?? '', 'hold_count' => count($p['hold'] ?? [])],
                    'counts' => $s['counts']];
            self::writeAtomic($s['file'], $out);
        }
    }
    /** tmp + rename with error checks; throws on any failure so the caller never believes a partial write succeeded. */
    public static function writeAtomic($file, array $data)
    {
        $json = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        if ($json === false) { throw new \RuntimeException('json_encode failed for '.basename($file)); }
        $tmp = $file.'.tmp.'.getmypid(); $old = umask(0077);
        $n = @file_put_contents($tmp, $json, LOCK_EX);
        umask($old);
        if ($n !== strlen($json)) { @unlink($tmp); throw new \RuntimeException('write failed: '.basename($tmp)); }
        if (!@rename($tmp, $file)) { @unlink($tmp); throw new \RuntimeException('rename failed: '.basename($file)); }
        return $n;
    }

    /** Is this Merchant issue a hard flag? Any *policy_violation (any severity) or a DISAPPROVED policy issue. */
    public static function isPolicyFlag(array $i)
    {
        $code = strtolower((string)($i['code'] ?? ''));
        if (strpos($code, 'policy_violation') !== false) { return true; }
        return strpos($code, 'policy') !== false && ($i['severity'] ?? '') === 'DISAPPROVED';
    }

    /**
     * Daily sweep of Merchant API product statuses for ONE context. Complete-or-nothing:
     * schema per page, repeated page token, duplicates counted once, foreign account names rejected, coverage vs last complete
     * sweep. A failed/partial sweep throws and changes nothing (previous holds stay sticky). A complete sweep writes the
     * snapshot and updates the sticky store: new holds added, holds absent from this complete sweep released with a log entry.
     */
    public static function policySweep(array $c, $client, $now = null)
    {
        $now = $now ?? time();
        $f = self::files($c);
        $base = 'https://merchantapi.googleapis.com/products/v1/accounts/'.$c['account_id'].'/products?pageSize=1000';
        $hold = []; $ids = []; $token = ''; $pages = 0; $tokens = []; $foreign = 0; $rows = 0;
        do {
            list($http, $body) = $client->request($base.($token !== '' ? '&pageToken='.rawurlencode($token) : ''));
            if ($http !== 200 || !is_array($body)) { throw new \RuntimeException('Policy sweep HTTP '.$http.' on page '.$pages); }
            if (isset($body['products']) && !self::isList($body['products'])) { throw new \RuntimeException('Policy sweep: bad schema on page '.$pages); }
            foreach ($body['products'] ?? [] as $p) {
                $rows++;
                if (!is_array($p) || !is_string($p['offerId'] ?? null) || $p['offerId'] === '') { throw new \RuntimeException('Policy sweep: product without offerId on page '.$pages); }
                if (isset($p['name']) && strpos((string)$p['name'], 'accounts/'.$c['account_id'].'/') !== 0) { $foreign++; continue; }
                if (($p['feedLabel'] ?? '') !== $c['feed_label'] || ($p['contentLanguage'] ?? '') !== $c['content_language']) { continue; }
                $id = self::identity($c, $p['offerId']);
                $ids[$id] = true;
                $issues = $p['productStatus']['itemLevelIssues'] ?? [];
                if (!is_array($issues)) { throw new \RuntimeException('Policy sweep: bad itemLevelIssues for '.$p['offerId']); }
                foreach ($issues as $i) { if (is_array($i) && self::isPolicyFlag($i)) { $hold[$id][(string)$i['code']] = true; } }
            }
            $token = (string)($body['nextPageToken'] ?? ''); $pages++;
            if ($token !== '' && isset($tokens[$token])) { throw new \RuntimeException('Policy sweep: repeated page token'); }
            $tokens[$token] = true;
            if ($pages > 200) { throw new \RuntimeException('Policy sweep: too many pages'); }
        } while ($token !== '');
        $seen = count($ids);
        if ($foreign > 0) { throw new \RuntimeException('Policy sweep: '.$foreign.' products of another account in the response'); }
        if ($seen < self::MIN_PRODUCTS) { throw new \RuntimeException('Policy sweep: only '.$seen.' unique products read; not replacing snapshot'); }
        $prev = self::load($f['pol'], PHP_INT_MAX, $now)['data'];
        $prevRead = is_array($prev) ? (int)($prev['products_read'] ?? 0) : 0;
        if ($prevRead > 0 && $seen < (1 - self::MAX_COVERAGE_DROP) * $prevRead) {
            throw new \RuntimeException('Policy sweep: coverage dropped from '.$prevRead.' to '.$seen.'; treated as partial');
        }
        $holdOut = array_map('array_keys', $hold);
        $context = ['account_id' => (string)$c['account_id'], 'content_language' => $c['content_language'], 'feed_label' => $c['feed_label'], 'channel' => 'ONLINE'];
        // Sticky store: add new holds, release only holds that this COMPLETE sweep saw without any policy flag.
        $st = self::load($f['sticky'], PHP_INT_MAX, $now)['data'];
        $stHold = is_array($st['hold'] ?? null) ? $st['hold'] : []; $log = is_array($st['released'] ?? null) ? $st['released'] : [];
        foreach ($stHold as $id => $codes) {
            if (!isset($holdOut[$id]) && isset($ids[$id])) { $log[] = ['id' => $id, 'codes' => $codes, 'released_at' => gmdate('c', $now)]; unset($stHold[$id]); }
        }
        foreach ($holdOut as $id => $codes) { $stHold[$id] = $codes; }
        self::writeAtomic($f['pol'], ['version' => self::SCHEMA, 'generated_at' => gmdate('c', $now), 'context' => $context, 'complete' => true,
            'source' => 'Merchant API products.list productStatus', 'products_read' => $seen, 'rows' => $rows, 'pages' => $pages, 'hold' => (object)$holdOut]);
        self::writeAtomic($f['sticky'], ['version' => self::SCHEMA, 'generated_at' => gmdate('c', $now), 'context' => $context, 'hold' => (object)$stHold,
            'released' => array_slice($log, -500)]);
        return ['products_read' => $seen, 'hold' => count($holdOut), 'sticky_hold' => count($stHold), 'pages' => $pages];
    }
}
