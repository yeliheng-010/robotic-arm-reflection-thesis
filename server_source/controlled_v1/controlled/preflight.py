"""重用已验证的渲染预检，仅替换本轮配置与独立输出目录。"""
import json
import os
from unittest.mock import patch
import cv2
import numpy as np
from diversity import preflight as previous
from diversity.overview import depth_picture
from stability.collection_status import atomic
from controlled.config import GROUPS, tasks, scenario
from controlled.freeze import verify
from controlled.worker import ROOT

CELL, TITLE = 240, 32


def overview(directory, rows):
    selected = [row for row in rows if row['task']['fault'] == 'none']
    sources = list(dict.fromkeys(row['task']['source'] for row in selected))
    scene = np.full((len(sources)*(CELL+TITLE), len(GROUPS)*CELL, 3), 255, dtype=np.uint8)
    noise = scene.copy()
    for row in selected:
        task = row['task']
        x = GROUPS.index(task['level'])*CELL
        y = sources.index(task['source'])*(CELL+TITLE)
        path = directory/f"{row['case']:02d}"
        for grid, picture in ((scene, cv2.imread(str(path/'scene.png'))), (noise, depth_picture(path/'depth.npz'))):
            grid[y+TITLE:y+TITLE+CELL, x:x+CELL] = cv2.resize(picture, (CELL, CELL))
            cv2.putText(grid, task['source']+'/'+task['level'], (x+3, y+20),
                        cv2.FONT_HERSHEY_SIMPLEX, .35, (0, 0, 0), 1)
    cv2.imwrite(str(directory/'scene-grid.jpg'), scene)
    cv2.imwrite(str(directory/'depth-grid.jpg'), noise)


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Render through Slurm'
    verify()
    directory = ROOT/'preflight'
    directory.mkdir(exist_ok=False)
    rows = []
    with patch.object(previous, 'ROOT', directory), patch.object(previous, 'scenario', scenario):
        for case, task in enumerate(tasks()):
            rows.append(previous.check(case, task))
            atomic(directory/'progress.json', dict(completed=len(rows), expected=48))
            print(json.dumps({k: rows[-1][k] for k in ('case', 'passed', 'target_visible_pixels')}), flush=True)
    verify()
    result = dict(passed=all(r['passed'] for r in rows), cases=len(rows), rows=rows,
                  test_used=False, job=os.environ['SLURM_JOB_ID'])
    atomic(directory/'result.json', result)
    overview(directory, rows)
    assert result['passed'], 'Preserve failed preflight; do not launch pilot'


if __name__ == '__main__':
    main()
