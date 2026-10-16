# 2026-10-16 三份 0.3.2 反馈归档与问题映射

整理日期：2026-10-16（Asia/Shanghai）；整理条目：[DEV-026](../work-items/DEV-026.md)。当前状态与排期统一见[开发台账](../BACKLOG.md)。

## 来源与归档

读取来源目录 `C:\Users\Administrator\Downloads\0.3.2` 的全部 3 份 Markdown，以下归档与原件逐字节相同（SHA256 与大小一致）。目录中无其他文件；未取得报告引用的 `out/`、`out2/` 交付物、TXT 建模说明、job 附件、日志或模型文件。

| 来源代号 | 原报告归档 | SHA256 | 大小 |
| --- | --- | --- | --- |
| A | [0.3.2 钣金增料与四壁折边仍未修复验收报告](feedback-0.3.2/2026-10-16_CREO_0.3.2_钣金增料与四壁折边仍未修复验收报告.md) | `b390180ce399ceca4176b70d61edcc4aa842cee2d897d4bba124f059661584ab` | 8 571 B |
| B | [0.3.2 种子版本不兼容未修复与筋特征"Creo10"仍失败](feedback-0.3.2/2026-10-16_CREO_0.3.2_种子版本不兼容未修复与筋特征Creo10仍失败.md) | `9a5ab524951616b3cc81831830d4ccfca3f5c87b0d4666fac8c77957a7e4c754` | 12 673 B |
| C | [0.3.2 回调 DLL 非确定性构建致注册反复失效](feedback-0.3.2/2026-10-16CREO0.3.2回调DLL非确定性构建致注册反复失效.md) | `6e21d3b60ccc4aa3cc53fc7b2f960ff58bd676923f278faee55dd98993d8073b` | 8 870 B |

三份报告均针对**公开版 v0.3.2**：A 由 `creo_capabilities.update` 读出 current 0.3.2 = latest 0.3.2；B 自述"MCP 版本 0.3.2（GitHub 最新，Pre-release）"；C 记录从 0.3.1（main@`515d50b8`）升级到 v0.3.2 正式 Release，源码包 SHA256 `b9cc576d0a78af0cc277bb5e32131daa3215ebdef48c7144bf0201e9fbbb261f`、种子包 `e7b07e9a18f6101ec3fed145359831a7ffcf801be2e53a65f335d4c3cc9c2a16`、覆盖 344 个文件。

## 环境与证据边界

| 来源 | 报告中的测试环境与身份 | 本次不能确认的范围 |
| --- | --- | --- |
| A | 2026-10-16；v0.3.2；4 个测试模型（`acc_test_sm`/`acc_test_sm2`/`ai_part_8f612a5204a6`/`acc_rot_asm`）；未给出 OS、Python、SDK、源码提交与构建指纹 | 具体 Creo/OS 或构建身份无法确认；逐调用请求与日志未随本次文件提供；报告自述"已修复"没有可核对的本地改动 |
| B | 2026-10-16 13:35–14:50 GMT+8；Windows 10 / **Creo Parametric 9.0.0.0（release_numeric=41）**；MCP 0.3.2；stdio；约 40 作业 / 8 模型；留痕在 `F:\WorkBuddy CREO Space\...`（本机路径，未归档） | 文件名与标题写"Creo10"而正文环境为 Creo 9.0.0.0，**两者不一致且未提供更多身份信息**；作业日志、模型与附件未随本次文件提供；"Creo 9 未修复"只对该报告环境成立，不倒推其他版本 |
| C | 2026-10-16；Windows 10 x64 / **Creo Parametric 10.0.0.0**；VS 2022 BuildTools 17.14.40 + Windows SDK 10.0.26100.0；Python 3.13 x64；v0.3.1 → v0.3.2 覆盖升级 | 两次编译日志、三个 sha 目录清单与 `blend_sync_build.json` 变更序列报告方称可提供但未附；DLL 非确定性构建未在本仓库独立复现；观察项 0.3.1→0.3.2 断档结论沿用报告表述 |

工作区身份边界：本工作区分支 `codex/dev-026-0.3.2-feedback`（整理前基线 `ac18d66`/`daba288`），`version.py = 0.3.1`，台账与工作卡仍记 0.3.1 内容；0.3.2 的版本、发布说明与 DEV-025 只存在于 `main`（本工作区没有 DEV-025）。因此本次不把"报告针对 0.3.2"等同于"本工作区已交付 0.3.2"，也不在本次改动版本元数据或发布记录。

