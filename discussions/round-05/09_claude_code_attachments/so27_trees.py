#!/usr/bin/env python3
"""Round 5 move 9: executable SO27 Shopping trees + checker (R5-CHATGPT-19/20).
Shape (Google Ads API): ONE optional campaign listing scope (CampaignCriterion, equality only) per campaign; ONE ad group per
campaign with a listing-group tree. Every SUBDIVISION has an explicit Others unit. Order on every included path:
custom_label4 (ads_ok only) -> [custom_label0 allowlist] -> custom_label3 (paid bands only) -> item_id (selected IDs) -> leaf.
So price is always checked BEFORE any selected item_id. Others / unknown / missing values are EXCLUDED at each level.
Outputs: so27_trees.json (spec for the executor) and synthetic_cases_results.csv. The same evaluate() is ported 1:1 to JS for the
read-only live check (live_check.js). Nothing is applied."""
import csv, itertools, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PAID = ['p_20_49', 'p_50_199', 'p_200_499', 'p_500_1499', 'p_1500_2999', 'p_3000_4999', 'p_5000_plus']
EXCL = {'excluded': True}

def band_node(bids, items=None, items_bid=None, item_others='band'):
    """label3 subdivision; under each paid band an optional item_id subdivision."""
    kids = []
    for b in PAID:
        if items:
            units = [{'value': i, 'cpc': (items_bid[i] if isinstance(items_bid, dict) else items_bid)} for i in items]
            units.append({'value': None, **({'cpc': bids[b]} if item_others == 'band' else EXCL)})
            kids.append({'value': b, 'dimension': 'item_id', 'children': units})
        else:
            kids.append({'value': b, 'cpc': bids[b]})
    kids.append({'value': None, **EXCL})          # p_lt20, p_invalid, legacy p_0_49, missing, unknown
    return {'dimension': 'custom_label3', 'children': kids}

def gate(inner):
    return {'dimension': 'custom_label4', 'children': [{'value': 'ads_ok', **inner}, {'value': None, **EXCL}]}

def by_label0(values, make):
    return {'dimension': 'custom_label0', 'children': [{'value': v, **make(v)} for v in values] + [{'value': None, **EXCL}]}

B = lambda a, b, c, d: {'p_20_49': a, 'p_50_199': b, 'p_200_499': c, 'p_500_1499': d, 'p_1500_2999': d, 'p_3000_4999': d, 'p_5000_plus': d}
SMART = ['104421', '46205', '46206', '46208', '64627', '46201', '46204', '47769', '102735', '102736', '106477', '106476', '102737', '102741', '102738', '102740', '104500', '64818']
TEL_HERO = ['64085', '26955', '26957', '64962', '47606', '64878', '64732', '26960', '47376', '64077', '64114', '47633', '27063', '47488', '26457']
BIN_HERO = ['33079', '26929', '26757', '100719', '26940', '26945', '104247']; BIN_LOW = ['31171', '26799', '26772']
MIC_HERO = ['34540', '26879', '26873', '26374', '25882', '106996', '34531']
JUN = ['25828', '64089', '26947', '102391']
BIN_L0 = ['ďalekohľady a binokuláre', 'monokuláre', 'spektívy', 'príslušenstvo k ďalekohľadom', 'príslušenstvo k spektívom']
THERM_L0 = ['termovízie', 'nočné videnie']
CATCH_L0 = ['montáže a statívy', 'astronomické filtre', 'príslušenstvo pre mikroskopy', 'astronomické príslušenstvo', 'astrofotografia', 'refraktometre',
            'meracie nástroje', 'fotopasce', 'statívy', 'meteostanice', 'príslušenstvo pre fotopasce', 'okuláre na teleskopy', 'lupy', 'akčné kamery',
            'príslušenstvo pre polarimetre', 'polarimetre', 'domáce planetáriá', 'spektroskopy', 'nástroje na čistenie optiky', 'kompasy a buzoly', 'drony']

