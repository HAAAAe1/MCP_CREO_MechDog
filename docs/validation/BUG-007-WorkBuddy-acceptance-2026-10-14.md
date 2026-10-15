# BUG-007 WorkBuddy 最终 MCP 黑盒验收报告

- 日期：2026-10-14（UTC+8，约 18:50–19:20）
- 受测接口：WorkBuddy 通过已连接 MCP `MCP_CREO_MechDog_dev` 直接调用公开工具，未查看/分析/修改源码，未执行本地测试脚本
- 测试件：全部为本次新建独立测试件（`bug007_*`），不复用用户模型
- 协议遵守：每次修改只提交一次；只轮询同一 job_id 至终态；全程无 unknown_outcome、无提交/轮询响应丢失、无重交；未清 pending_job、未取消任务、未注入锁、未终止进程、未改变 Creo 安全设置
- 单位：毫米；角度：度

## 0. 环境侦察（MCP 公开接口）

| 项目 | 公开返回值 |
| --- | --- |
| 服务公开版本 | 0.3.0（pre-release candidate；update: up_to_date） |
| runtime.code_root | `E:\Projects\MCP_CREO_MechDog` |
| source_changed_since_startup | false |
| 单位 | mm / degrees |
| direct_blend_callback.artifact_status | prepared（registry_file/module_file/dll_sha256 已列出；文档明确 "artifacts alone do not confirm readiness"）→ **准备文件存在 ≠ 回调已加载；实际加载状态由本次约 10 次原生 Blend 成功间接证明工作中** |
| 连接状态 | creo_session_status connected=true，state=ready（"Toolkit connection verified; modeling is available"），release_numeric=44，worker_exit_code=0 |
| seed_library | 9 个种子可用（two_straight fid=60 / two_smooth fid=60 / three_straight fid=71 / three_smooth fid=71 / five_smooth fid=93 / four_straight fid=82 / four_smooth fid=82 等），SHA256 均匹配清单 |
| 结束时会话 | connected=true，current_model=▩BUG007_STEP8_AFTER0001（最后小件在会话中可见），worker_exit_code=0 |

说明：MCP 公开接口未提供 Creo 版本字符串（仅 release_numeric=44）；构建身份细节记“无法确认”。本环境结论不外推到 Creo 10（Creo 10 由协助者独立验证）。

## 1. 2000mm³ 矩形底座 — 通过

- 输入：creo_execute_plan（新建，model_name=bug007_step1_base）：XY 矩形草图 min=[-10,-10]/max=[10,10]、offset=-5；extrude depth=5（回显 direction=positive）；断言 require_solid + volume_mm3=2000
- job_id=427e7711169e4ba0a842d9223060b714；model_id=377eb5666ed54ec59fe8abfecbabde29
- 终态：succeeded / verified；耗时 7.65s（start→finish）
- 结果：volume_mm3=1999.9999999999998（≈2000，断言通过）；bodies=1；has_solid=true；revision 0→1；saved_file_reloaded_and_verified=true；rollback_succeeded=false（无需回滚）

## 2. 两截面 straight 放样 blend_probe — 通过

- 检查点：job fb9439cf5dc44d679ec7c79a0ae793bd（model 1dbe4c34f50d4f7eaf47ee1a2d7d325a）：XY 圆 sk_a R10@Z0、sk_b R6@Z25；7.38s；revision 0→1；重载 true
- inspect：sk_a feature_id=40、sk_b feature_id=49；revision=1
- creo_loft：model_id、expected_revision=1（实际值）、label=blend_probe、sections=["sk_a","sk_b"]、mode=add、interpolation=straight、new_body=false
- job_id=6a4017e34bae41f89becaf1d0616e724；终态 succeeded/verified；耗时 8.02s；revision 1→2（推进一次）
- 几何：volume_mm3=5131.268000863329（期望 4900π/3，误差 0）；bbox=[[-10,-10,0],[10,10,25]]；bodies=1
- 原生参数（Creo native PRO_FEAT_INFO，保存前与重载后均核对）：BLEND_PROBE feature_id=56、type=917 protrusion、native_subtype「混合」、section_count=2、直（straight）
- 原草图保留：SK_A(40)/SK_B(49) 在位；saved_file_reloaded_and_verified=true