本次只整理文档，未调用 MCP、连接 Creo、运行源码测试、核查远端发布或复现缺陷。报告中的代码阅读、文件头分析、日志与命令行观察保留为外部线索，不属于本次 WorkBuddy MCP 黑盒验收。报告的"3 项已修复""Creo 9 未修复""非确定性构建"均为来源结论；在缺少逐调用完整证据时，不认定全部工具、全分支、真实并发或跨版本通过，也不把来源结论升级为本机验收。

按用户 2026-10-16 决定，报告 A 的三项"已修复"按已修复登记：BUG-042/043/044 转入[完成事项归档](../BACKLOG_COMPLETED.md)，并同口径将 B 实测 `BOOLEAN(53)` 的 BUG-038 一并转移；四项均标注"采信外部报告、本仓库无对应提交可核实、本机复现失败须重开"。新增 **DEV-026**（本轮整理）、**DEV-027**（回调 DLL 非确定性构建与注册路径解耦）、**BUG-048**（含镜像特征模型的抽壳失败）、**FEAT-031**（装配交付打包导出）；原有条目状态、优先级和目标版本不因补录自动变更，Creo 9 支持声明只按[兼容说明](../COMPATIBILITY.md)本次调整的文档口径执行。

## A：v0.3.2 缺陷回归（P1～P5、P11、S1～S10）

报告对 0.3.1 已登记的 16 项缺陷做最小复现回归，用体积、边缘坐标和变换矩阵判定。P6～P10（查询体量、capabilities、失败上下文、进度、回滚历史）本轮未复测。