tel_bids = {**{i: 0.55 for i in TEL_HERO}, **{i: 0.40 for i in SMART}}
bin_bids = {**{i: 0.45 for i in BIN_HERO}, **{i: 0.20 for i in BIN_LOW}}
TREES = {
 'SO27 | SHOP | Teleskopy': {'scope': {'custom_label0': 'teleskopy a hvezdárske ďalekohľady'}, 'tree': gate(band_node(B(0.30, 0.40, 0.45, 0.50), TEL_HERO + SMART, tel_bids))},
 'SO27 | SHOP | Ďalekohľady': {'scope': {}, 'tree': gate(by_label0(BIN_L0, lambda v: band_node(B(0.20, 0.35, 0.40, 0.40), BIN_HERO + BIN_LOW, bin_bids) if v == BIN_L0[0] else band_node(B(0.20, 0.35, 0.40, 0.40))))},
 'SO27 | SHOP | Mikroskopy': {'scope': {'custom_label0': 'mikroskopy'}, 'tree': gate(band_node(B(0.20, 0.35, 0.40, 0.40), MIC_HERO, 0.45))},
 'SO27 | SHOP | Termovízie (pozorovanie)': {'scope': {}, 'tree': gate(by_label0(THERM_L0, lambda v: band_node(B(0.25, 0.30, 0.30, 0.40))))},
 'SO27 | SHOP | Junior výber': {'scope': {'custom_label0': 'sonata junior lab'}, 'tree': gate(band_node(B(0.25, 0.25, 0.25, 0.25), JUN, 0.25, item_others='excluded'))},
 'SO27 | SHOP | Príslušenstvo a ostatné': {'scope': {}, 'tree': gate(by_label0(CATCH_L0, lambda v: band_node(B(0.15, 0.25, 0.35, 0.35))))},
}

def evaluate(tree, p):
    """Walk the tree; returns ('BID', cpc, path) or ('EXCLUDED', None, path). Others = no sibling value matches (case-insensitive)."""
    node, path = tree, []
    while 'dimension' in node:
        dim = node['dimension']; val = (p.get(dim) or '').strip().lower()
        nxt = next((ch for ch in node['children'] if ch['value'] is not None and ch['value'].lower() == val), None)
        if nxt is None:
            nxt = next(ch for ch in node['children'] if ch['value'] is None)
        path.append(f"{dim}={nxt['value'] if nxt['value'] is not None else '*others*'}")
        node = nxt
    return ('EXCLUDED', None, path) if node.get('excluded') else ('BID', node['cpc'], path)

def route(p):
    """All campaigns whose scope matches and whose tree gives a BID leaf."""
    out = []
    for name, c in TREES.items():
        if all((p.get(k) or '').lower() == v.lower() for k, v in c['scope'].items()):
            r = evaluate(c['tree'], p)
            if r[0] == 'BID':
                out.append((name, r[1], ' > '.join(r[2])))
    return out

def check_structure(node, depth=0):
    if 'dimension' not in node:
        return
    vals = [c['value'] for c in node['children']]
    assert vals.count(None) == 1, f'exactly one Others at {node["dimension"]}'
    assert len(set(v.lower() for v in vals if v)) == len([v for v in vals if v]), 'duplicate values'
    assert depth < 7, 'too deep'
    for c in node['children']:
        check_structure(c, depth + 1)

def synthetic():
    rows, bad = [], 0
    ids = ['64085', '25828', '104421', '99999']
    l0s = ['teleskopy a hvezdárske ďalekohľady', 'sonata junior lab', 'mikroskopy', 'monokuláre', 'termovízie', 'lupy', 'neznáma kategória', '']
    l4s = ['ads_ok', 'ads_review', 'ads_hold', '']
    l3s = ['p_lt20', 'p_20_49', 'p_50_199', 'p_invalid', 'p_0_49', '']
    for i, l0, l4, l3 in itertools.product(ids, l0s, l4s, l3s):
        p = {'item_id': i, 'custom_label0': l0, 'custom_label4': l4, 'custom_label3': l3}
        r = route(p)
        allowed = l4 == 'ads_ok' and l3 in PAID and l0 in ([TREES['SO27 | SHOP | Teleskopy']['scope']['custom_label0'], 'mikroskopy', 'monokuláre', 'termovízie', 'lupy']
                                                             + (['sonata junior lab'] if i in JUN else []))
        ok = (len(r) <= 1) and (bool(r) == allowed)
        bad += not ok
        rows.append(dict(item_id=i, label0=l0 or '(missing)', label4=l4 or '(missing)', label3=l3 or '(missing)', routes=len(r),
                         campaign=r[0][0] if r else '-', cpc=r[0][1] if r else '-', path=r[0][2] if r else '-', expected='BID' if allowed else 'EXCLUDED', result='PASS' if ok else 'FAIL'))
    return rows, bad

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    for c in TREES.values():
        check_structure(c['tree'])
    json.dump({'shape': 'one optional campaign listing scope (equality) + one ad group with this listing-group tree per campaign; value null = Others',
               'campaigns': TREES}, open(os.path.join(HERE, 'so27_trees.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    rows, bad = synthetic()
    with open(os.path.join(HERE, 'synthetic_cases_results.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    for r in rows:
        if r['result'] == 'FAIL':
            print('FAIL', r)
    print('structure OK;', 'synthetic cases', len(rows) - bad, '/', len(rows), 'PASS')
    return bad

if __name__ == '__main__':
    sys.exit(1 if main() else 0)