## 3. 三独立模型串行重复 — 第1/3轮通过；第2轮（整数ID）公开接口失败

串行执行，未并发。每轮实际耗时（start→finish）：

| 轮次 | 模型 | sections 形式 | 作业终态 | 耗时 | 结果 |
| --- | --- | --- | --- | --- | --- |
| 1 | 33e8dd04e3bd48d499c5a20ed8ac46e9 | 标签 | succeeded/verified（job bc027cbd52d649ccaab6acca10e4b613） | 7.87s | volume=5131.268000863329、revision 1→2、重载 true |
| 2 | 04ce20e4b6d3424bb5e9a8351de47444 | 整数 feature_id [40,49] | failed（job d1751a52673f4969933cb95ebb663dfa） | 5.61s | "Unknown feature label: 40"；rollback_succeeded=true |
| 3 | 6a90c906156643768dff70a012430a73 | 标签 | succeeded/verified（job c20683a5ef7c4a63924d03c081498a83） | 9.06s | volume=5131.268000863329、revision 1→2、重载 true |

第2轮说明（据实记录，不重交同一修改）：
- 提交前 inspect 确认该新模型 sk_a=40/sk_b=49，与检查点公开返回的整数 ID 一致；按整数 [40,49] 提交。
- 作业回显 sections 为字符串 "40"/"49"，原生按标签查找拒绝："Unknown feature label: 40"。
- 模型保护：inspect 确认 revision 仍为 1、sk_a(40)/sk_b(49) 在位、无残留 Blend、updated_at 未变。
- 归属限制：同一版本（0.3.0，源码指纹与启动时一致）的开发者 stdio 脚本证据显示整数 `sections=[40,49]` 可被服务端保留并成功；本环境作业回显为字符串，差异发生在公开接口路径的某一层，**无法从公开接口进一步归因**（不读源码/本地脚本）。标签引用在全部正例中稳定工作。

## 4. execute_plan op=loft 入口 — 通过（与 creo_loft 一致）

- 输入：单计划内 sk_a/sk_b 两圆 + op=loft（label=blend_plan、sections=["sk_a","sk_b"]、mode=add、interpolation=straight、new_body=false）；断言 require_solid + volume_mm3=5131.268000863329
- job_id=994c29c3a84144e2b1ec7931b87f8658；model_id=9e38387a95c14762805fdc8bf7729dfb
- 终态 succeeded/verified；耗时 9.87s；revision 0→1
- 结果：volume=5131.268000863329（断言通过）；bbox=[[-10,-10,0],[10,10,25]]；bodies=1
- 原生参数（保存前+重载后）：BLEND_PLAN feature_id=56、type=917、「混合」、section_count=2、直
- 与 creo_loft 入口对比：特征 ID（40/49/56）、几何、原生模式/截面数、bbox、体积、重载全部一致 → **两个入口一致**；saved_file_reloaded_and_verified=true

## 5. 三截面 straight / smooth / 种子对照 — 全部通过