| 来源编号 | 固定 ID / 去向 | 纳入范围与判断 |
| --- | --- | --- |
| P1（多区域增料） | [BUG-042](../work-items/BUG-042.md)；FEAT-008 | 据报已修复：100×100×10 底块 + 2 个互不相邻矩形一次 `extrude(add, depth=20)`，体积 103 000 = 100 000+1 000+2 000 逐项吻合（job `7fee41d0c5604db2b80b06497c30fb11`）。按用户决定转已完成；本仓库无对应修复提交，本机复现须重开。 |
| P2（共面合并） | [BUG-043](../work-items/BUG-043.md)；FEAT-006 | 据报已修复：10×10×10 草图置于 Z=10（底块顶面），`add(depth=10)` 成功并入同一实体 `bodies:1`、体积 +1 000（job `194f59d6ff9e40559d1aa9d1f82313e9`）。按用户决定转已完成；同 P1 的证据边界。 |
| P4（polyline 截面） | [BUG-044](../work-items/BUG-044.md) | 据报已修复：4 点 `polyline` + `closed:true` 拉伸成功（+1 000，同 job）。`closed:false` 开放链仍不可作实体截面，报告认为合理但建议补"截面未闭合"类可读原因。按用户决定转已完成；同 P1 的证据边界。 |
| S9（组件列表体量） | FEAT-023；FEAT-008 | 据报已修复：1 组件约 4 KB 且内联（原 2 组件 170 KB 落盘），`aliases` 增加草图几何、normal、u_axis/v_axis、`section_normal_sign`、solver 明细（`013abd07d043429b917f713d0dd35986` 之后）。补外部正例，不替代 32 KiB 单条超预算边界验收。 |
| S8（版本比较措辞） | FEAT-020；DEV-015 | 据报已改善：current 0.3.2 = latest 0.3.2 判"已是最高可比较的公开版本"，措辞正确（`creo_startup_status`）。未发布 main 与 local_dev 来源区分仍按 FEAT-020 验收。 |
| 失败诊断 | FEAT-006 | 据报明显改善：native log 给出 `BUILD_FAILED`、`PHASE=rollback_to_saved_checkpoint`、具体失败调用与错误码（如 `ProModelitemInit=-23`，job `db461369f76c44b8a9c5c581cb0fe3f2`）。补外部正例，统一错误载荷与 union dump 精简仍待验收。 |
| S1（钣金增料） | [BUG-046](../work-items/BUG-046.md)；FEAT-008 | 仍未修复：`acc_test_sm2` 底板后 10×10 草图 `extrude(mode="add", depth=5)` 报 `ProFeatureWithoptionsCreate -1`（op index 3），同模型 cut 正常（job `4601aa39ac6149bf93a04d453eb5186d`）。报告列为头号阻塞；补 0.3.2 外部复现，仍不外推旋转等入口。 |
| S3（四壁折边） | FEAT-014；FEAT-006；DEV-006 | 仍未修复：同底板边 104/105/106/107 一次挂 4 道折边，前 2 道（±X）成功、第 3 道（−Y）`-1` 并整体回滚，仍无 bend relief（job `e9dc13d031484e86b7590e390f15d879`）。释放/角部裁剪方案与明确限制仍待评估。 |
| S5（闭合壁 depth） | [BUG-032](../work-items/BUG-032.md) | 仍未修复：`sheetmetal_wall(depth=1.0, thickness=232.0)`、草图线 185 得体积 9 957 440 = 185×232×232（应为 42 920），depth 被静默替换为 thickness（job `667c71ae0958460bb63c8fd17b3f1af3`）。补 0.3.2 外部复现，开放/闭合分支分别验收。 |
| S4（壁参数语义） | BUG-032；FEAT-008 | 仍未修复：depth/thickness/草图线长三轴语义未文档化且反直觉。报告建议画清三方向并对被改写参数返回告警；先定契约再判实现。 |
| P3（字典平面 offset≠0） | [BUG-031](../work-items/BUG-031.md)；FEAT-008；FEAT-006 | 仍未修复：`{kind:datum_plane, axis:x, offset:20}` 报 `Plane reference must identify exactly one surface`，补 `reference` 容器后同样失败（job `334a1a1366374dccb15bd598f2b737ac` / `d14ce9cf5a4b419aa23d631749a010f7`）。正面：缺 `reference` 时先给明确 JSON 错误。offset 是否自动建面属候选，不预先认定实现缺陷。 |
| P5（旋转反手） | [BUG-045](../work-items/BUG-045.md)；FEAT-008 | 仍未修复：`assemble_component(rotation=[0,90,0])` 回读 `[[0,0,-1],[0,1,0],[1,0,0]]`（Ry(−90°)），仍需传 [0,-90,0]，且工具不回显变换矩阵。先核实行/列向量、局部/全局与欧拉顺序，不直接翻转符号。 |
| P11（装配交付打包） | [FEAT-031](../work-items/FEAT-031.md) | 仍未修复：`creo_export_model` 仍仅 step/stl/iges/jpeg/pdf，装配交付需手工携带 `C_*.prt` 快照。按用户决定新开能力条目，评估 `native_bundle`（.asm + 快照）或明确文档约束。 |
| S10（计划失败回滚后 operations） | BUG-018；FEAT-006；FEAT-018 | 仍未修复：计划失败后 `result.operations` 多次返回 `[]`（`e9dc13d0…` 等）。需区分已执行后回滚/失败/未执行/未知；报告建议返回 `operation_outcomes` 以便只重跑后半段，不得据执行历史只重放半步。 |
| S2（折边 flip 方向） | [BUG-047](../work-items/BUG-047.md)；FEAT-008 | 未复测：报告据 S1/S3 同代码路径未变推断未修，未做同边/同高仅切 flip 的正交实验，不据此判方向契约。 |
| S6（unbend fixed_surface） | FEAT-008；FEAT-006 | 未复测：0.3.1 传真实 surface id 可用；datum_plane 是否应被接受仍属候选，先界定"必须是材料固定面"的契约。 |
| S7（跨日连接与就绪） | BUG-008；BUG-011；FEAT-001 | 未复测：本轮会话起始仍只见 "checking"，未做跨日 `connect_creo -4` 复现。沿用既有条目，不把进程可见当作 Toolkit ready。 |

## B：v0.3.2"Creo 9"全功能回归（2 项失败、1 项行为变更、5 项观察）

报告称 0.3.2 在 Creo 9.0.0.0 上"基础建模/钣金/装配/工程图/UDF/翼型/布尔/sweep 全链路通过"，并指出 0.3.1/0.3.2 的修复验证环境为 Creo 12.4.0.0（`RELEASE_NOTES_0.3.2` 自述）。

