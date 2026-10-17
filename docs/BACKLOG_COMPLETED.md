# 开发台账完成事项归档

归档建立：2026-10-15；最近追加：2026-10-17。当前排期与状态统一查看[主台账](BACKLOG.md)；本文件保留完成摘要、证据与历史来源，不承担当前排期。后续完成事项追加到本文件，主台账移除对应行。

## 已完成事项

以下保留原验收范围与目标版本，不因当前源码已到 0.3.5 而改写历史受测身份。2026-10-15 用户取消全项目 Creo 10 独立验收门槛，历史交接/复测安排不再作为当前要求；朋友反馈具体问题后再跟进。BUG-022 按已有本机证据完成并归档；DEV-015 的历史主干集成已核实，公开交付由 DEV-025 / v0.3.2 累计承接。BUG-038/042/043/044 于 2026-10-16 按用户决定采信 0.3.2 外部报告转已完成，均标注"本仓库无对应提交可核实、本机复现失败须重开"，不代表本机复验通过。

| ID | 优先级 | 状态 | 目标版本 | 完成摘要与证据 |
| --- | --- | --- | --- | --- |
| [BUG-056](work-items/BUG-056.md) | P1 | 已完成（用户确认关闭） | 未排期 | Toolkit 通道验证通过后约 37～41 秒静默失效（-4/exit 20），Creo 存活、用户确认非人为。2026-10-17 DEV-036 两轮核实：定位为跨批次遗留 nmsd（名字服务）会话信息失效——失败请求未到达 Creo（trail 无 IPC 初始化记录），「40 秒周期」为客户端轮询+快照 30 秒 stale 期伪影，服务侧探测/快照/分类无缺陷；`creo_session_status` 增只读进程快照（服务重启后生效）。清理遗留 nmsd 并重启 Creo 后，38 次探测跨约 7.5 分钟+空闲对照与建模闭环（rev 0→2、保存重载、体积精确一致）全部通过。nmsd 内部触发器为黑盒残余假设；T07/T08、WorkBuddy 黑盒由 DEV-036 跟踪。证据见[核实记录](validation/BUG-056-DEV-036-investigation-2026-10-17.md)。 |
| [DEV-038](work-items/DEV-038.md) | P2 | 已完成 | 未排期 | 2026-10-17 按 humanizer-zh 改写主台账的 85 项任务说明，解释常见术语，保留任务编号、优先级、目标版本和证据链接。同步另一次 DEV-036 调查的最新进度，未自行关闭任务。任务、表格、链接和其他文件摘要检查通过；本次只改文字，未执行建模或发布。 |
| [DEV-037](work-items/DEV-037.md) | P2 | 已完成 | 未排期 | 2026-10-17 核对较早完成事项均已归档，迁入旧进展与 10 段反馈补录并折叠显示，主台账从 56,381 缩至 34,736 字节（减少 38.4%）。原有 85 项未完成行、39 项完成行及其状态/验收边界保持；ID、链接/入站锚点、表格、历史原件/上一轮修改摘要和 diff 检查通过。仅文档整理，未连接 Toolkit、未升版或发布。 |
| [DEV-035](work-items/DEV-035.md) | P1 | 已完成（发布候选） | 0.3.5 | 用户指定统一交付DEV-033/BUG-054、DEV-034/BUG-055及反馈/BUG-056登记；两目录各307项单元/增量检查、84工具、SDK实际编译/6521常量、12项ABI、独立安装和9种子ZIP通过。已知通道问题和M2未取得范围保留；实际main/Release/四附件SHA256在[PR #10](https://github.com/wudahua/MCP_CREO_MechDog/pull/10)回填，见[验收](validation/RELEASE-0.3.5.md)。 |
| [BUG-054](work-items/BUG-054.md) | P1 | 已完成（本机实机及WorkBuddy已测范围） | 0.3.5 | 拉伸/旋转切除零去料曾静默成功。2026-10-17 在 0.3.4 复现并按 DEV-033 修复：cut 前后测体积，零去料抛错回滚（revision 不变、别名无残留），成功返回 material_removed_mm3；T01～T08 实机与 WorkBuddy 5 场景黑盒均通过，revolve 正反例纳入。外部 Creo 10/9、thin/装配/钣金 cut 未测；BUG-016 不随本项关闭。证据见[验收记录](validation/BUG-054-cut-material-2026-10-17.md)与[黑盒记录](validation/BUG-054-WorkBuddy-acceptance-2026-10-17.md)。 |
| [BUG-055](work-items/BUG-055.md) | P1 | 已完成（WorkBuddy核心范围，M2未完成） | 0.3.5 | 根因链闭环：WorkBuddy 实测客户端把显式 null 降级为空串（服务端回显 received ''），服务端各层无转换；修复后空串精确拒绝、省略字段替代路径端到端成功。M1 abandoned 闭环+幂等+历史保留全过；M2 终态与稳定通道字面 null 对照因通道静默掉线未取得（保护按契约保留），外部 Creo 9 未复测。2026-10-17 补录：BUG-056 关闭后 M2 已按用户确认经 live 取证 abandon_new 收尾（abandoned/rev 0/保护清除），字面 null 稳定通道对照仍归 DEV-036 T07。 |
| [DEV-033](work-items/DEV-033.md) | P1 | 已完成（本机实机及WorkBuddy已测范围） | 0.3.5 | 2026-10-17 按 G0～G5 执行 BUG-054：会话条件核对后复现、确定孔类一致契约、最小修复（native 守卫+docstring+compact 白名单+4 项单元回归）、实机 T01～T08 与 WorkBuddy 5 场景黑盒全通过（revolve 正反例纳入），台账/能力说明同步。未测边界（外部 Creo 10/9、thin/装配/钣金 cut）保留；未合入 main、未发布。 |
| [DEV-034](work-items/DEV-034.md) | P1 | 已完成（WorkBuddy核心范围，M2未完成） | 0.3.5 | G0～G4 完成后 WorkBuddy 核心验收通过（客户端 null→空串降级实证、M1 闭环、空串精确拒绝、字面 null 接受、unknown 保护保留），开发者只读核对一致。未取得：M2 终态与稳定通道对照（通道 37–41 秒静默掉线三次，环境异常，是否另立条目待用户定）、外部 Creo 9。事实边界：同名残留模型触发 abandon owned 保护、journal 临时名过深数据根逼近 260 路径上限。不升版、不合入、不发布。 |
| [DEV-032](work-items/DEV-032.md) | P1 | 已完成（发布候选） | 0.3.4 | 用户指定版本并要求汇总七个待合分支；BUG-001按用户决定关闭，FEAT-018/029仍验收中。两目录各297项单元/增量语言、独立SDK编译、12项ABI、84工具、源码分发及九种子ZIP安装通过；实机/WorkBuddy本轮未执行。实际main/标签/Release/四附件SHA256回填[PR #9](https://github.com/wudahua/MCP_CREO_MechDog/pull/9)，见[本版记录](validation/RELEASE-0.3.4.md)。 |
| [BUG-001](work-items/BUG-001.md) | P0 | 已完成（用户决定关闭） | 0.3.4 | 2026-10-17用户要求先关闭并将待合分支一并交付main。正式恢复实现及部分实机证据保留；IPC初始化通信失败/Creo无响应根因未定，完整恢复与WorkBuddy未完成，不代表全部验收通过。详见[离线排查](validation/BUG-001-hang-offline-2026-10-17.md)；后续复现沿用本ID重开，FEAT-018/029仍验收中。 |
| [DEV-029](work-items/DEV-029.md) | P1 | 已完成 | 0.3.3 | main@9ee923c、v0.3.3 与公开 [Pre-release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.3.3)一致；两目录各263项、原生回归和主干CI通过，四份主干附件已回下载核对SHA256；最终交付见 [PR #8](https://github.com/wudahua/MCP_CREO_MechDog/pull/8)，[候选验收](validation/RELEASE-0.3.3.md)及未测范围保留。 |
| [DEV-015](work-items/DEV-015.md) | P1 | 已完成（历史主干准备与集成） | 0.3.1 | 已核实 main@515d50b；未存在的 0.3.1 Release 不补造，累计公开交付由 DEV-025 / 0.3.2 承接。 |
| [DEV-025](work-items/DEV-025.md) | P1 | 已完成（发布候选验收） | 0.3.2 | 三批代码及完成文档集成，新目录独立安装、247 项单元、匹配 SDK 构建、8 成功/1 预期回滚作业、82 工具/9 种子和种子 ZIP 实际安装通过。见[本次证据](validation/RELEASE-0.3.2.md)；实际 main/标签/公开附件交付在 [PR #6](https://github.com/wudahua/MCP_CREO_MechDog/pull/6) 回填。 |
| [DEV-028](work-items/DEV-028.md) | P1 | 已完成 | 未排期 | 2026-10-16 Creo 9 编译与安装闭环：统一 BUG-033、DEV-019～022；14 项新增定向回归、260 项完整单元/语言守卫、本机 Creo 12.4 SDK 构建、显式环境真实 x64 编译运行及七个原生作业全部保存重载通过。[本批证据](validation/DEV-028.md)明确桌面启动环境、普通宿主 -4、此前失败与未测范围；Creo 9 实机编译/运行时未验收，版本 0.3.1，一个本地提交，不推送/发布。 后续 [WorkBuddy](validation/DEV-028-WorkBuddy-review-20261016.md) 的部署/通用单孔/通孔+盲孔已测范围通过，底板专用入口参数受阻仍未覆盖；本次仅补录，不改公共接口。 |
| [BUG-033](work-items/BUG-033.md) | P1 | 已完成 | 未排期 | 本机 SDK 生成 MECHDOG_HAS 探针，geometry/generic 两孔调用在两探针均存在时走原路径；常量表包含位置前移。缺失/部分/完整 SDK 夹具及 Creo 12.4 通用孔/底板孔的几何与保存重载通过，见 DEV-028；本机无 Creo 9 SDK，不外推实际旧版编译或运行时。 |
| [DEV-019](work-items/DEV-019.md) | P2 | 已完成 | 未排期 | 构建失败只读日志尾部 128 KiB、最多 15 条 error 摘要；仅实际 C2065 的 PRO_ 标识符提示 SDK 版本方向。纯函数与 bridge 失败路径夹具通过，不改变 MCP stdout，见 DEV-028。 |
| [DEV-020](work-items/DEV-020.md) | P2 | 已完成 | 未排期 | INSTALL 补微软官方 --includeRecommended 命令、静默缺组件症状及与显式环境/Python 占位一致的排错表；官方来源和文档检查通过，未运行 VS 安装器，见 DEV-028。 |
| [DEV-021](work-items/DEV-021.md) | P2 | 已完成 | 未排期 | config.json + setup.ps1 -VcVars64Env 两层完整 INCLUDE/LIB/PATH，校验/回写/环境检查/前置自检与默认路径兼容；PowerShell/cmd 夹具及真实 x64 编译运行通过，受限机器完整安装未验证，见 DEV-028。 |
| [DEV-022](work-items/DEV-022.md) | P2 | 已完成 | 未排期 | WindowsApps Python 在执行前提示 Microsoft Store placeholder 和 -Python；自动发现/显式路径夹具及真实 Python -CheckOnly 通过，真实商店交互未验证，见 DEV-028。 |
| [BUG-008](work-items/BUG-008.md) | P0 | 已完成 | 未排期 | 2026-10-16 按本机 Creo 12.4 已验证范围关闭：246 项单元，断开/探针有界保护，同实现真实冷态自动归档/重建/单次启动，以及新 [WorkBuddy](validation/BUG-008-WorkBuddy-reboot-retest-result-2026-10-16.md) 单次/重叠 retry、120 mm³ 建模/保存重载和 unknown 保护通过；见[关闭复核](validation/BUG-008-closure-2026-10-16.md)。WorkBuddy 冷态/异常环境和历史完整故障链仍未验证；未知任务不解锁，BUG-001/005/011 保留，未推送或发布。 |
| [BUG-009](work-items/BUG-009.md) | P0 | 已完成 | 未排期 | 模型锁内收尾、释放后发布终态；busy 保留协议错误并补占用/重试诊断。210 项开发检查及本机 Creo 12.4 [WorkBuddy 验收](validation/BUG-009-WorkBuddy-acceptance-20261015.md)已测范围通过；报告 33 个作业只读核对一致，协议疑点及即时性边界已[复核](validation/BUG-009.md#2026-10-15-验收复核与关闭)。真实挂死/失联恢复及其他宿主范围不外推，服务仍 0.3.1，未另发布。 |
| [BUG-002](work-items/BUG-002.md) | P1 | 已完成 | 0.2.6 | Windows 共享读取、单步原子替换、有界重试及自有临时文件清理；90 项单元、4,000 次压力写入与 Creo 12.4 并发/MCP 验收通过；原外部复测安排已随 DEV-018 取消。[本次证据](validation/BUG-002.md) |
| [BUG-006](work-items/BUG-006.md) | P1 | 已完成 | 0.3.0 | 修复提交 `ccc7366`：axis_pattern 兼容 datum_feature 轴标签，补齐逐工具引用契约与可操作错误；9 项新回归、158 项检查、stdio schema 与全新安装通过。用户 N1 确认后，本轮报告 P0-1 再次记录别名归一化通过及 by_tool 15 工具；仍无完整任务/模型 ID 清单，其他包装差异归 FEAT-008。开发者 timeout 保留；见 [证据](validation/BUG-006.md)、[引用说明](REFERENCE_SYNTAX.md) 与 [复测步骤](validation/BUG-006-WorkBuddy-test.md) |
| [BUG-007](work-items/BUG-007.md) | P0 | 已完成 | 未排期 | 本环境核心验收通过：标签引用两/三截面straight/smooth、已有底座追加、计划入口、几何/原生参数/保存重载/revision/回滚及后续通道；[最终WorkBuddy报告](validation/BUG-007-WorkBuddy-acceptance-2026-10-14.md)。整数公开引用失败单列BUG-028，开发者stdio整数成功证据保留；Creo10/并发/外部模态/策略未测，不外推 |
| [BUG-022](work-items/BUG-022.md) | P1 | 已完成 | 未排期 | 本机 Creo 12.4 边参考定位修复及 [WorkBuddy 四场景](validation/BUG-022-WorkBuddy-retest-20261015.md)通过，0.3.1 报告补真实去料正例；用户取消 Creo 10 独立验收门槛后按本机已测范围关闭。原报告来源、根因未确认及未测事实保留，收到新反馈再沿用本 ID 跟进。 |
| [FEAT-019](work-items/FEAT-019.md) | P1 | 已完成 | 0.2.6 | 用户接受 WorkBuddy / Creo 12.4 最终 MCP 验收：自动启动与真实 Toolkit 就绪、新建/草图/拉伸/尺寸驱动/倒角、保存重载通过；Codex MCP 只读复核 6 个成功修改任务与 revision=6 / volume=9980 mm³；121 项 Windows 单元/语言检查通过；Creo 10 及真实多客户端并发/退出后重连未测，Codex 冷启动失败单列 BUG-005；见 [证据](validation/FEAT-019.md) |
| [DEV-001](work-items/DEV-001.md) | P1 | 已完成 | 0.2.6 | 开发入口、台账、模板、语言基线与守卫、Windows CI 配置、源码分发同步；[本批验收](validation/DEV-001.md) |
| DEV-010 | P2 | 已完成 | 0.2.6 | 根 AGENTS.md 与[开发入口](DEVELOPMENT.md#workbuddy-测试约定)统一 WorkBuddy 最终 MCP 黑盒测试约定，不查看源码、不运行本地源码测试；2026-10-13 Windows 文档引用与约定一致性检查通过，未执行 WorkBuddy 测试 |
| [DEV-011](work-items/DEV-011.md) | P1 | 已完成 | 0.2.6 | 合并近两日三个开发分支至 main；121 项单元/语言守卫、SDK 构建、协议、解压与九种子 ZIP 安装通过；v0.2.6 预发布，源码/种子附件及 SHA256；本轮 Toolkit 超时、Creo 10 未测、BUG-005 保留，见 [发布证据](validation/RELEASE-0.2.6.md) |
| [DEV-012](work-items/DEV-012.md) | P2 | 已完成 | 0.2.6 文档补充 | 根据用户确认与已有 Creo 12.4 实机证据，统一 Creo 10 / Creo 12 可用性说明并补充 12.4 安装示例；文档链接与范围一致性检查通过，GitHub Release 正文已修改并回读核对；历史测试日期、未测分支、BUG-005、标签及附件保持原样；本次未执行新实机测试，见 [记录](work-items/DEV-012.md) |
| [DEV-013](work-items/DEV-013.md) | P1 | 已完成 | 0.3.0 | PR #3 普通合并保留历史，v0.3.0 Pre-release 已公开；本地/全新安装各 158 项及 Windows CI 通过，82 工具/九种子、四份附件回下载与摘要、公开更新发现通过；FEAT-020 未测场景、DEV-002 后续批次及 BUG-005 保留；见 [发布证据](validation/RELEASE-0.3.0.md) |
| [DEV-014](work-items/DEV-014.md) | P2 | 已完成 | 0.3.0 文档补录 | 原报告归档与原件 SHA256 一致，补录统计/覆盖边界并映射固定 ID，P0 三项建立独立卡；BUG-006/FEAT-020 同步本轮证据与未测范围。文档链接、ID/来源映射、表格和 diff 检查通过，见 [检查记录](validation/DEV-014.json)；仅文档整理，未修复缺陷或新做建模测试 |
| [DEV-016](work-items/DEV-016.md) | P2 | 已完成 | 未排期 | 2026-10-15 精简主台账并归档原有 10 项完成记录，合并三项重复登记；原有 62 个 ID 的状态、优先级与目标版本保留，文档完整性及链接检查通过。 |
| [DEV-017](work-items/DEV-017.md) | P2 | 已完成 | 未排期 | 原样归档0.3.1全量报告，17个问题及部署建议完成去重映射；新增4项待核实缺陷与4项能力建议，同步复验和覆盖边界。报告字节/哈希、ID保留、映射与本次引用检查通过，见[文档证据](validation/DEV-017.json)；DEV-002同期链接单独记录，未修复程序或新增建模测试。 |
| [DEV-018](work-items/DEV-018.md) | P2 | 已完成 | 未排期 | 按用户要求取消全项目 Creo 10 独立复测、双版本验收及正式基线门槛，同步当前规则、台账和任务卡；DEV-002 第二批按开发与 WorkBuddy 已测范围完成，BUG-022 按本机证据归档。历史报告与未测事实保留，收到朋友新反馈再跟进；[文档检查](validation/DEV-018.json)通过，无新程序或实机测试。 |
| DEV-023 | P2 | 已完成 | 流程规范（不升版） | 2026-10-16 按用户要求，将每次合入 main 必须发布对应版本 GitHub Release 写入[根级规范](../AGENTS.md#合入-main-与-release项目全局)、[开发入口](DEVELOPMENT.md)与[发布规则](development/RELEASING.md#合入-main-必须同步发布)，同步 PR 模板；覆盖文档/配置变更，要求版本、主干提交、标签及附件一致，发布未完成则交付未完成。Windows 下 9 项规则检查、13 个本地文档链接及定向 git diff --check 通过；仅文档变更，版本仍为 0.3.1，未执行合并、实际发布或原生测试。 |
| [DEV-024](work-items/DEV-024.md) | P2 | 已完成 | 未排期 | 2026-10-16 阅读并原样归档下载目录4份Markdown，41个编号问题及构建线索去重映射；新增14项待核实缺陷BUG-034～047、2项能力候选FEAT-029～030，同步已有工作卡及证据边界。[文档检查](validation/DEV-024.json)核对原件/哈希、ID、来源、链接与表格；保留同期BUG-008外部更新，仅同步文档，未复现、修复或执行新建模测试。 |
| [BUG-038](work-items/BUG-038.md) | P2 | 已完成 | 未排期 | 2026-10-16 按用户决定采信 [0.3.2 报告 B](validation/FEEDBACK-0.3.2.md) 的 Creo 9.0.0.0 实测（`true` 存为 `BOOLEAN(53)=True`，0.3.0 为 REAL(52)=1）转已完成：本仓库无对应修复提交可核实，未在本机复验布尔映射与保存重载；本机复现失败须重开本 ID。 |
| [BUG-042](work-items/BUG-042.md) | P1 | 已完成 | 未排期 | 2026-10-16 按用户决定采信 [0.3.2 报告 A](validation/FEEDBACK-0.3.2.md) P1（100×100×10 底块 + 2 个互不相邻矩形一次 add，体积 103 000 逐项吻合，job `7fee41d0c5604db2b80b06497c30fb11`）转已完成：本仓库无对应修复提交可核实，未在本机复验多区域增料；本机复现失败须重开本 ID。 |
| [BUG-043](work-items/BUG-043.md) | P1 | 已完成 | 未排期 | 2026-10-16 按用户决定采信 [0.3.2 报告 A](validation/FEEDBACK-0.3.2.md) P2（面贴合 add 成功并入同一实体 `bodies:1`、体积 +1 000，job `194f59d6ff9e40559d1aa9d1f82313e9`）转已完成：本仓库无对应修复提交可核实，未在本机复验共面合并；本机复现失败须重开本 ID。 |
| [BUG-044](work-items/BUG-044.md) | P2 | 已完成 | 未排期 | 2026-10-16 按用户决定采信 [0.3.2 报告 A](validation/FEEDBACK-0.3.2.md) P4（闭合 `polyline` 截面拉伸成功、体积 +1 000）转已完成：开放链不可作实体截面属预期限制；本仓库无对应修复提交可核实，未在本机复验 polyline 截面；本机复现失败须重开本 ID。 |
| [DEV-026](work-items/DEV-026.md) | P2 | 已完成 | 未排期 | 2026-10-16 归档并映射下载目录 3 份 0.3.2 报告（A/B/C 与原件逐字节一致），新增 DEV-027、BUG-048、FEAT-031；按用户决定把 BUG-038/042/043/044 转入本归档并标注外部证据边界；Creo 9 与 Toolkit 9 纳入文档支持范围。[文档检查](validation/DEV-026.json)核对原件/哈希、编号覆盖、ID 与链接；仅同步文档，未复现、修复或执行新建模测试。 |

## 历史来源索引

以下仅保留来源编号与固定 ID 的对照；其中涉及未完成事项时，以主台账当前记录为准。报告中的优先级编号不等于仓库优先级或交付状态。

### WorkBuddy 0.3.0 报告编号

来源：[2026-10-14 原始报告](validation/MCP_CREO_MechDog_0.3.0_全量实测问题报告.md)及[证据边界](validation/WORKBUDDY-0.3.0.md)。P0-3.1/3.2 归 BUG-007，P0-3.3/3.4 归 BUG-008，P0-2 归 BUG-009。

| 来源编号 | 固定 ID |
| --- | --- |
| P1-5 | BUG-010 |
| P1-8 | BUG-011 |
| P1-7；P3-2 | BUG-012 |
| P1-6（原 P2-1）；N2；P3-4；Creo10报告问题7 | BUG-013 |
| P1-2/P2-13；P2-8；P3-1/P3-5；Creo10报告问题9 | BUG-014 |
| P1-7 根因补充；第八节 P2 | BUG-015 |
| P2-10 | BUG-016 |
| P2-11（rib）；Creo10尺寸编辑报告问题2 | BUG-017 |
| P2-4；P2-8 的空 operations | BUG-018 |
| P1-3 | BUG-019 |
| P2-12 | BUG-020 |
| P0-3 建议4/5；第八节 | FEAT-021 |
| 第二节2.1；第八节 | FEAT-022 |
| P2-5；P3-3 | FEAT-023 |
| N4；第八节 | FEAT-024 |

对已有条目的复用关系如下，验收条件合并到主台账或独立工作卡中，不在此重复维护。

| 报告项 | 固定 ID / 去向 |
| --- | --- |
| P0-1；兼容别名 | BUG-006 / FEAT-008 |
| P1-1 | FEAT-005 |
| P1-4；P2-3/P2-11；N3 | FEAT-006 |
| P2-9 | FEAT-004 |
| P2-2 | FEAT-008 |
| P2-6 | FEAT-001 / BUG-008 |
| P2-7 | DEV-005 / DEV-012 |
| P3-2；恢复建议 | BUG-001 / FEAT-018 |
| 更新接口及升级后重启连接器 | FEAT-020 / FEAT-022 |
| 全量测试范围、覆盖限制及重启事件 | DEV-006 / DEV-007 / DEV-014 |

### 原问题清单编号

来源：[原问题快照](待完善功能清单.md)。下列编号属于旧清单，不作为新增已证实缺陷；实施前须整理可移植的复现输入和仓库内证据。

| 来源编号 | 固定 ID |
| --- | --- |
| 1 | FEAT-001 |
| 2 | BUG-001 |
| 3 | FEAT-002 |
| 4 | FEAT-003 |
| 5 | FEAT-004 |
| 6 | BUG-002 |
| 7 | BUG-003 |
| 8 | BUG-004 |
| 9 | FEAT-005 |
| 10 | FEAT-006 |
| 11 | FEAT-007 |
| 12 | FEAT-008 |
| 13 | DEV-005 |
| 14 | DEV-006 |

保留原快照澄清：工具/参数名不稳定需原始日志，不能直接认定服务端缺陷；旧关系式再生失败曾因取错尺寸；Creo 12 直接混合因人工加载等待，尚无有效几何验收；翼型入口已统一 `pivot_fraction`。

### 未来能力候选编号

来源：[NEXT_STEPS_025](NEXT_STEPS_025.md)。此处仅供溯源，范围、状态与排期以主台账为准。

| 来源编号 | 固定 ID |
| --- | --- |
| 功能建议 1 | FEAT-009 |
| 功能建议 2 | FEAT-010 |
| 功能建议 3 | FEAT-011 |
| 功能建议 4 | FEAT-012 |
| 功能建议 5 | FEAT-013 |
| 功能建议 6 | FEAT-014 |
| 功能建议 7 | FEAT-015 |
| 完善建议 2 | FEAT-016 |
| 完善建议 3 | FEAT-017 |
| 完善建议 4 | FEAT-018 |
| 完善建议 1 | DEV-007 |


## 历史进展与反馈补录

2026-10-17 按 [DEV-037](work-items/DEV-037.md) 从主台账迁入。以下保存整理前的阶段叙述和反馈映射，包括已完成事项及未完成事项的历史观察；其中“未合入”“待验收”“待用户决定”等均是当时状态，不承担当前排期，也不表示相关未完成条目已经关闭。当前状态统一查看[主台账](BACKLOG.md)。

<details>
<summary>整理前阶段进展（2026-10-15～17）</summary>

- 2026-10-17 根据当前进度建立 [DEV-036：Toolkit 通道静默掉线核实、修复与验收](work-items/DEV-036.md)（P1，待开发），接续 0.3.5 交付后的 BUG-056。先离线区分快照陈旧/探测失败/真实 IPC 失效/进程退出，满足卡死核对与当前会话可操作条件后再做空闲及间隔探测、定位修复和分层验收；M2 保护保持，实际处置另须明确选择。DEV-027/DEV-030 的最新 Creo 10 反馈继续原卡跟踪；BUG-056 仍待核实、FEAT-018/029 仍验收中。本轮仅建卡和文档同步，目标版本未排期，不恢复 Toolkit 联调。

- 2026-10-17 [0.3.4 / Creo 10 构建与回调反馈补录](validation/FEEDBACK-0.3.4-CREO10-2026-10-17.md)（0.3.5 交付后登记，不新建 ID）：[DEV-027](work-items/DEV-027.md) 核心问题获首个外部 Creo 10 实测正例——0.3.4 loader/payload 分层实测修复"重编译致注册失效"（删除 loader.dll 后同 SHA256 恢复、`protk.dat` 不变），剩余范围收窄为 payload 目录清理/当前标记（该环境 6 个/17 MB 只增不减，0.3.5 源码仍无清理逻辑）；vcvars64_env 恰好三键再报归 [DEV-030](work-items/DEV-030.md) 需求核对（0.3.5 源码一致）；[FEAT-029](work-items/FEAT-029.md) 补 readiness 双义观察；[BUG-034](work-items/BUG-034.md)/[FEAT-030](work-items/FEAT-030.md) 补 Creo 10 三截面种子正例对照。原件逐字节归档；本轮仅同步文档，不清理目录、不重演删除测试、不连接 Toolkit。同日 Creo 9 报告此前已随 BUG-055/DEV-034 闭环，不重复登记。

- 2026-10-17 按用户要求通过 [DEV-035](work-items/DEV-035.md)统一提交并交付0.3.5：DEV-033/BUG-054、DEV-034/BUG-055及反馈/BUG-056登记保留全部历史；本轮做适用离线/单元/SDK/分发核对，不新增Creo连接。BUG-054与BUG-055核心范围完成并归档，M2终态未取得、BUG-056待核实、FEAT-018/029验收中保持，实际主干/Release信息在交付PR回填。

- 2026-10-17 新增 [BUG-056：Toolkit 通道验证通过后约 40 秒静默失效](work-items/BUG-056.md)（P1 待核实）。WorkBuddy 验收期间三次"验证通过→37～41 秒→`not_found_or_unreadable`/`connect_creo` -4/探测退出码 20"，Creo 进程存活、可重连、用户确认无手动操作；与 BUG-001 卡死区分不重开。先低风险间隔探测复现并取 Creo 侧证据，再排除许可证/多协调器/空闲超时等假设；不自动重连、不清保护。M2 的收尾受阻于此项。

- 2026-10-17 [BUG-055 WorkBuddy 黑盒验收通过](validation/BUG-055-WorkBuddy-acceptance-2026-10-17.md)（受测 `26a3edd`，开发者只读核对逐项一致）：核心契约全部符合——schema 空值契约可见、M1 经省略字段完整闭环（abandoned/rev 0/幂等/原作业保留）、空串精确拒绝回显 `received ''`、字面 "null" 按 SDK 预解析接受、M2 恢复作业 unknown_outcome 时保护按契约保留未重放。**决定性证据：WorkBuddy 客户端实测把显式 JSON null 降级为空串**——外部报告根因链闭环（转换在客户端序列化层，旧代码误报 stale，修复后可观察且省略字段替代路径可用）。未取得：M2 最终终态与稳定通道下字面 null 对照（通道三次静默掉线 37–41 秒节奏、worker_exit_code=20，环境异常超本卡范围、不据此重开 BUG-001，是否另立条目待用户决定）、工具总数（capabilities 响应超 WorkBuddy 客户端上限）。[DEV-034](work-items/DEV-034.md) G0～G5 完成。

- 2026-10-17 [DEV-034 G0～G4 完成](work-items/DEV-034.md)：服务端各层不存在 null→空串转换（受测 mcp 2.3.0 与 v0.3.4 锁定一致），空串产生与外部报告逐字一致的 stale 错误，字面 "null" 被 SDK 预解析为 null；按此确定契约（null/省略合法等价、空串/空白精确拒绝、非空 ID 精确匹配、stale 拆分报告实际值）完成最小修复并同步 schema 描述与 [MODEL_RECOVERY.md](MODEL_RECOVERY.md)。新增 `tests/unit/test_reconciliation_mcp.py` 真实 stdio 协议回归 6/6，全量单测 307/307，dev_check 通过；实机（Creo 12.4）自然失败模型经真实 MCP 显式 null apply 到 succeeded，空串实机协议得到精确输入错误。BUG-055 转"已修复，WorkBuddy 验收待执行"，[提示词](validation/BUG-055-WorkBuddy-test.md)已备；外部 Creo 9 环境未复测记为未验证；未升版、未合入 main。证据见 [BUG-055-fix-2026-10-17.md](validation/BUG-055-fix-2026-10-17.md)。

- 2026-10-17 根据用户最新修改后的台账，DEV-033/BUG-054 已完成实机及 WorkBuddy 验收；下一轮建立 [DEV-034：恢复工具 MCP 空值契约核实、修复与验收](work-items/DEV-034.md)，聚焦 P1 BUG-055。先以真实 stdio/独立客户端核对 null、省略及 stale 差异，再最小修复、授权保护回归和正式 MCP 恢复闭环；本轮仅建卡，BUG-055 保持待核实，目标版本未排期，FEAT-018/029 不随本卡关闭。

- 2026-10-17 [BUG-054 WorkBuddy 黑盒验收通过](validation/BUG-054-WorkBuddy-acceptance-2026-10-17.md)：5 场景全部符合预期（有效切除 40π、板外/重复/revolve 无交集按契约失败且体积/revision/sha256 不变、失败后可继续编辑），开发者只读核对 11 个作业与本地记录逐项一致；含提示词场景 D 基准歧义说明与 `depth:1.0` 回显次要观察（未登记新条目）。[BUG-054](work-items/BUG-054.md) 三层证据链闭环、[DEV-033](work-items/DEV-033.md) G0～G5 完成；未测边界不变，未合入 main、未发布。本轮仅记录验收与核对，未连接 Creo、未改代码。

- 2026-10-17 [0.3.4 / Creo 9 反馈补录](validation/FEEDBACK-0.3.4-2026-10-17.md)：新增 [BUG-055](work-items/BUG-055.md)（恢复 apply 的 MCP 可空参数/stale 拒绝差异，P1 待核实）。null 转空串仅为根因线索，需真实协议与独立客户端对照；inspect 和 callback_status 补限定正例。token 时效、入队前回调提示、别名/分页和新工具 MCP 冒烟沿用原条目，种子/筋/装配约束/round 不重复建卡。保留当前 BUG-054/DEV-033 的开发实机成果及剩余 WorkBuddy 范围；本轮仅同步文档，不连接 Creo，不重开 BUG-001。

- 2026-10-17 下一轮建议优先推进 [DEV-033：切除材料变化核实、修复与验收](work-items/DEV-033.md)，聚焦新增 P1 BUG-054。先离线核对，满足卡死根因核对与会话可操作条件后再做当前版本最小复现、结果契约、修复和分层验收；BUG-054 保持待核实，FEAT-018/029 保持原验收状态。本轮仅建卡，目标版本未排期，不恢复 Toolkit 联调。

- 2026-10-17 [0.3.3 四份反馈去重补录](validation/FEEDBACK-0.3.3-2026-10-17.md)：新增待核实 [BUG-054](work-items/BUG-054.md)（拉伸切除零去料仍静默成功）及待规划 FEAT-034～037（弧方向/扫角、沉孔/沉头孔、零件特征删除/抑制/恢复、参数作用域）。装配直接矩阵输入补入 FEAT-012；组件身份/快照/选轴/图纸默认值、PATH 示例、签名 DLL 及 Creo 9 冒烟建议沿用已有条目。原件逐字节归档，均为外部 0.3.3 证据，当前 0.3.4 未复测；本轮只补文档，不连接 Creo。

- 2026-10-17 用户决定关闭BUG-001并将全部待合分支统一交付main，明确指定0.3.4。[DEV-032](work-items/DEV-032.md)发布候选已完成，两目录各297项、独立SDK构建/分发通过；实际主干/Release核对见[PR #9](https://github.com/wudahua/MCP_CREO_MechDog/pull/9)；BUG-001移入[关闭归档](BACKLOG_COMPLETED.md)，卡死根因和未完成实机范围保留，不视作全部验收通过。FEAT-018/FEAT-029继续验收中，本轮不恢复Toolkit联调。下面已注明日期的验证与提交记录保留当时阶段。

- 2026-10-17 BUG-001新增[卡死离线排查](validation/BUG-001-hang-offline-2026-10-17.md)：trail确认IPC初始化`-97`/Warning、客户端`-11`，Windows确认同一Creo12.4进程无响应关闭；底层诱因未定，不能认定SDK版本错误。当前快照无Creo进程，待确认会话可操作后再恢复联调；本轮没有Toolkit连接/注入，未关闭、合并或发布。

- 2026-10-17 已补齐 [BUG-001/FEAT-018受控恢复联合执行卡](work-items/BUG-001-FEAT-018-RECOVERY.md)，两项现进入验收中：正式恢复入口、保护和持久化登记已实现，284项单元及四动作部分实机通过；本轮随后Creo卡死，最终实机/WorkBuddy未完成，见[本次验证记录](validation/BUG-001-recovery-2026-10-17.md)。工作目录固定E盘；本机MCP只启用MCP_CREO_MechDog_dev，C盘旧服务退役。未关闭、合并或发布。

- 2026-10-16 [DEV-030 G0已完成](work-items/DEV-030.md)：[BUG-001现版本复现](validation/BUG-001-repro-2026-10-16.md)确认当时0.3.3模型协调阻断，保护层按设计生效但无正式恢复接口；有基线模型人工解锁后门禁循环，无基线模型可能静默采纳半成品，保存后未交付另列一类。2026-10-17恢复实现已提交并进入验收，复现原始记录保持不变，BUG-008锁释放/通道恢复关闭范围保持。

- [DEV-030分期](work-items/DEV-030.md)现为恢复实现验收中、FEAT-029开发分支已集成；剩余为卡死定位、完整验收和主干交付，之后处理底板/编辑闭环及履带基础/性能/阵列。[分支核对](validation/DEV-030-branch-sync-2026-10-17.md)确认建卡、反馈补录、G0复现及E盘同步提交均已包含在当前集成分支。新增[0.3.3构建/回调反馈](validation/FEEDBACK-0.3.3-BUILD.md)关联DEV-021/019/027及FEAT-029：外部三键环境编译正例、额外键兼容与日志展示待核对、目录/缓存/可复现性分别核实，DEV-019/021原完成范围保持。

- [DEV-029：0.3.3 主干交付](work-items/DEV-029.md)已完成：main@9ee923c 与 v0.3.3 指向一致，[Release](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.3.3)已公开为 Pre-release，四份附件从实际主干生成并下载核对 SHA256；主干 CI、两目录各 263 项与原生回归通过，最终交付见 [PR #8](https://github.com/wudahua/MCP_CREO_MechDog/pull/8)。原[候选记录](validation/RELEASE-0.3.3.md)保留当时阶段与未测范围。

- 2026-10-16 [DEV-028：Creo 9 编译与安装闭环](work-items/DEV-028.md) 已完成，BUG-033 与 DEV-019～022 统一移入[完成归档](BACKLOG_COMPLETED.md)：14 项新增定向回归、260 项完整单元/语言守卫、本机 SDK 构建、显式环境真实编译及桌面环境 Creo 12.4 七个原生作业通过，逐任务保存重载 true，见[本次证据](validation/DEV-028.md)。Creo 9 实机编译/运行时仍未验证；普通 Codex 宿主连接 -4 的限制单独记录。一个本地提交，不推送、不发布、不升版。 后续 [WorkBuddy 复核](validation/DEV-028-WorkBuddy-review-20261016.md)采纳部署和通用计划单孔/双孔通过；底板快捷入口参数受阻，仍未覆盖，序列化原因待核实，线索归 FEAT-008。
- FEAT-029已按2026-10-17用户指令集成到E盘codex/feat-029-integration：297项单元、SDK编译、载荷ABI及84工具stdio离线检查通过。见[本次集成](validation/FEAT-029-integration-2026-10-17.md)。BUG-001卡死未定位，集成环境实机/WorkBuddy待测，未合入main或发布；历史879aebe证据不改标为本轮通过。
- [P1 联合修复](work-items/P1-MODELING-REPAIR.md)：本环境已测分支已有 WorkBuddy 通过记录；查询预算、放样计划入口引用及恢复失败等功能边界按各项继续验收。BUG-022 已完成并归档，原环境反馈保留来源。
- 0.3.1 已合入历史 main@515d50b，未发布 v0.3.1；累计公开交付已由 DEV-025 / v0.3.2 完成。更新提醒仍有未测场景，Python 包迁移继续分批推进。
- P0 通道恢复 BUG-008 按本机 Creo 12.4 已验证范围完成并移入[完成事项归档](BACKLOG_COMPLETED.md)：246 项单元、同实现真实冷态自动归档/重建/单次启动，以及新 WorkBuddy retry/120 mm³ 建模/unknown 保护通过。WorkBuddy 冷态与异常环境、历史完整链仍未验证，分层边界见[关闭复核](validation/BUG-008-closure-2026-10-16.md)。BUG-009 已完成并归档；其他未确定版本的事项保持“未排期”。
- [0.3.1 实测补录](validation/WORKBUDDY-0.3.1.md)：新增 4 项待核实缺陷、4 项能力/体验建议，其余复用已有 ID；报告统计与输入适用性有待核实之处，本次未复现或修复。
- [2026-10-16 四份反馈补录](validation/FEEDBACK-2026-10-16.md)：41 个编号问题及构建绕过线索已去重映射；新增 BUG-034～BUG-047（14 项待核实）和 FEAT-029～FEAT-030（2 项待规划）。保留 Creo 9/10 与具体版本未明的不同来源；回调升级负担、拓扑/API 根因和 Release 状态按证据边界继续核实，本次仅同步文档。
- [2026-10-16 三份 0.3.2 反馈补录](validation/FEEDBACK-0.3.2.md)：A/B/C 三份报告已归档并去重映射。按用户决定把 BUG-038、BUG-042、BUG-043、BUG-044 转已完成并移入[归档](BACKLOG_COMPLETED.md)，标注"采信外部报告、本仓库无对应提交可核实、本机复现失败须重开"；新增 [DEV-027](work-items/DEV-027.md)（回调 DLL 非确定性构建）、[BUG-048](work-items/BUG-048.md)（含镜像特征抽壳失败）、[FEAT-031](work-items/FEAT-031.md)（装配交付打包导出）。Creo 9 与 Toolkit 9 纳入[兼容说明](COMPATIBILITY.md)等文档的支持/要求范围，建模运行时未在本机验收；本次仅同步文档，见 [DEV-026](work-items/DEV-026.md)。
- 2026-10-15 按用户要求取消整个项目的 Creo 10 独立验收门槛，见 [DEV-018](work-items/DEV-018.md)。DEV-002 第二批本机开发与 WorkBuddy 已测场景通过，本批完成；整体迁移继续推进。
- 2026-10-15 收到第三方用户 Creo 9 SDK（Toolkit 9）编译失败反馈，[报告已归档](validation/2026-10-15_CREO_0.3.0_旧版ToolkitSDK原生编译失败.md)，当时登记 BUG-033 与 DEV-019～022。2026-10-16 DEV-026 调整支持文档，DEV-028 现已完成编译探测和安装链实现；本机未验证 Creo 9 实机编译/运行时，后续反馈继续按来源补录。

</details>

<details>
<summary>历次反馈补录与来源映射</summary>

## 2026-10-17 0.3.4 恢复工具与 Creo 9 反馈补录

[原件、环境、方法与去重映射](validation/FEEDBACK-0.3.4-2026-10-17.md)及[SHA256 清单](validation/feedback-0.3.4-2026-10-17/manifest.json)已归档。新增 BUG-055；报告原列 P0，本台账先按 P1 待核实跟踪恢复工具调用差异，未取得全通道封锁或会话损坏证据。直接 Python 驱动作业不是 MCP apply 通过，标准 null 是否被转换及发生在哪层仍需核实。

FEAT-018 补 token 时效/重新 inspect 指引，FEAT-029 补状态查询正例与建模前摘要，FEAT-006/008 补 label/原生名及分页规则，DEV-006/007 补真实 MCP 工具层冒烟。种子生产版本/兼容元数据归 FEAT-030，筋/种子/装配约束/round 继续原 ID；未知 owner 的 busy 回退符合 BUG-009 现有边界，不自动重开。BUG-033 补限定孔正例，所有外部观察均保留缺少完整 job/model/保存重载证据的范围。

本轮未修改代码、配置、token、模型或版本，未执行报告中的升级/Python 绕行/恢复/并发测试，未连接 Toolkit。BUG-001 原关闭、FEAT-018/029 验收中及 BUG-054/DEV-033 当前进度保持，不因报告建议推断种子生产版本、跨环境失败根因或全部兼容性。

## 2026-10-17 0.3.4 Creo 10 构建与回调反馈补录

[原件、环境与去重映射](validation/FEEDBACK-0.3.4-CREO10-2026-10-17.md)及[SHA256 清单](validation/feedback-0.3.4-2026-10-17/manifest.json)已归档（11088 字节，与同日 Creo 9 报告同目录收录、manifest 合并为双来源，登记于 main `8ce644f` / v0.3.5 之后）。本轮不新建 ID：注册解耦正例与 payload 目录累积续报归 [DEV-027](work-items/DEV-027.md)，readiness 双义观察归 [FEAT-029](work-items/FEAT-029.md)，vcvars64_env 三键再报归 [DEV-030](work-items/DEV-030.md) 需求核对，Creo 10 三截面种子正例归 [BUG-034](work-items/BUG-034.md)/[FEAT-030](work-items/FEAT-030.md)。

报告在其 0.3.4 / Creo 10 环境实测：loader/payload 分层修复注册反复失效（含删除 loader.dll 破坏性对照）、三键配置编译成功、三截面混合建模通过（保存重载 true）、直接放样约 9 秒快速失败；反馈人无法在其 Creo 10 完成 GUI 注册安全确认，回调加载后端到端链路仍未验证。本轮已对 0.3.5 源码逐项核对报告三处事实（恰好三键、payload 无目录清理、loader/payload 分层），均一致；未执行报告建议的目录清理/current 指针/键集放宽，未重演删除测试或编译，未连接 Toolkit。报告环境（Creo 10、reg.exe 受限）观察不外推到本机 Creo 12.4 或其他环境。

## 2026-10-17 0.3.3 四份反馈去重补录

[原件、环境与去重映射](validation/FEEDBACK-0.3.3-2026-10-17.md)及[SHA256 清单](validation/feedback-0.3.3-2026-10-17/manifest.json)已补齐。新增 1 个缺陷候选、4 个能力条目；装配直接矩阵输入复用 FEAT-012，不重复建卡。FEAT-008/023 补组件内联身份、快照、实际选轴与 drawing_view 默认值；DEV-021 的 PATH 示例请求、FEAT-029 的签名 DLL 评估、DEV-006/007 的 Creo 9 冒烟切片沿用原 ID。

钣金、种子、筋、装配约束、round 参数、诊断/体量等重复反馈保持原归属和状态。BUG-033 的外部 Creo 9 编译正例与限定孔建模数值已补卡，未取得完整作业身份/重载链；不外推为本机或完整 Creo 9 运行时验收。所有来源均为 0.3.3，当前 0.3.4 未复测；本轮未改代码/版本、未执行来源操作或连接 Creo，BUG-001 关闭和 FEAT-018/029 验收中状态保持。

## 2026-10-16 0.3.3 构建与回调补录

[原件、来源边界、Q1～Q3及去重映射](validation/FEEDBACK-0.3.3-BUILD.md)已归档：三键显式环境在外部Creo10/reg.exe受限环境编译成功；额外SDK键拒绝关联DEV-021，成功warning/note与失败摘要须区分关联DEV-019，目录累积/重新注册负担关联DEV-027和FEAT-029。没有完整日志、环境转储及连续构建序列，根因与计数仍待核实。DEV-019/021历史完成状态不改，不新开重复ID；后续兼容/展示请求由DEV-030核对再明确实施范围。没有执行报告中的清目录、固定current、改缓存或/Brepro建议。

## 2026-10-16 履带案例与反馈映射

两份材料见[原件清单、逐节去重与输入差异](validation/TRACK-FEEDBACK-2026-10-16.md)；新建 BUG-049～053、FEAT-032～033、DEV-030～031，补齐 BUG-001、FEAT-006/008/018 等既有卡。报告中的清锁/重启、自动并集、预算公式和根因解释只作来源，不是本次操作指令；BUG-001对应阻断后续已在G0复现，其余问题不外推为已复现，不改已关闭 BUG-008 的结论。

## 2026-10-16 四份反馈问题映射

[来源、41项编号映射与证据边界](validation/FEEDBACK-2026-10-16.md)收录下载目录全部4份Markdown原件，保留SHA256、报告环境及job/model标识。新增BUG-034～BUG-047与FEAT-029～FEAT-030；回调就绪、会话/状态、查询体量、错误上下文、进度、回滚历史、四壁折弯释放与发布缺口复用已有ID。

报告中的根因、优先修复顺序和替代方案不自动成为实施结论；Q6启动路径未复测、回调重注册负担未实测、两份配电箱具体Creo版本未提供。Q3所述0.3.1 Release缺失按DEV-015待核对，当前远端未查询；Q4旧版本句在本次工作区已不存在，远端/反馈方部署是否更新无法确认。本次只补录，不执行报告中的注册、发布或本地重建步骤，不把旧实例失败覆盖本机已测正例，不改变兼容支持声明。

## 2026-10-16 三份 0.3.2 反馈问题映射

[来源、编号映射与证据边界](validation/FEEDBACK-0.3.2.md)收录下载目录全部 3 份 Markdown 原件，保留 SHA256、报告环境、作业与模型标识。报告 A 的 16 条回归编号、报告 B 的 9 项问题与 2 项已修复确认、报告 C 的 2 项问题及观察项均已落到固定 ID：新增 [DEV-027](work-items/DEV-027.md)、[BUG-048](work-items/BUG-048.md)、[FEAT-031](work-items/FEAT-031.md)；BUG-042、BUG-043、BUG-044（A 的 P1/P2/P4）与 BUG-038（B 的布尔类型实测）按用户决定转已完成并移入[归档](BACKLOG_COMPLETED.md)。

报告 B 的文件名与标题写"Creo10"而正文环境为 Creo 9.0.0.0，两者不一致已如实保留；报告 A 的"已修复"采信为外部结论，本仓库无对应提交可核实，本机复现失败须重开。A 未复测 P6～P10，S2/S6/S7 未复测或据同代码路径推断，不因同一报告其他项通过而外推。报告中的建议、作者提问与本机路径只作来源记录，不构成本轮执行指令，见 [DEV-026](work-items/DEV-026.md)；Creo 9/Toolkit 9 支持声明按[兼容说明](COMPATIBILITY.md)本次调整的口径执行。本次只补录，未执行报告中的注册、重编或建模步骤，未核对远端 Release。

## WorkBuddy 0.3.1 全量实测问题映射

[原始报告](validation/MCP_CREO_MechDog_0.3.1_全量实测问题报告.md)已原样归档，17 个问题、部署建议、修复复验及未测项的固定 ID 对照见[补录与证据边界](validation/WORKBUDDY-0.3.1.md)。新增 BUG-029～BUG-032、FEAT-025～FEAT-028，其余复用已有条目；新增项报告环境为 Windows x64 / Creo 12.4.0.0，其他环境收到具体反馈后再跟进。

“82/82 调用”与 `create_udf` 未调用等统计存在口径不一；直接 loft 仅验证缺回调失败路径，不能关闭 BUG-028 或重开 BUG-007。API/锁/草绘根因推断、种子降级方案均待核实。以上仅补录，未开展新建模测试；报告修复建议顺序不自动变为排期。

## WorkBuddy 0.3.0 全量实测问题映射

[原始报告](validation/MCP_CREO_MechDog_0.3.0_全量实测问题报告.md)与[证据摘要及覆盖限制](validation/WORKBUDDY-0.3.0.md)保留历史结论。报告编号与固定 ID 的[来源索引](BACKLOG_COMPLETED.md#workbuddy-030-报告编号)已归档；未完成事项按本表继续跟踪。报告含内部分析、历史证据复用和未测场景，不代表全工具、全分支或真实并发验收通过。

## 原问题清单映射

[原问题快照](待完善功能清单.md)与[未来建议快照](NEXT_STEPS_025.md)保留原日期和编号；固定 ID 对照见[历史来源索引](BACKLOG_COMPLETED.md#历史来源索引)。

</details>
