#!/bin/bash
# Round 5 move 11: rollback scenarios with the REAL old code (v2, live today) and v3.2. Temp dir only.
# usage: bash test_rollback_scenarios.sh <php> <AdsGate_v2.php> <AdsGate_v32.php> <migrate.py> <merge.py>
PHP=$1; V2=$2; V32=$3; MIG=$4; MERGE=$5; N=0; F=0
t(){ N=$((N+1)); if [ "$2" = "$3" ]; then echo "PASS $1 expected=$3 actual=$2"; else F=$((F+1)); echo "FAIL $1 expected=$3 actual=$2"; fi; }
fresh(){ rm -rf "$D"; mkdir -p "$D/catalog-state"; NOW=$(date -u +%FT%TZ)
  echo "{\"version\":2,\"generated_at\":\"$NOW\",\"hold\":[],\"review\":[],\"ok\":[]}" > "$D/ads-review.json"
  echo "{\"version\":2,\"generated_at\":\"$NOW\",\"hold\":{}}" > "$D/ads-policy.json"; }
D=$(mktemp -d)/s
# --- deploy: backup v2 state, migrate register, v3.2 sweep flags X (a hold NOT present in the backup) ---
fresh; mkdir -p "$D.bak"; cp "$D"/ads-*.json "$D.bak/"
python3 "$MIG" "$D/ads-review.json" --account 999000111 --lang sk --feed SK --write >/dev/null
$PHP sweep_cli.php "$V32" "$D" X >/dev/null
t "after deploy: v3.2 labels new hold X" "$($PHP label_cli.php "$V32" "$D" X)" ads_hold
cp -r "$D" "$D.post"
# --- A1: UNSAFE rollback from move-9 plan (restore 5 backups + delete sticky) -> demonstrates the defect ---
cp "$D.bak"/ads-*.json "$D/"; rm -f "$D/ads-policy-holds.json"
t "UNSAFE old rollback (restore backups, delete sticky): X leaks with v2 code" "$($PHP label_cli.php "$V2" "$D" X)" ads_ok
# --- A2: SAFE rollback (move 11): keep current state files, merge holds into register, then old code ---
rm -rf "$D"; cp -r "$D.post" "$D"
python3 "$MERGE" --dir "$D" --account 999000111 --lang sk --feed SK --write >/dev/null
t "SAFE rollback: v2 code sees merged hold X" "$($PHP label_cli.php "$V2" "$D" X)" ads_hold
t "SAFE rollback: v2 still holds X after policy snapshot is 4 days old" "$($PHP label_cli.php "$V2" "$D" X 345600)" ads_hold
rm -rf "$D"; cp -r "$D.post" "$D"; python3 "$MERGE" --dir "$D" --account 999000111 --lang sk --feed SK --write >/dev/null
t "SAFE rollback: v2 clean product unaffected" "$($PHP label_cli.php "$V2" "$D" P5)" ads_ok
t "roll-forward again to v3.2 after merge: X still hold" "$($PHP label_cli.php "$V32" "$D" X)" ads_hold
# --- A3: state unreadable -> merge refuses (exit 2), nothing written ---
rm -rf "$D"; cp -r "$D.post" "$D"; echo '{broken' > "$D/ads-policy-holds.json"; before=$(md5sum < "$D/ads-review.json")
python3 "$MERGE" --dir "$D" --account 999000111 --lang sk --feed SK --write >/dev/null; rc=$?
t "unreadable sticky: merge refuses with exit 2" "$rc" 2
t "unreadable sticky: register unchanged" "$(md5sum < "$D/ads-review.json")" "$before"
# --- B: scope rollback model (state machine of the move-11 plan) ---
python3 - <<'PY' && t "scope rollback model: no review/hold product served in any intermediate state" ok ok || t "scope rollback model" fail ok
products=[('ok','ads_ok'),('rev','ads_review'),('hold','ads_hold')]
def served(camp,p): return camp['status']=='ENABLED' and (('ads_ok_filter' not in camp['scope']) or p[1]=='ads_ok')
legacy={'status':'ENABLED','scope':{'label0','ads_ok_filter'}}
plan=[('PAUSE',None),('REMOVE_SCOPE','ads_ok_filter')]   # move-11 order: pause BEFORE touching the filter; no re-enable without filter
for op,arg in plan:
    if op=='PAUSE': legacy['status']='PAUSED'
    if op=='REMOVE_SCOPE': assert legacy['status']=='PAUSED'; legacy['scope'].discard(arg)
    assert not any(served(legacy,p) for p in products if p[1]!='ads_ok'), (op, legacy)
# re-enable is allowed only after the filter is restored and read back
legacy['scope'].add('ads_ok_filter'); legacy['status']='ENABLED'
assert not any(served(legacy,p) for p in products if p[1]!='ads_ok')
assert served(legacy,('ok','ads_ok'))
PY
echo "$((N-F))/$N PASS"; rm -rf "$(dirname "$D")"; exit $F