| 来源编号 | 固定 ID / 去向 | 纳入范围与判断 |
| --- | --- | --- |
| P0-1（叶片种子 -16） | [BUG-034](../work-items/BUG-034.md)；[FEAT-030](../work-items/FEAT-030.md)；FEAT-008 | 仍未修复：两截面 smooth/straight 均 `ProMdlFiletypeLoad=-16`，失败阶段 connect；种子库与 0.3.0 相同（文件头 `PART 2128 1860 810 … 2023073`），而本机 Creo 9 自建文件头为 `PART 2023 1760 …`、模板 `PART 1934 1460 …`；`creo_list_seeds`/`creo_validate_seed` 仍只校验哈希并显示 `available: true`。补 0.3.2 外部证据，不承诺按 Creo 大版本分发种子或支持 Creo 9 运行时。 |
| P0-2（筋特征 Creo 9 失败） | [BUG-017](../work-items/BUG-017.md)；FEAT-006 | 该环境仍未修复：4 次尝试（含独立底座 + 两种材料侧）均失败，native.log 显示两阶段创建正常（`ProFeatureWithoptionsCreate=0`、`created_feature_id=84`、MATRLSIDE 重定义成功），redefine 后 `ProFeatureStatusGet != PRO_FEAT_ACTIVE`。补 Creo 9 外部证据，不覆盖本机 Creo 12.4 已测正例，也不把版本差异当已确认根因。 |
| P1-1（loft 需人工注册回调） | [BUG-007](../work-items/BUG-007.md)；[FEAT-029](../work-items/FEAT-029.md)；FEAT-008；FEAT-022 | 行为变更：0.3.0 可直接成功（体积 8 639.38），0.3.2 两截面直接放样返回 `BLEND_CALLBACK_SETUP_REQUIRED` 并要求在 Creo 辅助应用程序注册/启动回调 DLL；报告称 `callback_result.json` 不存在。属已声明机制，不作回归缺陷重开，但自动化成本与升级后重注册负担归 FEAT-029；回调状态可查询归 FEAT-008。 |
| P1-2（约束后不重求解） | [BUG-036](../work-items/BUG-036.md) | 仍未修复：comp2 固定 (-30,20,0)+Z30°，应用 mate+align+align 后 `underconstrained=false` 但 transform 仍为旧位置，实际违反新约束。补 0.3.2/Creo 9 外部证据，验证约束求解与残差，不只看标志位。 |
| P2-1（抽壳 + 镜像失败） | [BUG-048](../work-items/BUG-048.md) | 新增缺陷：块体+孔+圆角+旋转体+镜像（关于 z=0）+变换+成组后 `shell(2mm)` 失败（status 6，无具体原因），回滚正常；同一流程在 0.3.0（镜像之前抽壳）成功。先核实原生实体/特征依赖与组合限制，失败给可读原因。 |
| P2-2（失败模型无清理/恢复） | FEAT-018；BUG-001 | 仍未修复：断言值错误导致失败的 `wb_reg_pat` 进入 `status=failed, revision=0`，无法继续操作也没有删除/归档接口。补外部来源，恢复/重试/清理契约与未知结果保护仍按 FEAT-018/BUG-001 核实，不直接删记录当恢复。 |
| P2-3（union dump） | FEAT-006；FEAT-023 | 仍未修复：实体引用错误时 pydantic 校验错误仍含 60+ 操作类型名。补外部来源，错误载荷预算与可操作摘要按两项继续验收。 |
| P2-4（过期 surface id 报 -23） | FEAT-006；FEAT-008 | 仍未修复：`creo_hole` 传失效几何 ID 报 `ProModelitemInit=-23`，提示不直观。建议 resolve 层给"surface id 不存在，请 inspect 后刷新"类指引；与 FEAT-008 引用契约合并验收。 |
| P2-5（truncated 标志） | FEAT-023；BUG-013 | 观察：0.3.1 的 compact 分页工作正常，但 `creo_inspect_model` 未带 `truncated`/`complete` 标志。报告建议始终显式标注；与 BUG-013 默认摘要、section 分页一起验收。 |
| 已修复确认（布尔类型） | [BUG-038](../work-items/BUG-038.md) | 本环境实测 `true` 正确存为 `BOOLEAN(53)=True`（0.3.0 为 REAL(52)=1）。按与报告 A 相同的口径转已完成并归档，标注外部证据与无本地提交可核实。 |
| 已修复确认（孔无去料） | BUG-022（已归档） | 本环境实测 offset 置于体外时明确失败并回滚，BUG-022 生效；补充归档条目的外部正例，不改变其历史受测身份。 |
| 建议：版本兼容矩阵 | DEV-005；本轮文档口径 | 报告要求为每个修复/工具标注已验证 Creo 版本并在 README/RELEASE_NOTES 声明边界。矩阵与能力说明仍按 DEV-005 维护；本次只把 Creo 9/Toolkit 9 纳入支持与要求范围并标注运行时未验收。 |
| 建议：种子与筋的 CI 冒烟 | DEV-006 | 报告建议增加旧版冒烟（筋、种子加载、dimension_pattern）。归入回归清单范围评估，不因该建议引入 Creo 9 独立验收门槛。 |