| 用例 | 模型/作业 | 终态/耗时 | 原生参数 | volume_mm3 | 重载 |
| --- | --- | --- | --- | --- | --- |
| 5a 三截面 straight（R10@Z0、R8@Z12.5、R6@Z25） | 0017fd8e / job 716b3328c58940f2b194bf7245869f84 | succeeded/verified，8.43s，rev 1→2 | BLEND_THREE fid=65，「混合」，section_count=3，直 | 5131.268000863329（与两截面 straight 解析值一致：中间截面在锥面上） | true |
| 5b-1 两截面 smooth | 3420baad / job b4da94c410784457b0a3e17bafea9821 | succeeded/verified，7.79s，rev 1→2 | BLEND_SMOOTH2 fid=56，「混合」，section_count=2，原生行「平滑」 | 5131.268000863329（两截面 smooth 与 straight 同值，未套用解析公式断言，实测记录） | true |
| 5b-2 三截面 smooth | cd967657 / job d7362aed93c140749015c24a6f7de325 | succeeded/verified，8.34s，rev 1→2 | BLEND_SMOOTH3 fid=65，「混合」，section_count=3，原生行「平滑」 | 5130.649365654384（区别于 straight；bbox 平滑外扩 [[-10.065,-10.12,-0.12],[10.065,10.12,25.12]]） | true |
| 5c-1 种子对照 2/straight（two_straight，mechdog_loft_reference.prt.5，fid=60，显式传入 capabilities 公开种子信息） | d6f32526 / job 317e63164eda439baa7ee4a42492b944 | succeeded/verified，7.83s，rev 0→1 | construction=native_multisection_blend_seed_rebinding，seed feature_id=60 | 5131.268000863329（与直接 straight 差 0，容差 0.01 内） | true |
| 5c-2 种子对照 2/smooth（two_smooth，fid=60） | d5c0ba82 / job 8c990c4d7c0c4fbb97bb0df16c418898 | succeeded/verified，8.15s，rev 0→1 | seed rebinding，feature_id=60 | 5131.268000863329（与直接 2/smooth 差 0） | true |
| 5c-3 种子对照 3/smooth（three_smooth，db_ca74c20181.prt.2，fid=71） | a53a862a / job 8791ed75a95a4212b396b8b32fc1c377 | succeeded/verified，9.70s，rev 0→1 | seed rebinding，feature_id=71 | 5130.649365654384（与直接 3/smooth 差 0） | true |

smooth 体积均以独立种子对照校验（差 0），未把 smooth 体积套用 straight 解析公式。

## 6. 已有 2000mm³ 底座追加放样 — 通过

- 模型 377eb5666ed54ec59fe8abfecbabde29（步骤1底座，revision=1）
- 先追加两圆草图：job 6b07f5b33195429ba4f56aad4d66460d，6.95s，revision 1→2，底座体积不变（1999.9999999999998），重载 true
- creo_loft：expected_revision=2、label=blend_on_base、sections=["sk_a","sk_b"]、straight；job 4d6f0b7874dd4dce8ace965f1a5fdf60；8.84s；revision 2→3
- 结果：单实体（body id=54, state=4）；volume=7131.268000907383（期望 7131.268000863329，差 4.4e-8）；bbox=[[-10,-10,-5],[10,10,25]]
- 原生参数（保存前+重载后）：BLEND_ON_BASE fid=96、「混合」、section_count=2、直
- 原特征/引用保留：SK_RECT(42)、BASE_EXTRUDE(51)、SK_A(80)、SK_B(89) 全部在位；saved_file_reloaded_and_verified=true

## 7. 负例拒绝 — 通过（拒绝原因各自不同，未归并为单一推测）

独立检查点：model c4214d3d003a4584b60319fa4f1be32f（job 9d4e560baf974a29acf2cdbe97a16443，7.79s，rev 0→1，重载 true）：sk_a(XY,R10@Z0,fid=40)、sk_b(XY,R6@Z25,fid=49)、sk_xz(XZ,R5@Z0,fid=56，法向 [0,-1,0])。

| 负例 | 输入 | 实际拒绝与错误 | 作业/耗时 |
| --- | --- | --- | --- |
| 重复截面 | sections=["sk_a","sk_a"] | MCP 入参校验拒绝："Loft sections must be distinct" | 未创建作业 |
| 不存在标签 | sections=["sk_a","nope"] | 作业失败："Unknown feature label: nope"，rollback_succeeded=true | job e474ae70d21148a3b6e13942ccb21b22，5.72s |
| 非XY截面 | sections=["sk_a","sk_xz"] | 作业失败："Blend sections require XY frames with strictly increasing Z"，rollback_succeeded=true | job 6d1ebeff818148069f70d019baf53178，5.51s |
| mode=cut | mode="cut" | MCP 边界拒绝："Direct Blend supports solid add into the default body only; cut, surface and new_body are not accepted" | 未创建作业 |
| mode=surface | mode="surface" | 同上边界拒绝 | 未创建作业 |
| new_body=true | new_body=true | 同上边界拒绝 | 未创建作业 |
| 过期 expected_revision | expected_revision=0（实际 1） | 边界拒绝："Stale revision: current model revision is 1"，未提交新任务 | 未创建作业 |

