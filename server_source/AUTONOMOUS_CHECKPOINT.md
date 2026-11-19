# 自主推进检查点

## 最新：第八批6154正式112/30，第九批资格运行

6152四片、6153/6154/6155/6158均COMPLETED/0:0。18条件全接受、39尝试；本批dev胶囊首次成功，没有新增dev自然失败。6154正式train112快照/40布局、65恢复/35恢复布局；dev30/13、18/12。SFT97=65+32STOP，dev27=18+9STOP。原门槛只差train8/dev10。6158训练胶囊15快照/5布局、2恢复/2布局，dev仍7/4、5/4。6文本逐份SHA256同步EIGHTH_BATCH_DELIVERY.json，train/dev同manifest.outputs，原图像/NPZ远端。

第九批实际链6163prepare→6164资格四片→6165merge→6166physics_prepare→6167physics_v3→6168merge→6169export→6170next_v3，资格运行。第九批coverage实际6173依赖6169（勿重复提交）。资格66项已完成，27条件/最多189尝试：baseline2，增强train方块13/胶囊8、dev方块3/胶囊1。6167物理v3启动。6008仍collecting，无新Qwen生成或参数更新。

## 最新：第七批正式99/30，第八批资格运行

6142..6147全COMPLETED/0:0。第七批75尝试、22条件（21接受/1完整性拒绝），只续跑3未启动条件。6144正式train99快照/36布局、59恢复/32恢复布局；dev30/13、18/12。SFT88=59+29STOP，dev27=18+9STOP；原门槛缺21/10快照。6146训练胶囊11快照/4布局、2恢复/2布局，dev7/4、5/4。新增8文本哈希同步SEVENTH_BATCH_DELIVERY.json，包含6144、6146、6147及第六批此前未同步的R0_964167安全拒绝（4尝试、首次1自接触采样约200.13N）。

6147完整分母：baseline14尝试/14运动；varied434/369，含15拒绝条件尝试；合计448/383。varied raw成功170/规划79/自然184/outside1，raw不作安全成功率或模型效果。全部拒绝轨迹保留，不隐去执行消耗。

第八批链6148→6149资格四片→6150→6151→6152物理v3四片→6153→6154export→6155next_v3，已核实实际提交账本。6008已读6144，仍collecting，无新增Qwen生成或训练更新。当前waiting属于正在执行，不是目标完成。

## 最新：第六批正式85/27，第七批严格隔离续接

6117正式train85快照/31布局、53恢复/28恢复布局，dev27/12、16/11；SFT79/24。原数量门槛仍缺35/13。6115四片、6116/6117/6118/6121现场sacct全部COMPLETED/0:0。6121训练胶囊9快照/3布局、1恢复/1布局；dev胶囊7/4、5恢复/4布局。六份文本逐份哈希同步SIXTH_BATCH_DELIVERY.json，train/dev同manifest.outputs。

第七批6130_1在R1_964194完整7尝试后的审计失败，其余三片完成。6140只读诊断COMPLETED/0:0：七尝试均缓存source_center y与qpos重建差1.0726079329170801e-6m（原阈值1e-6），静态字段相等、重复forward相等、qpos不变、无采样自接触。确认缓存/重建不一致，但未证明具体更新时序原因，不放宽阈值或修改冻结执行器。

recovery_integrity_v3新增严格隔离；passed=false、完整身份/消耗保留，整条件不计自然快照/恢复。仅识别完整有限且静态精确的动态超限；其他异常继续抛出。6141七测试/三独立入口/长度检查/实际异常拒绝/旧R0_964194五尝试审计完全相等通过，COMPLETED/0:0，源冻结。按review清单自审，未独立代理审查。