报告同时给出成功范围（拉伸 120 000 精确、孔 `material_removed` 785.398/453.842、圆角 −321.9、旋转 270°、镜像翻倍、布尔 2→1、钣金第一壁/法兰/展开/折回、装配 30° 矩阵、工程图 PDF 15 543 B、UDF、NACA 0012 更新、`execute_plan` 组合）。这些只保留为对应环境的外部报告记录，不改写当前兼容声明。

## C：回调 DLL 非确定性构建（v0.3.2 用户反馈）

| 来源编号 | 固定 ID / 去向 | 纳入范围与判断 |
| --- | --- | --- |
| 1（核心：非确定性构建 + 哈希目录） | [DEV-027](../work-items/DEV-027.md)；FEAT-029 | 新增工程项：`native/blend_sync.cpp` 与 0.3.1 逐字节相同（sha256 `c2c6d4a6…`），但 0.3.1/0.3.2 及同机同工具链两次编译产出不同 DLL（`96430578b3ac85f0`、`0e46ef9d76575785`、`c6dbf37b5335d7a6`、`e60521d2…`，均 3 384 832 B）；`prepare_callback()` 以 sha256 建不可变目录并被 `protk.dat` 引用，导致每次重编译使 Creo 已注册条目指向失效路径，`build/blend_callback/` 3 小时内累积 3 个 sha 目录（2 个为噪音）。注册路径与构建哈希解耦、过期目录清理、`registered_dll_stale` 告警、`/Brepro` 均列为候选，需先核实现有实现与协议版本耦合。 |
| 2（副本校验无自愈） | DEV-027；FEAT-029 | 副本哈希不一致时只抛 `Immutable Blend callback copy was changed; inspect it before setup`。报告建议区分"副本被外部改动"与"登记过期"并自动重建登记；先核实该分支的实际触发条件与安全边界，不直接放开校验。 |
| 3（观察：版本发现已化解） | FEAT-020；DEV-015 | 0.3.1 确无公开 Release、0.3.2 说明如实不追写；`creo_check_update` 已能发现 v0.3.2，上轮 Q3 缺口按预期化解。补正向来源，本地领先/local_dev 文案与 Release 核对仍分别归 FEAT-020/DEV-015。 |
| 3（观察：文档收录反馈） | [DEV-024](../work-items/DEV-024.md)；DEV-026 | 报告肯定 0.3.0/0.3.1 报告与两份回调反馈已被收进 `docs/validation/feedback-2026-10-16/` 并登记为 BUG-029～047。本轮归档与映射延续该流程，不视为新缺陷。 |
| 4（正向：BUG-007/BUG-009/新模块） | BUG-007；BUG-009；DEV-002 | 直接放样 12 s 内快速失败且未回退挂死；紧随其后的第二个建模任务未误报 busy（volume 11 626.666…）；3 截面自动匹配 volume 22 159.999999999996 且 `saved_file_reloaded_and_verified=true`；升级后新增 `recovery`/`startup_state`/`windows_boot` 模块导入正常。补充为对应条目的外部来源，不代替本机验收。 |
| 5（作者提问 Q1～Q5） | DEV-027；FEAT-029 | 报告方提出是否解耦注册路径、是否清理过期目录、是否自动重建登记、是否用 `/Brepro`，以及可提供更多材料。仅作来源记录，不构成本轮执行指令或已确认方案。 |

## 正向结果、近似与后续验收

- 报告 A 未复测 P6～P10；S2/S6/S7 明确标注未复测或推断，不因同一报告称其他项已修复而外推。
- 报告 B 的通过项覆盖 Creo 9.0.0.0 单机单会话；其"大部分正常"不构成全工具、全分支或并发验收。
- 报告 C 的 DLL 哈希、目录数与体积为报告方本机观测，本次未复现；工作区重编译后出现"登记哈希过期"的机制性推理保留为报告推断。
- 后续按固定 ID 补最小完整输入，先复现并区分适用性/契约/实现缺陷，再确定方案。受支持正例检查原生类型、几何/尺寸/体积、保存重载 true 与 revision；负例保留原始错误、检查点和后续可用性。摘录的 job/模型标识保留在对应工作卡；完整来源标识保留在原报告。
- 本次文档检查见 [DEV-026.json](DEV-026.json)。