拒绝后模型核对（inspect）：revision=1 未推进；SK_A(40)/SK_B(49)/SK_XZ(56) 与原几何全部在位；无残留 Blend 特征；updated_at 停留在检查点时刻；pending_job=null。

## 8. R1@Z40 断言失败与回滚 — 通过

- 模型：1dbe4c34f50d4f7eaf47ee1a2d7d325a（步骤2已成功放样模型，revision=2）
- 输入：execute_plan(expected_revision=2)：XY 圆 sk_r1 R1@Z40；断言 volume_mm3=1
- job_id=972fa72c274746418b096e6097857bff；终态 failed（"Volume assertion failed"）；耗时 6.82s；rollback_succeeded=true
- 保存快照核对（inspect）：revision=2 保留；特征数=10（无 sk_r1 残留）；BLEND_PROBE(fid=56, type=917, 2截面, straight) 完整；volume=5131.268000863329；bbox=[[-10,-10,0],[10,10,25]]；updated_at 停留在成功放样时刻（10:52:24）
- creo_refresh_model 实时核对：job 09ee81cc88a742d18dc5ef6d465e1ba3，5.61s，succeeded；活动模型 10 特征、4 面、6 边、1 实体、volume=5131.268000863329、sha256=b40b4112…（与成功放样后保存文件一致）→ 回滚在实时会话中完整恢复
- 后续通道：新建 2000mm³ 小件 bug007_step8_after（job 788f5e8e19194ab8b28076d7f4207bf5，7.45s，rev 0→1，volume=1999.9999999999998，saved_file_reloaded_and_verified=true）→ 失败后通道可用，无需重启

## 9. 回调未就绪环境 — 未验证（条件未满足）

- 发起者未准备“未初始化/已卸载”环境；当前会话回调已加载并持续工作（本次约 10 次原生 Blend 创建均经原生 worker 的 DLL 句柄/协议核对后成功）。
- WorkBuddy 未主动卸载回调、未注入锁、未终止进程、未改变 Creo 安全设置；BLEND_CALLBACK_SETUP_REQUIRED 路径本次未触发。
- 同记未验证：未准备的首次加载确认、外部模态窗口、NEVER/ALWAYS 实际策略场景、并发（本次全部串行）。

## 结论汇总

| 范围 | 结论 |
| --- | --- |
| BUG-007 核心（已有件追加放样挂死/占用通道） | **通过**：全部直接放样（两/三截面、straight/smooth、新件与已有底座追加、两个入口）在 7.8–9.9s 内明确成功，无 running 卡死、无 unknown_outcome；失败用例均在 5.5–6.9s 内明确失败并回滚 |
| 几何/原生参数/重载/revision | **通过**：体积、bbox、原生 Blend 类型/截面数/模式（保存前+重载后双核）、单实体、revision 推进一次、原特征 ID 保留、saved_file_reloaded_and_verified 全部符合预期 |
| 负例与模型保护 | **通过**：七类拒绝错误各自具体；模型/revision/几何在拒绝与断言失败后完整保留（快照+实时双核） |
| 失败后可用性 | **通过**：断言失败回滚后 refresh 一致，后续小件成功并重载 |
| 整数 feature_id 引用（creo_loft.sections） | **失败（公开接口路径）**：按整数 [40,49] 提交被拒 "Unknown feature label: 40"，作业回显为字符串；同版本开发者 stdio 证据显示整数可被服务端正确处理，差异层无法从公开接口归因；标签引用稳定工作。建议登记为接口契约问题（schema 声明 anyOf integer） |
| 回调未就绪/首次加载/外部模态/策略场景/并发/Creo 10 | **未验证** |

附：全程工具调用均保存于 MCP 作业记录（jobs/ 目录，job_id 见上）；预览图 preview.jpg 随各成功作业生成；结束时会话 current_model=▩BUG007_STEP8_AFTER0001。本报告仅基于公开 MCP 接口可见信息；内部 DLL 调用、临时文件/hash、重试预算等非公开机制未纳入结论。
