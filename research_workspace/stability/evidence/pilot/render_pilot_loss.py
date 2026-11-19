import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path('/home/yeliheng/grasp_server/stability_20261019/pilot_sft_v1')
r=json.loads((root/'result.json').read_text())
fig,axes=plt.subplots(1,2,figsize=(10,3.7),gridspec_kw={'width_ratios':[2,1]})
axes[0].plot([u['step'] for u in r['updates']],[u['loss'] for u in r['updates']],marker='o',markersize=3,color='#2563eb')
axes[0].set(xlabel='Optimizer update (1 epoch, 163 examples)',ylabel='Assistant-token cross entropy',yscale='log',title='Training: per-batch loss (different examples)')
values=[r['validation_before']['loss'],r['validation_after']['loss']]
axes[1].plot(['Before','After'],values,'o-',color='#059669')
axes[1].set(yscale='log',ylabel='Assistant-token cross entropy',title='Validation: same 48 examples')
for i,value in enumerate(values):
 axes[1].annotate(f'{value:.6g}',(i,value),xytext=(12,-15) if i==0 else (-8,8),textcoords='offset points',ha='left' if i==0 else 'right')
for ax in axes:
 ax.grid(alpha=.2)
 ax.spines[['top','right']].set_visible(False)
fig.suptitle('Qwen3.5-4B / QLoRA pilot / rule-generated supervision',fontsize=12)
fig.text(.5,.01,'Text imitation metrics only. Test set sealed; robot task success not evaluated.',ha='center',fontsize=9)
fig.tight_layout(rect=[0,.05,1,.95])
fig.savefig(root/'pilot_loss.png',dpi=180,bbox_inches='tight')
fig.savefig(root/'pilot_loss.svg',bbox_inches='tight')
print('Saved pilot_loss.png and pilot_loss.svg')