旧pending6131/6132/6133由本任务continuation管理器取消并替换；实际新ID读recovery_integrity_v3/continuation/*_submitted.json。复用18个通过条件，隔离964194异常，只续接R1_964202、R1_964211、R0_964221三未启动条件，绝不重跑已消费案例。后续next使用v3，资格/执行器/分布/门槛不变。6008仍等待，尚无训练或新增Qwen生成。

下文是历史记录，以本节和CURRENT_STATUS.md现场更新为准。

第六批再更新：资格12/66全完成；2baseline、训练增强方块5/胶囊3、开发增强各1，最多84尝试。6115_0/1实际RUNNING，已见首个baseline审计接受，其他分片依赖数组上限正常等待。6121覆盖报告已提交勿重复，6008仍collecting。正式仍6106(train75/dev25自然快照)，无训练。

## 第五批完整完成，第六批已提交（最新）

6104/6105/6106/6107/6108/6109全部现场sacct确认COMPLETED/0:0。第五批25资格条件已全部有去向：24审计接受、1安全拒绝964143；新complete_v2不伪造全安全通过。R0_964157七次耗时搜索均collision，完整审计接受但规划拒绝不计自然失败；R1_964157首次成功，三分支共享一次。964160原轨迹新几何审计通过，无重复物理。

正式6106累计：train75自然快照/28布局、49恢复/26恢复布局；dev25自然快照/11布局、15恢复/10恢复布局；两任务三有效类型。SFT train73=49恢复+24STOP，dev22=15恢复+7STOP。原数量门槛只剩train45/dev15自然快照缺口；其他数量/覆盖检查已达。训练胶囊仍5快照/2布局、1恢复/1布局；dev胶囊5/3布局、4恢复/3布局，未新增材料随机化。

6109全分母：baseline10尝试/10运动/10任务成功；varied321尝试/285运动，317接受条件尝试+4拒绝条件尝试；raw task success137（含被拒绝条件，不能叫安全成功率）、planning47、natural136、outside_container1。全量331尝试/295运动；第五批86尝试。非同预算AI效果比较。

第六批实际链：6111 prepare→6112资格四片→6113资格合并→6114物理prepare→6115物理v2四片→6116合并v2→6117export→6118next_v2；全部已提交不重复。**6121**为依赖6117的覆盖v2，实际ID已核对，勿重复。6008已读到6106仍collecting，无训练链，无新Qwen生成/参数更新。

第五批8份核心文本已分块本地同步并逐份SHA256核验；train/dev另与正式manifest.outputs一致。见recovery_dataset_v1/FIFTH_BATCH_DELIVERY.json，包含6106 manifest/train/dev、complete_v2、安全拒绝完整账本、6108覆盖、6109全分母、第五批后扩量决定。图像/NPZ仍远端。

6108自然现场相机：train28布局方位-56.90..56.84、俯仰35.49..74.51、距离0.913..1.427m，三容器各6颜色，但方位正区间占比偏高；dev11布局方位-45.94..49.22、俯仰38.60..73.23、距离0.936..1.472m，BlueBin仅4颜色/SortingTray5颜色。不是均匀覆盖或已验证泛化，不据此挑选开发种子。

最新只读盘点6110（COMPLETED/0:0）：102接受条件/312尝试，train75自然快照/28布局/49恢复/26恢复布局；dev22快照/10布局/15恢复/10恢复布局；两任务三类型。拒绝964143明确未混入，仍partial非正式导出。6104继续R0_964157：首次、顶面两次与下移首次均已返回collision，前两次bridge明确0运动，当前下移加减速；随后还有slow_then_top和R1_964157。无新工程错误，CPU持续增长；不提前计自然失败，不重复已消费尝试。

## 第五批审计修订续接（优先于下文）

6084_2/3最终FAILED/1:0，0/1成功；两问题独立：6101实证964160每字段重建偏差<1微米、组合间隙差1.522微米，旧组合检查未传播输入误差；964143下移和减速分支有真实自接触（1/2采样、最大穿入0.358mm），不可计安全恢复。已有21条件完整执行、19审计通过；仅R1_964143、R0_964150、R0_964157、R1_964157从未启动。

新recovery_integrity_v2已实现/冻结。6102预期红测；6103七测试、四实际入口、964160全7尝试完整审计、旧964135重放方法/接触等价、964143拒绝识别均通过，COMPLETED/0:0。修订保留原每字段1微米与物理约束，仅严谨复算组合误差；任何真实自接触整条件记录audit_rejections，不进入自然/恢复门槛；其他异常仍中止。complete_v2表示全条件去向完备，inventory只含审计接受条件，资格/接受/拒绝/全部消耗分列。不是把拒绝伪装成passed。

旧pending6085/6086/6087/6090/6098已取消，不可再等/恢复。新实际链：6104 resume（复用21旧条件、只执行4个未消费案例）→6105 merge_v2→6106正式export。新next6107/coverage_v2 6108/ig_execution6109已依赖6106提交，实际ID已核对，勿重复；完整记录RESUME_CHAIN.json。6008仍等待正式新导出，不改/重启。后续自动next须走recovery_integrity_v2/next.sbatch（包装旧数量策略，仅替换物理shards/merge/next）；正式覆盖仍collection_coverage_v1/report_v2.sbatch。执行分母须用新recovery_integrity_v2/execution.sbatch，旧report只认complete.json会漏v2批次。

6104最新已复用前10条审计、写出964143拒绝，正在执行第一个未消费胶囊。5份6101/6103核心证据已本地同步且逐份SHA256核验，DELIVERY_6103.json。原协议/旧冻结文件不改，门槛不降；正式累计仍6055(train57/dev20自然快照)，第五批尚未导出。目标仍未完成，持续推进到数据足够及训练门禁通过。

## 最新续接：第五批与训练产物验证

第五批6084尚在运行，最新19/25条件独立审计，6008仍collecting；第五批累计分母报告6098依赖6086，已提交勿重复。期间Jupyter短暂504/502/超时，已恢复200，重连原terminal9，现场队列证明原仿真仍RUNNING；没有重启作业。

第四批6055的6份正式文本已同步且SHA256核验，见FOURTH_BATCH_DELIVERY.json，第四批37次执行尝试（完整complete.json）。新增visual_checkpoint_review_v1：6096预期红测；6097五测试、真实v2入口/源码长度限制和源冻结通过；未来review.sbatch须依赖正式train_v2完成，尚未提交，无真实最终adapter重载。

新增visual_adapter_comparison_v1：6099预期红测；6100七测试/三个入口独立进程实际路径/源长度检查通过，源已冻结。显式启用trained adapter（基础生成器默认关闭adapter，不能沿用），保留相同公开dev输入、两图、贪心/2048/seed42；私有后果仅报告进程读；unknown不作失败，完成STOP单列。prepare/run尚未提交。正式训练与checkpoint review成功后，prepare.sbatch需CHECKPOINT_REVIEW_JOB，run.sbatch依赖prepare。没有新Qwen生成或参数更新。

新增两目录已各自同步source_manifest与红绿日志（DELIVERY_6097/DELIVERY_6100），不得覆盖冻结源；REVIEW.md明确自审和真实未验证边界。当前本地正式累计数据到6055，远端正式也仍6055：train57失败/21布局/38恢复，dev20失败/9布局/14恢复。目标未完成，继续采集、审查数量与覆盖，再跟踪6008训练链。

## 覆盖审查续接（最新）

第四批6053四片/6054/6055/6056/6062已现场sacct确认COMPLETED/0:0。6062按任务细分：train胶囊仍5失败快照/2布局、1恢复/1布局，方块52失败/20布局、37恢复/19布局；dev胶囊5失败/3布局、4恢复，方块15失败/6布局、10恢复。第五批覆盖报告实际**6090**，依赖6086，勿重复提交。6008仍RUNNING/collecting，Qwen新增生成0、参数更新0。

**第四批6055已完整导出：** train57自然快照/21布局、38恢复/20恢复布局；dev20快照/9布局、14恢复/9恢复布局，两任务/三有效类型。SFT train57(38恢复+19STOP)、dev21(14恢复+7STOP)，不能混同监督条数与失败快照数。下一自动链实际为6080 prepare→6081资格→6082合并→6083物理prepare→6084物理→6085合并审计→6086导出→6087next，已提交勿重复；第五批覆盖v2刚依赖6086提交，实际ID待读terminal。6008持续collecting，未训练。第四批文本尚未同步，本地正式数据目前到6038(第三批)。

第四批最新现场：14/66资格通过，最多98尝试；6053已见6/14条件审计，1片完成，0/2片RUNNING、3片待队列。6008实际仍RUNNING约2h18m。前一段计数停顿来自两条六尝试轨迹，不是工程错误，R0_964103已完成顶面恢复与其余探索，R0_964127也已审计。尚无6055正式导出；当前正式数量仍6038的48train/16dev自然快照。

第三批源证据同步完成：THIRD_BATCH_DELIVERY.json共7文件，逐份本地/远端文本SHA256一致，6038 train/dev另与正式manifest.outputs哈希匹配；图片/NPZ仍远端。包含第三批physics complete（58尝试，前三批累计208尝试）。**6062**为已提交的第四批覆盖v2报告，依赖6055；无需重复。6036四片/6037/6038/6039/6042均已现场sacct确认COMPLETED/0:0。

**第三批已完整审计/正式6038导出。** 累计train48自然快照/18布局、32恢复/17恢复布局；dev16快照/7布局、11恢复/7恢复布局。两边两任务/三有效类型。SFT train48=恢复32+STOP16，dev16=恢复11+STOP5。6042新版覆盖报告已产出：train胶囊仍5失败/2布局、1恢复/1布局；方块43失败/17布局、31恢复/16布局。dev964093出现仅直接减速分支成功，顶面/下移分支均未成功，6尝试并完整审计。3批任务/动作多样性检查允许继续，无需引入材料扩展。

第四批自动链已实际提交：6049 prepare→6050资格→6051合并→6052物理prepare→6053物理→6054合并审计→6055导出→6056next，勿重复。下一份覆盖v2刚依赖6055提交，实际ID待读terminal。6008监控仍有效，尚未训练。第三批正式文本尚待同步，本地目前到6016(第二批)；CURRENT_STATUS.md已更新最新数。

第三批资格已全完成：16/66通过、max112尝试；train增强方块8/胶囊3，dev增强方块2/胶囊1，baseline2。6036物理0/1片已启动，已见两条baseline审计。6043前两批执行分母报告已产出：baseline4尝试/4运动/4成功；增强146尝试/134运动，68成功尝试、20规划拒绝、57自然失败、1outside_container单列；增强26/47首次成功、45/47至少一个探索分支成功，不能当AI效果。

交付与挂钩：SECOND_BATCH_DELIVERY.json记录7份第二批正式文本逐份SHA256核对，含6016 train31/dev12的JSONL、manifest、physics complete、6026覆盖、6031验证与扩量决定；图片/NPZ仍远端。**6042**是依赖6038的下一份覆盖v2报告；**6043**是前两批累计执行分母报告。实际ID已确认，不重复提交。

**第二批已完整完成。** 6014四片/6015/6016/6017/6026均现场确认COMPLETED/0:0。6016累计train32自然快照/11布局、21恢复/11恢复布局；dev11快照/5布局、8恢复/5恢复布局；两分区均两任务、三有效类型。正式SFT train31(21恢复+10STOP)、dev12(8恢复+4STOP)。6026按任务分解：train胶囊5失败/2布局、1恢复/1布局，方块27失败/10布局、20恢复；dev胶囊5失败/3布局、4恢复，方块6失败/2布局、4恢复。R1_964054首次自然掉落，三种修正均直接成功，4尝试且完整审计。仍未达数量门槛，真实参数更新0。

第三批自动链实际ID：6032 prepare、6033资格array、6034 merge、6035物理prepare、6036物理array、6037合并审计、6038导出、6039next；全部已提交，6033前两片RUNNING。6008看到6016导出仍collecting。6031为只读覆盖v2验证：六测试、首批真实结果逐字段等价、函数长度及分支上限检查通过。为满足复杂度约束，仅新增coverage_stats_v2/report_v2/verify_v2入口，原已冻结文件不改。下一份覆盖报告(依赖6038)与累计执行分母报告刚提交，需读terminal实际ID。

再更新：6030部分只读盘点47条件/143尝试：train31自然快照/10布局、20恢复/10布局，已覆盖方块/胶囊；dev11快照/5布局、8恢复。两分区均有三种有效类型。R1_964039胶囊7次尝试全collision失败（首次无规划拒绝字段），完整独立审计通过；能计自然失败，不能作恢复标签，train胶囊成功监督仍待补。6014已有21/25审计（0/1/2片完成），3片继续；仍未正式6016导出、未训练。

后续：6027独立进程检查通过，prepare/run/report及其lines绑定均正确，COMPLETED/0:0；新增verify_isolated_entries.sbatch，没有改冻结旧文件。6028部分只读盘点35条件/102尝试：train18快照/7布局、13恢复，仍仅方块；dev7快照/3布局、5恢复。随后6014已见17/25审计，0/1片完成、2/3片运行；无Traceback，R0_964039六尝试刚完成待审计。6026已依赖6016提交第二批累计覆盖报告，勿重复。简明交接见CURRENT_STATUS.md。

已恢复6014第二批物理采集与6008训练门禁监控，均继续运行；只终止了上一轮本地exec701的日志轮询，没有终止远端仿真/训练。第二批至少6个条件完成独立审计，含两个新方块恢复条件，完整统计待6015/6016。6010..6017链不重复提交。

新增collection_coverage_v1只读分层报告：同一正式导出内，按train/dev分别统计全增强提案、资格通过、自然失败与恢复条件的任务/相机/颜色/物体位置。按种子去重环境、按快照去重分支；不改门槛/分布、不送模型。6023为缺实现的预期红测，6024六测试通过，6025首批真实报告通过并与5980汇总一致；4份文件本地分块同步且SHA256一致，见DELIVERY_6025.json。

首批进一步分解：train方块9快照/4种子、7恢复/4种子，胶囊0；dev胶囊4快照/2种子、3恢复，方块3快照/1种子、2恢复。全train提案相机方位-57.0..54.4度，资格通过仍保留该范围，但自然失败子集仅-19.8..54.4度，4个种子；不能把全提案覆盖当作已学习覆盖。dev自然失败3种子。继续原种子协议扩大，暂不引入材料扩展。真实参数更新仍0。

## 新续接更新（优先于下面记录）

**首批完整完成，第二批已启动。** 5974/5980/5982/5985/5995均已现场核对COMPLETED/0:0。首批26资格条件、75执行器尝试（baseline2+varied73）；真正启动运动64（2+62）。私有分类：34成功、19规划拒绝、21已登记自然失败、1`object_outside_container`因不在冻结白名单而单列，未计训练门槛。不是所有规划拒绝都0运动（可能前段已动、后段规划拒绝），不要把两个分母混同。

5980最终正式导出：train9去重自然快照/4组、7恢复/4组、3有效动作，任务仍RedBlock；dev7快照/3组、5恢复/3组、两任务，2有效动作。SFT train10=恢复7+STOP3，dev7=恢复5+STOP2；这些正样本数不能冒充120/40自然快照门槛。5995全17条图像/输入/动作/编码审计通过，最长提示5772tokens，无截断、0模型生成/0更新。6份核心结果已本地同步并全SHA256核对，recovery_dataset_v1/FIRST_BATCH_DELIVERY.json。

第二批自动链实际ID：6010 prepare已完成；6011资格array0-3%2（当前0/1运行，2/3等待）；6012资格merge→6013物理prepare→6014物理array0-3%2→6015合并审计→6016导出→6017next。全部已提交，**不得重复**。6008 v2监控仍RUNNING，已看到5980导出但quantitative_ready=false，只等待，未提交训练链。

**重要数据进展：** R1_964029_varied_noisy（独立dev）首次胶囊自然掉落，top直接成功；lower后出现outside_container再掉落；slow失败再top成功。完整独立审计passed，6尝试。原分布两任务已具备自然失败/恢复证据，训练partition仍待补胶囊，**暂不接入材料扩展**。5974最新23/26已审计（964030方块首次成功）。6009私有接触只读分析完成61尝试，不作模型输入/标签；记录部分胶囊成功运输夹爪法向合力中位103..110 N，不能将驱动限±5当触点5 N或仅靠局部摩擦饱和值推断承载能力。完整报告还在远端grip_contact_review_v1/results/job_6009.json。

**当前自动衔接为6008**，来自training_stage_bridge_v2/watch.sbatch、依赖已完成6007（五测试+源冻结），已输出collecting。6001旧监控已CANCELLED，不可恢复。v2 source_manifest与6007日志、6006入口修复证据、6004盘点已本地同步并校验，见training_stage_bridge_v2/DELIVERY_6007.json。最新5995仍等5980；5974已审计19/26、正在独立dev种子964025，首失败与顶面成功已出现但本条件尚未完整审计，不能提前计数。

修订验证已确认实际作业**6006**：7测试通过，子进程现场复现旧smoke/train确实来自candidate_sft_v2；逐个断言freeze_v2/smoke_v2/train_v2/vf_common_v2均来自新目录，train_v2.probe is smoke_v2.probe通过。**6004**只读盘点18已审计条件：train6自然快照/3组、5恢复/3组，新增SET_TIME_SCALE，已有3有效类型；dev0、任务仍仅RedBlock。R0_964013的减速分支直接成功；其他修正非统一有效，有实际动作选择价值。5974已审计19/26。training_stage_bridge_v2已上传，prepare刚以afterok:6006提交，实际ID待读terminal；prepare过后提交新的watch，旧6001已CANCELLED，不能重启。

**重要修订在途：** 自审发现vf_common.py永久把candidate_sft_v2插到sys.path首位，train.py的`from smoke import probe`可能拿旧文本probe；先前5997的联合`import freeze,smoke,train`也会导入旧smoke/train，因此“入口导入成功”不等于新入口正确。已仅取消本轮自建监控6001（不影响5974仿真），保留源与日志。新增vf_common_v2（加载runtime后恢复路径）、freeze_v2/smoke_v2/train_v2与独立sbatch，新训练显式import smoke_v2；verify_entries_v2会用子进程复现旧路径并逐个断言新路径。验证刚提交，须读terminal实际ID。原冻结已有文件未改。**后续只能用新v2训练入口，旧6001不能恢复，需training_stage_bridge_v2。** 尚无真实参数更新，错误在启动训练前发现。

最新6003真实多模态反向检查通过：loss0.4885008931、496 LoRA梯度张量全部有限、norm6.6163173664、峰值显存9331497472字节；未创建优化器，0参数更新/0生成，所有可训练参数逐张量比对不变。新增gradient_check.py/.sbatch，没有修改已冻结旧文件；结果已本地同步并核对SHA256。5974已审计18/26，下一只读progress刚提交（读terminal取实际ID）。后续任务仍是数据覆盖与数量，不是训练计算故障。

再追加：training_stage_bridge_v1准备最初带已完成作业afterok:5993:5997提交被Slurm拒绝（依赖已老化，不是代码失败）；已重新用sacct确认两者COMPLETED/0:0，直接提交**6000**，3测试/源冻结完成。**6001**为afterok:6000的长时只读监控，已RUNNING并输出collecting/export None；最多23h轮询，原数量门槛满足才提交编码审计、基础对照、冻结、受控训练依赖链。其source_manifest冻结了6个训练相关目录现有py/sh/sbatch，后续不能修改这些已有源文件；修订用新版本/新入口。未提交真实训练链，目前Qwen生成仍51、更新0。

material_randomization_v1是独立未接入能力：6002四项编译/接触混合测试通过（baseline不变、确定性/越界拒绝、质量惯量同比例、priority真实接触）。密度0.7..1.5倍、夹爪垫滑动摩擦0.65..1.15倍，只编译/微型接触mj_forward，0动力学/0训练样本。没有改当前采集分布或启动材料pilot；须等正式三批覆盖结论再决定接入。5974最后已审计15/26，R0_964013共6尝试、R1_964013/R0_964014各1，数字需刷新。

后续更新：comparison 5993九测试+全部入口通过。5994只读编译材料盘点完成：方块0.1611504kg/胶囊0.12664545kg，夹爪垫priority1（滑动摩擦0.7/0.6）高于物体priority0，故只改物体摩擦不足以保证改变夹持；无参数改动、无动力学。physical_diversity_probe_v1/PLAN.md仅记录候选未来材料范围，未实施，当前协议不变。

visual_dataset_audit_v1已实现正式导出全量图像/动作/编码检查，**5995依赖5980、RECOVERY_EXPORT_JOB=5980**，勿重复提交。visual_finetune_v1新增门禁、token加权优化器、freeze、最长训练样本单步smoke/独立重载、从基础权重一轮训练代码；**5997七测试与全部入口导入通过**，5996为先前仅测试通过。训练冻结需原数量门槛、同一导出审计、完整基础模型对照，另需≥3个独立dev布局有已测成功选项且基础模型非法/提前STOP/已测失败的缺陷；未知动作不算失败。**未提交freeze或train，没有Qwen参数更新。** REVIEW.md记录自审及未验证边界；该新目录尚无manifest，仍可修订。最后5974已审计12/26条件，新的964008与964012各6尝试，完整统计需再刷新。

已现场确认并把5982依赖更新为afterok:5980:5987；5987五测试和入口导入通过。5974首批仍运行，不重复提交。964006完整独立审计已通过：首次自然掉落，top直接成功、下移30mm直接成功、slow失败后top成功；5尝试。第二种有效动作SET_GRASP_OFFSET已有真实成功后继。5989只读进度：9已审计条件，train5去重自然快照/2组、4恢复/2组、2有效动作；dev0，任务仍只有RedBlock。这是部分统计，非最终数据。

visual_training_v1新开发多模态答案后缀损失：5988四测试通过（完整因果损失参照、真实梯度、两图与完整上下文传递、错误掩码/缺图拒绝）；5990真实基础模型前向检查COMPLETED/0:0，4634提示token/31答案token、两图grid[1,28,28]、loss=0.4885008931、参数不变，0生成/0更新，不是训练。四份证据已本地同步，DELIVERY_5990.json逐份SHA256核对。此目录已被5990记录源身份，后续不要改已有文件。

visual_comparison_v1已实现正式dev全部去重自然输入+导出STOP的基础模型对照；公开inputs和private_outcomes分离，多成功选项都认可、未测动作不算失败、离线结果不当物理恢复率。准备入口强制原quantitative gate，未运行生成。5991九测试通过但缺mm_generator路径；5992修正路径后九测试通过，入口暴露仿真bootstrap将graspnet loss.py遮蔽模型loss.py。已在新run.py显式优先candidate_sft_v2并校验runtime/loss路径，再次verify已提交（需读terminal确认ID）。新comparison尚未冻结，可修复；旧模型/采集文件未改。

当前持续推进目标未完成，不能把以上接口验证当训练就绪。下一步核对comparison入口检查、首批完整审计/5980导出及5985运动分母；盯5982首次自动分批。若三批后仍仅一个任务自然失败，必须分析覆盖缺口并继续开发，不能降门槛或默默停工。

## 当前续接更新（优先于其余旧记录）

最新调度：collection_scale_v1在首次调度尚未启动前补齐后续物理按种子四分片/最多两GPU；每条件三分支仍一个进程，完整审计后统一合并。5984四测试与sc_qualification/sc_physics/sc_next入口通过；已把5982改依赖afterok:5980:5984。首批5974顺序采集保持不变，未打断任何在途任务。5976当前完成57/66资格、21通过（实时数仅供交接，下次须刷新），尚无正式物理数据。5983实际ID已确认，是资格完成后的覆盖报告。

后续追加：5977已通过旧恢复轨迹接入新采集器/新独立审计器的完整回放检查，0新增物理/模型。5978多模态编码3测试及真实两图检查通过：4633提示token/27答案token、pixel_values[1568,1536]、两个[1,28,28]grid，答案后缀掩码正确，无截断，0训练更新。5979导出强化后7测试通过（增加STOP成功事实和直接成功后继检查）。5980已依赖5974:5979提交正式导出。collection_scale_v1四分片最多两GPU、按种子隔离资格、每批导出后门槛审查；5981四策略测试和入口导入通过。5982已依赖5980:5981提交next.sbatch，RECOVERY_EXPORT_JOB=5980；首批完整后最多按既有1024种子预约继续，三批后仍不足两种有效修正/持续无收益则留下具体缺口停止自动扩量，需代理继续开发，不代表总目标完成。5983（需核对terminal）已依赖5976提交diversity.sbatch，报告全提案与通过子集的相机/颜色/位置/资格覆盖，不当全分布物理成功。当前5976资格仍运行，5974尚等资格，不重复任务。

5964因独立审计读取分支观测路径错误退出，不是物理/模型执行失败；保留原日志。新增observation_reference_v5/audit_v5，5967四测试和失败现场完整审计通过。5968仅续跑未消费962906/962907，15回归测试通过，最终7条件13物理14视觉调用；原配置2/2，增强首次3/5、规则5/5、direct3/5、diagnostic3/5。原pending审计5966已改依赖5968并完成：16决策去重4自然快照，2真实恢复，均SET_GRASP_STRATEGY，模型累计51（原37+14）。这些仍是pilot，不能计正式数据。

新recovery_collection_v1实现预登记三分支（top_then_slow、lower_then_slow、slow_then_top），同一首次执行共享、每条件≤7物理、0模型；32种子/批（24train+8dev），保留原随机分布和噪声。5969为门禁红测缺rc_gate，5970发现新rc_common与旧container_recovery模块冲突；已在冻结前改为collection_common/collect_worker/collect_audit。5971八测试、七入口和旧模块解析检查通过。5972协议冻结1024预约种子964001..965024，**仅首批已安排，不代表全量提交**。正式训练门槛保持。

5973首批资格在baseline渲染之后因嵌套输出目录错误拼接旧参考路径失败，0物理/模型。新增qual_one_v2/qualification_resume_v2显式分离项目参考与批次输出，只复用哈希校验的已有渲染；5976正在执行66条件资格。**5974是既有pending物理作业，已将依赖改为afterok:5976，勿重复提交。** 后续如继续新批次不能用有路径问题的旧rc_qual_one；需新增入口继承正确v2算法。原冻结文件均未改。

recovery_dataset_v1实现已审计批次导出、失败正标签拒绝、同输入多成功动作保留选项、STOP比例≤恢复正样本1/2；5975五测试通过。导出任务尚未提交，待确认5974完整审计；数据准备仍未达标，无训练。

11份核心文本已本地分块同步并逐份SHA256核验，见recovery_collection_v1/PRIOR_EVIDENCE_DELIVERY.json；含新视觉manifest/complete、resume清单、visual inventory、采集protocol/verification和日志。原始图像/NPZ与完整逐条件证据仍远端。旧会话原文件已只读流式筛选（22729行），最后成功回复与最新多样性要求核对；不导入旧工具定义。

本轮使用executing-plans、writing-plans、systematic-debugging、verification-before-completion并按requesting-code-review原则自审；用户限定的旧子代理型号不可用，未派发。MEMORY.md:24-25仅作背景且已现场验证，最终需要引用。未commit/push、未写memory、未干预其他进程。

## 最新追加（优先于下方旧视觉状态）

**首条有效恢复已证实，视觉闭环已启动。** 5959资格8/26；5960和5961完成：11尝试、baseline2/2、增强5/6（首次4/6），T0_963107首次object_dropped→observed_top成功，完整独立审计通过。inventory自然快照1/恢复1/有效类型SET_GRASP_STRATEGY；T1_963101三次规划拒绝不计自然失败。完整manifest与7份结果/恢复证据本地同步，natural_top_pilot_v1的LOCAL_DELIVERY与FINAL_DELIVERY记录哈希。

**5964（不是5963）正在运行ai_safe_visual_loop_v1/run_v4.sbatch**。已通过prepare门禁，7条件，最多49新执行/56模型调用。Qwen3.5-4B基础模型adapter关闭，service/ready startup_generations=0。当前两baseline及增强A0_962902/A1_962903首次成功，A0_962905首次object_dropped，正在先跑fixed_rule修正，随后两AI共享首失败现场决策。实际模型新调用数须读service/requests，不凭服务启动计数。

visual_data_review_v1新开发只读盘点：逐条件审计身份、task+state+clean去重、规划拒绝单列，动作真实后继才计恢复，模型诊断不作正确标签。5965三项统计测试已通过；**5966 afterok:5964已提交review.sbatch**，勿重复提交。原v4仅pilot，正式训练条目仍0，未训练。QUALIFICATION_COVERAGE.json在observed_top_pose_v1：最近24种子48增强提议中11通过，仍覆盖约-58..51度方位/37..72度俯仰/0.95..1.48m距离；不可将条件通过样本成功率当全分布成功率。

最新在途：5959资格26条件8通过；5960准备10测试和两个入口通过，已执行baseline两条及增强T0_963101首次成功并审计，当前继续后续条件（需实时读status）。**5961已afterok:5960提交review.sbatch**，不重复提交。新三方法视觉v4已开发并上传，5962验证11测试/两入口/真实基准历史审计/旧失败输入隔离通过；新增SET_GRASP_STRATEGY(observed_top)消费一次执行并清零旧偏移，top状态禁直接偏移，保留时间/重试/观察/停止。分支与审计独立同时检查state+strategy，初始统一original。**未来须run_v4.sbatch**且必须natural_top inventory>=1真实自然恢复；run_v4尚未提交。新增v4不覆盖旧v1/v2/v3文件。模型总调用仍37，无训练。

继续更新：5951与5952均COMPLETED/0:0。span实际9次、baseline2/2、增强4/5全部首次成功；963008三次掉落、2去重自然失败快照、恢复0。5955私有诊断确认selected观测跨度43mm/完整几何88mm，不能把可见跨度当真宽；不作AI标签。9份结果/日志已同步，observed_top_pose_v1/LOCAL_DELIVERY.json哈希逐份核对。

observed_top_pose_v1新增仅观测顶面矩形候选：90分位下6mm、99.5上界、XY2/98分位、1度搜索、顶面下30mm；最多50mm名义到新点位移。5956红测ModuleNotFoundError保留；5957三测试+9历史输入检查完成；5958五测试+原配置与963008两个完整静态路径独立审计通过。963008新轴完整宽约68-71mm，但仍有16-18mm水平偏差，**0新物理、不能算恢复**。

新执行接口top_motion/top_session/top_audit明确记录strategy和original_nominal，不悄改旧名义点；继承原安全保护与独立点云重建。已新增命令/策略分发回归测试。开发审查发现并修正StrategySession继承/直接super调用问题，发生在新pilot manifest不存在、作业等待资格时；未消耗物理、旧冻结文件不动。

**5959 natural_top_preflight_v1运行中**，新预约963101..963112（26条件），原分布噪声与资格不变。**5960 natural_top_pilot_v1已afterok:5959提交**，准备阶段先执行本批+top全部测试、入口导入与依赖冻结，通过才物理；首次原span策略，失败统一USE_OBSERVED_TOP，再失败SLOW_3X，最多3次/条件。不要重复提交。5960审计依赖review尚未提交，先确认准备与实际job状态。视觉v3仍未启动，因为span恢复0；后续若top证明有效，需显式向三方法接入新策略与独立审计，不能直接拿原v3缺少动作接口跑。

本次续接现场核对：5938深入抓取已COMPLETED/0:0，共24尝试、baseline2/2、增强4/10；5941去重8自然失败快照、0恢复。5945..5949均完成，新增姿态宽度保护与投影审计已有结果。5950新预约963001..963012资格26条件仅7通过（2baseline+5增强），保留19拒绝；**5951宽度保护/0.20m抓取正在运行，5952依赖审计已排队，不重复提交**。当前已审计baseline两条件与963003/963006胶囊首次成功；963008方块首次掉落，尚未最终审计，不推测恢复。

5953对未物理消费的视觉预约962901..962908复查7/7通过，COMPLETED/0:0。新增ai_safe_visual_loop_v1 v3入口（worker/audit/prepare/controller/environment/run）接SpanSession与0.20m，并继承上述两份预约。5954代码验证COMPLETED/0:0：8测试、执行/审计入口、历史真实跨度轨迹独立重建、公开输入隔离均通过。v3恢复门禁改为已采用同一新执行器的natural_span_pilot_v1 inventory至少1自然恢复；未运行物理/模型。旧v1/v2冻结文件不变，后续使用run_v3.sbatch。

最新6份文本已同步本地：natural_span_preflight_v1/result.json、safe_visual_qualification_v2/result.json、natural_deeper_pilot_v1的complete/inventory、ai_safe_visual_loop_v1的code_checks_v3/verification与verify-v3-5954.log。完整新manifest和span批次最终结果仍待同步。现有总37模型调用未增加，无训练，正式数据门槛不变。此次恢复还读了MEMORY.md:22-25（最终须memory citation）。

最新批次状态：5937已COMPLETED/0:0，26条件完成，2baseline+10varied通过，8可见性拒绝/6有限路径拒绝。5938深入抓取12条件/≤36次仍运行；前两baseline首次成功，D0_962802增强三次失败，前两掉落，第三次(-.03,time3)真实带起方块但运输碰另一箱壁，不能计恢复，已耗尽不加第四次。5941依赖5938做自然去重审计，尚未完成。natural_deeper_lift_audit_v1对该第三次只读重建.20/.25抬升，刚提交probe.sbatch（job需读terminal确认，不凭推测），0新物理。

5939四次真实视觉HTTP调用完成，5940完整独立审计通过，均合法OBSERVE；两图编码[1568,1536]、两个[1,28,28]grid。基础模型仍混淆lift_height与grasp height；不当正确原因。累计真实模型37=31文本+6视觉。12份协议/结果/验证文本同步，ai_visual_service_v1/LOCAL_DELIVERY.json登记，图像等仍远端。

ai_safe_visual_loop_v1已实现安全执行器+视觉服务+独立逐决策/物理审计，未提交物理run。5942四动作边界测试/真实历史输入边界/两个入口通过。审查发现固定ID颜色误导，新增sv_requests_v2和worker_v2/audit_v2/prepare_v2/controller_v2；以冻结任务配置生成与引擎一致的实际任务颜色名称，不传根因/位置真值。5944六测试与v2入口通过，结果在code_checks_v2。后续必须run_v2.sbatch。门禁要求natural_deeper inventory>=1自然恢复及visual service audit通过；不能绕过。旧接口10mm不改，新接口单步30mm/累计50mm，三方法相同权限。

safe_visual_preflight_v1新预约962901..962908（18条件）已5943 COMPLETED/0:0，7条件通过。原配置两资格在逐字段去seed比较一致后复用5937计划和可见性，未重复耗时静态搜索；增强逐条件真实检查。仍是pilot，未执行。新manifest/result、5944验证及5938最终结果仍待同步。

5933与5936已核对Slurm COMPLETED/0:0。qualified共25尝试、baseline2/2、增强2/9，全部逐条件审计通过；5936三测试通过，14决策→4去重自然失败快照（962703、962708），恢复0。已同步complete、inventory与两作业日志4份，qualified_data_review_v1/LOCAL_DELIVERY.json记录哈希；原始数组仍远端。两掉落闭爪均真实双侧接触，但夹爪垫靠近物体上缘；-10mm和3倍时间失败，原因仅假设，不作监督。

natural_observable_preflight_v1：新预约962801..962812，26条件（24增强+2原配置），64pixels/0.70可见性再有限几何资格，原随机分布/噪声不改，全部拒绝保留。5937运行中，2边界测试已通过。natural_deeper_pilot_v1已上传并以afterok:5937提交5938；资格完成后自动准备测试/独立审计入口，然后仅执行通过条件，首次安全world_down/.15/1.5，失败统一世界z=-.03，再失败time3，最多3次。0模型/训练。这是新增工程权限，不能冒充旧AI每步10mm权限。必须核对实际结果再接线新AI动作。

ai_visual_service_v1已上传并提交run.sbatch（job ID需读aiTerminal.output），从qualified已审计两条掉落首决策各运行direct/diagnostic，共4次新模型上限、0新物理。真实HTTP+两图哈希+tensor编码+EOS+基础adapter关闭审计；input保留旧10mm权限，不预填根因。尚未确认准备测试或生成成功。服务不自动重试请求；若失败先查generation_started及response消费账。

更新至5936：qualified准备5932通过2测试与独立入口导入，11条件、最多33尝试，manifest已冻结。**5933正在运行**，C0_962701_baseline首次成功及逐条件审计已通过，当前状态需读远端status（禁止缓存）。**5936已以--dependency=afterok:5933排队**，自动运行qualified_data_review_v1/review.sbatch；若5933失败则该审计不会启动，勿重复提交。review代码已上传尚未运行验证：过滤planning_rejection，使用task+state_sha256+clean_sha256去重，不把新增噪声/补看重复计数；将已执行LOWER_10MM/SLOW_3X映射为标准SET_GRASP_OFFSET/SET_TIME_SCALE并核对真实后继状态。只生成pilot候选input与实际后果，不宣称正式训练就绪。

ai_multimodal_requests_v1已构建真实before+latest_after RGB、公开执行事实、编码器偏差的共同请求。5934通过来源/隐藏字段/两模式公平/两图哈希/预算5检查，0模型0物理。复核后将“所有历史尝试已做硬件检查”措辞改为“不绕过当前执行器安全检查”，保留初版，新增visual_requests_v2.py及revision_v2；5935检查通过。**后续接线用visual_requests_v2.build**。目前仍未有新增视觉闭环模型调用，真实模型累计仍33。

最新30份文本已同步，natural_feasibility_v1/LOCAL_DELIVERY.json列哈希，含self_route最终完整审计/8条件result、joint_guard两版、feasibility完整结果与失败/续跑日志、qualified冻结manifest/prepare、multimodal两版校验。原始NPZ/图像/完整规划仍远端。此前26+9份同步也保留。

更新至5931：ai_self_route_v1/5926已完整完成，15次执行、两阶段审计通过，baseline4/4（首次2/4），增强2/4（首次1/4），3次SELF_SAFE_ROUTE工程恢复。原始错误证据核对这3条前序均route_planning_rejected=true，**正式自然失败恢复仍不能增加**。全部动态采样无自接触（有离散采样局限）。5927跟踪事实摘要4测试+历史0.424m误差对照通过，尚未接入模型闭环。

natural_joint_guard_v1：发现新静态端点肘关节4.068rad超控制范围±3.1415，新增等价角归一到真实关节/ctrl交集并检查连续路径跳变。5928初版3测试，但端点也错误检查跳变过严；未用于物理。新增bounded_ik_v2.py及probe_v2.py，不改冻结文件；5929五测试通过，revision_v2保留结果，旧962601两增强现场仍无完整路径。新版本上下文顺序必须self_geometry.context()后bounded_ik_v2.context(config)，否则self context的引用断言失败。

natural_feasibility_v1预约962701..962708，原随机布局范围/颜色/相机/噪声不改，只做参考几何任务资格。5930冻结18条件（16增强＋原配置两任务），完成8个静态结果后OOM；5931复用8份结果、逐条件独立进程完成余下10项。完整result：baseline2/2、增强9/16通过；7个增强拒绝保留，不称全局不可达。参考真值顶面位姿仅用于资格，不能送AI/复制执行器。

natural_qualified_pilot_v1已本地编写并上传，prepare.sbatch刚提交（实际作业ID需读aiTerminal.output）。引用预约全部11通过条件，最大33执行、0模型、0训练；从第一次就replan/world_down/lift=.15/time1.5，并加self+bounded限位；失败统一LOWER_10MM，再SLOW_3X，不读根因。实际抓取仍含噪观测。每条件worker后独立审计。准备检查仅允许natural_feasibility的预约种子复用，不允许任何其他清单重叠。**尚未提交run.sbatch**，先核对准备日志及测试。

待办：运行新qualified物理小批、按自然失败/规划拒绝拆分审计，验证偏移/减速恢复后再接入真实视觉AI闭环并扩正式集。现有正式门槛不变。ai_self_route最终结果、joint_guard两版、feasibility完整结果尚需同步本地；前次26份+后次9份证据已同步，分别见tracking_audit_v2及ai_tracking_facts_v1的LOCAL_DELIVERY.json。报告均本地已写。当前新模型总调用仍33（31文本+2视觉），无训练。

5920两次多模态生成成功；5924独立视觉审计通过。direct STOP、diagnostic OBSERVE，均EOS合法，实际两图进入编码；诊断内容不作正确标签。5921跟踪审计确认V0_962501增强首次TCP偏差424.26 mm，原配置15.02 mm，增强第三次49.35 mm；重算与遥测完全一致，控制/关节目标未越限。5922只读几何发现原过滤器忽略机器人自碰撞，增强首次末段理想穿入最大86 mm。无新增旧轨迹物理尝试。

natural_self_guard_v1新增作用域自碰撞静态筛选，5923四测试通过。旧962501增强方块无合格端点、胶囊918合格端点且完整路径可行，均非物理恢复。ai_self_route_v1使用新种子962601/962602，8条件、≤24执行、0模型；全部尝试启用自碰撞筛选，原参数失败后统一SELF_SAFE_ROUTE（world_down、replan、lift=.15、time=1.5），再失败LOWER_GRASP（世界z=-.015）。动态接触/力/控制量仅私有工程审计。5925两测试及独立审计导入通过并冻结。run.sbatch刚提交，实际job需读aiTerminal.output确认，不猜ID。完整代码/协议均已上传；下一步跟踪首种子审计，失败不重复已消耗尝试。

本地已同步26份新增文本，natural_tracking_audit_v2/LOCAL_DELIVERY.json列哈希，包含route_bridge_v2最终complete/两份审计/8条件result、视觉temporal_v3所有结果及两轮tracking。5923/5924及新小批结果仍待同步。各新目录REPORT已本地编写；不改冻结源文件。浏览器aiRequest的路径必须是`contents/grasp_server/...`（函数已自动加/user/yeliheng/api/），不要再次加api或前导斜杠；失败HTTP页面可能包含会话信息，只返回status，不返回HTML。

用户授权持续开发至有数据支持微调，不重复确认。总目标仍active，不能标complete。总计划与最低门槛见AUTONOMOUS_TRAINING_PLAN.md，不能为开训降低120训练/40开发快照、40实际恢复、种子隔离等要求。

已完成：ai_natural_loop_v1全8条件独立审计通过，26物理、31模型、原配置4/4、增强三方法各0/4；natural_data_review_v1去重39条决策为11个自然失败快照，恢复0。这些是pilot，不是正式训练数据。REPORT/STATUS及58份文本证据已本地同步，32份逐条件文件与远端审计哈希一致；原数组仍服务器。

动作能力只读检查：natural_capability_probe_v1两现场原高度范围路径搜索各耗尽512运输检查，均lift IK失败；270/315个端点可行不等于全程可行。两次重建错误经新增版本修订，5901/5903失败日志保留，5904五测试通过，复用第一项静态结果完成第二项，无物理重复。natural_lift_probe_v1作业5905已完成：两现场0.15至0.25米静态完整运输均通过，旧0.35米均IK失败。不是物理恢复。

ai_route_bridge_v1已完成：新种子962401/962402，每场景两任务，实际16物理/0模型/0训练，baseline4/4、增强0/4。初始原参数；失败后统一SAFE_ROUTE（replan=True，lift=.15；含噪深度局部恢复+合法目标完整路径），再失败SLOW_ROUTE（time_scale=1.5）。不按根因/案例挑动作。

5906通过5项测试并冻结。5907首种子4条件完成8物理，baseline2/2、增强0/2。方块no_grasp_candidate，胶囊虽静态合格但实际夹爪碰SortingTray。审计导入缺bootstrap，新增rb_audit_v2.py，不改原冻结逻辑；5909首阶段完整审计通过。5910仅继续第二种子并完成审计，完整结果见complete.json。29份后续文本证据已同步，8份逐条件结果哈希核对。旧failure.json是5907历史错误，勿重复首种子。旧962301/962302等不能加第四次；历史961103/961104更不能追加。

ai_route_bridge_v2也已完成：5911四测试、独立审计入口检查及69份历史种子隔离通过；5912新种子962501/962502共8条件16次尝试，baseline4/4、增强0/4，两个阶段审计通过。加入原候选耗尽世界竖直候选补救，第三次显式WORLD_DOWN_ROUTE，同lift=.15/time_scale=1。模式以独立control字段保存，原参数不伪改，排序保留全部姿态且执行/审计顺序一致。空抓/掉落仍未恢复。v2最终审计/结果尚需同步本地（manifest和prepare日志已同步）。

当前工作ai_visual_input_v1：把真实before+after RGB和执行事实送入Qwen3.5-4B。ai_observable_facts_v1的四项测试5913通过，公开task_completed和geometry_admitted/motion_started/时长，不含原因/未来字段。5914先准备单幅after输入，源mask不足未裁剪；模型调用0。5915改为同已审计V0_962501_varied_noisy首次尝试的before.png和默认暂停RGB，冻结temporal_v2，共2次生成预算，不执行提议/新物理/训练。只读核对reflection/engine.py before.png直接保存原RGB无标注。5916启动在AutoProcessor要求Torchvision处失败，生成0次，failure保留。

5917已把torchvision0.21.0+cu124从官方PyTorch仓库--no-deps安装到ai_visual_input_v1/torchvision_overlay，未改共享env；后续导入测试未source qwen环境导致libcudnn.so.9缺失。新增validate_dependencies.sbatch在正确candidate_sft_v2/environment.sh下导入校验，最近已提交（需从aiTerminal.output取实际作业ID，预计5918）。不要重复安装或删除overlay。待导入检查通过，提交overlay_prepare.sbatch（mm_prepare_overlay.py创建temporal_v3，继承旧身份并冻结overlay源码/so，确认旧生成0），然后overlay_model.sbatch。这两个尚未提交。实际执行mm_overlay_run.py，临时patch mm_common.ROOT和mm_run.ROOT到temporal_v3，复用冻结mm_run/mm_generator。新进程PYTHONPATH将overlay放首位。模型基础加载沿用f_generator.Generator，adapter关闭，温度0 seed42 max2048；AutoProcessor最大448²像素，保存image_grid_thw/pixel_values_shape和token数。失败后不得无痕重跑；先查generation_started及response判断已消费次数。

后续仍需有效抓取修正能力与真实恢复数据：当前累计自然三方法26物理+两版工程各16物理，恢复仍0。世界竖直已接线，但不够。可考虑在新的受控协议中开放并验证抓取偏移、低抬升、显式姿态/安全路径，以及真实图像/动作事实输入；不能按私有错误为每例预填正确动作。源物体的可见表面中位数不是体中心，不能用真值残差直接当模型输入或监督。只读反事实不能当物理成功。最终至少120训练/40开发快照、40真实恢复、≥2种有效修正等门槛尚远，不能宣称训练就绪。

远端：/home/yeliheng/grasp_server。浏览器pageId=2，Jupyter URL https://gpu.dtsci.cn/user/yeliheng/lab。window.aiRequest已用当前页面live token初始化，不输出token。aiTerminal.name=9，ws仍连接；发送stdin命令并读取output。所有仿真/模型/几何操作走Slurm；不打断他人进程。

读取可变文件须带&_t=Date.now()及cache:'no-store'，否则浏览器可能返回旧status。工具mcp__chrome_devtools__evaluate_script/pageId2、mcp__node_repl__js可调用。通过functions.exec元数据找schema。上传新路径先404检查；冻结文件禁止覆盖。同步大JSON先浏览器缓存字符串，再18000字符分块经node fs写本地，避免64000字节自动审查上限和把大数组输出给模型。

本地Python命令是WindowsApps占位，不作有效验证；服务端env_sim/bin/python为仿真/审计，qwen35/env/bin/python为模型。source脚本前export PYTHONPATH=${PYTHONPATH:-}。模型runtime必须解析到candidate_sft_v2/runtime.py。

本轮未写memory、未git commit/push。已使用MEMORY.md:22-25，正常最终回复须末尾memory citation。沿用此前已读writing-plans、executing-plans、systematic-debugging、verification-before-completion流程。不可派发不可用旧型号子代理。
