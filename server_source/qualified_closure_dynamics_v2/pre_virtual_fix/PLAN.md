# 来源分类修复与零积分真实导入验证

本轮仅修复并验证来源登记，不授权动力学、不创建场景、不登记轨迹claim。v1源码、授权、claim consumed=1和6832失败保持。新版本复用冻结的初态/控制/记录模块，只替换来源分类、准备与入口授权顺序。

- [ ] 先以Slurm回归测试覆盖嵌套虚拟环境、伪同名目录、解析路径/符号链接、项目/依赖文件变化、虚拟模块与缺授权。
- [ ] 新provenance.py按当前解释器sysconfig/site的真实根目录分类，记录每个实际导入文件及缓存哈希、模块映射；依赖不可直接忽略。
- [ ] distributions.py登记所属发行包、版本、METADATA/RECORD哈希及导入文件的RECORD校验。标准库和解释器另行绑定，未知真实文件拒绝。
- [ ] guarded_imports.py在导入运行模块前阻断模型/场景构造和积分；preflight.py登记真实导入集合；独立进程audit_imports.py重新加载并核验，不重复实验。
- [ ] entry.py先校验独立授权及来源，在零积分保护下完成真实导入核验，然后才能消耗新claim。本轮缺授权且没有execute.sbatch。
- [ ] 通过Slurm定向测试、真实导入和独立核验后冻结最终来源，完成自审、归档和CURRENT_STATUS更新。

主要风险：动态虚拟模块不能当作真实路径；未知真实源码不能因没有找到文件而跳过。包RECORD只验证当前安装，不提供旧运行历史保证。导入验证只覆盖已加载模块和明确预加载的入口模块，不等于完整模型创建、MJB重载或动力学通过。

使用systematic-debugging、executing-plans、test-driven-development、requesting-code-review及verification-before-completion；按项目约束串行实施，不修改旧实验文件或Git状态。
