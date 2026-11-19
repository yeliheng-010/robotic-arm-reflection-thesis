"""归纳动作边界与接触变化；保留原样本行号供复核。"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def bilateral(row, source):
    return all(source in row['pads'][side] for side in ('left', 'right'))


def witness(row, source):
    tcp = row['tcp']
    delta = [row['source'][i]-tcp[i][3] for i in range(3)]
    local = [sum(tcp[i][j]*delta[i] for i in range(3)) for j in range(3)]
    contact_rows = [c for c in row['contacts'] if source in c['roots']]
    forces = {}
    for contact in contact_rows:
        for name in contact['geoms']:
            if 'pad' in name:
                forces[name] = forces.get(name, 0.)+contact['force'][0]
    return dict(line=row['line'], time=row['time'], action=row['action'], event=row['event'],
                source=row['source'], tcp=[tcp[i][3] for i in range(3)], local_source=local,
                tracking_error=math.dist([tcp[i][3] for i in range(3)],
                                         [row['command'][i][3] for i in range(3)]),
                bilateral=bilateral(row, source), pads=row['pads'], normal_forces=forces,
                closure=row['closure'], control=row['ctrl'][-1],
                pad_z=[min(g['low'][2] for g in row['pad_geometry']),
                       max(g['high'][2] for g in row['pad_geometry'])],
                object_z=[min(g['low'][2] for g in row['source_geometry']),
                          max(g['high'][2] for g in row['source_geometry'])])


def action_stats(rows, source):
    result = {}
    for action in dict.fromkeys(row['action'] for row in rows):
        subset = [row for row in rows if row['action'] == action]
        result[action] = dict(samples=len(subset), start=witness(subset[0], source),
            end=witness(subset[-1], source),
            max_source_z=max(row['source'][2] for row in subset),
            min_source_z=min(row['source'][2] for row in subset),
            all_bilateral=all(bilateral(row, source) for row in subset))
    return result


def case_summary(case):
    item = case['item']
    directory = ROOT/'physics'/item['id']
    rows = [dict(json.loads(line), line=i+1) for i, line in
            enumerate((directory/'contacts.jsonl').read_text().splitlines())]
    checks = [row for row in rows if row['event'] == 'check_grasp']
    carry = [row for row in rows if row['action'] == 'move_to_point']
    lost = next((row for row in carry if not bilateral(row, item['source'])), None)
    near_loss = []
    if lost:
        near_loss = [witness(row, item['source']) for row in rows
                     if lost['time']-.06 <= row['time'] <= lost['time']+.04]
    return dict(id=item['id'], index=case['step']['index'], samples=len(rows),
                audit=load(directory/'audit.json'),
                checks=[witness(row, item['source']) for row in checks],
                first_loss=witness(lost, item['source']) if lost else None,
                near_loss=near_loss, actions=action_stats(rows, item['source']),
                final_contacts=rows[-1]['contacts'])


def main():
    manifest = load(ROOT/'manifest.json')
    result = [case_summary(case) for case in manifest['cases']]
    with (ROOT/'contact_summary.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps([dict(id=r['id'], samples=r['samples'],
                          first_loss=r['first_loss']) for r in result], ensure_ascii=False))


if __name__ == '__main__':
    main()
