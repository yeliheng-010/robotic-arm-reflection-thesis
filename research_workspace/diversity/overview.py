"""将实际预检图像和深度误差绘成四档对照，供人工检查。"""
import cv2
import numpy as np

CELL = 320
TITLE = 34
LEVELS = ('clean', 'light', 'medium', 'strong')


def depth_picture(path):
    with np.load(path) as depth:
        valid = np.isfinite(depth['clean']) & (depth['clean'] > 0)
        dropped = valid & (depth['noisy'] == 0)
        error = np.where(valid & ~dropped, np.abs(depth['clean']-depth['noisy']), 0)
    scale = np.clip(error/.015*255, 0, 255).astype(np.uint8)
    image = cv2.applyColorMap(scale, cv2.COLORMAP_TURBO)
    image[dropped] = [255, 0, 255]
    return image


def make_overview(root, rows):
    scene_grid = np.full((4*(CELL+TITLE), 4*CELL, 3), 255, dtype=np.uint8)
    noise_grid = scene_grid.copy()
    sources = list(dict.fromkeys(row['task']['source'] for row in rows))
    for row in rows:
        task = row['task']
        y = sources.index(task['source'])*(CELL+TITLE)
        x = LEVELS.index(task['level'])*CELL
        directory = root/f"{row['case']:02d}"
        rgb = cv2.imread(str(directory/'scene.png'))
        error = depth_picture(directory/'depth.npz')
        for grid, image in ((scene_grid, rgb), (noise_grid, error)):
            grid[y+TITLE:y+TITLE+CELL, x:x+CELL] = cv2.resize(image, (CELL, CELL))
            cv2.putText(grid, f"{task['source']} / {task['level']}", (x+5, y+22),
                        cv2.FONT_HERSHEY_SIMPLEX, .43, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.imwrite(str(root/'scene-grid.jpg'), scene_grid)
    cv2.imwrite(str(root/'depth-noise-grid.jpg'), noise_grid)
