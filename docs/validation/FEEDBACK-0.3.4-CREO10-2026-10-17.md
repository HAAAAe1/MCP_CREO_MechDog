# 2026-10-17：0.3.4 Creo 10 构建与回调反馈补录

按用户要求对下载目录第二份 0.3.4 报告去重补录。本报告与同日 [Creo 9 恢复工具报告](FEEDBACK-0.3.4-2026-10-17.md)来自不同反馈环境，主题不重叠；本次只登记文档与既有条目，不执行报告建议的目录清理、键集放宽、注册或建模操作，不连接 Toolkit。

## 原件与身份

[原始报告](feedback-0.3.4-2026-10-17/creo10-payload-vcvars-report.md)逐字节归档：11088 字节，SHA256 `de1209234c160d67a305f44536356c02bbc0812265fdbe6923bacdcae7fde2d1`。完整源路径、原文件名及登记基线见[清单](feedback-0.3.4-2026-10-17/manifest.json)，原件设置 `-text`，同目录既有验证文件保持不变。

| 项目 | 报告提供的内容与边界 |
| --- | --- |
| 测试环境 | Windows 10 x64 / Creo Parametric 10.0.0.0 / VS2022 BuildTools 14.44.35207 / Windows SDK 10.0.26100.0 / Python 3.13；本机 `reg.exe` 被安全策略拦截，编译走 `vcvars64_env` 配置化路径 |
| 受测版本 | 0.3.4（2026-10-17 14:29 发布，自 0.3.3 升级）；源码 ZIP SHA256 `e64c4246…33fb5f`、种子 ZIP `e7e59429…901d59` 与发布说明一致，509 文件覆盖复核差异为 0 |
| 当前登记基线 | main `8ce644f` / v0.3.5（报告登记晚于 0.3.5 交付）；本轮源码核对在 0.3.5 上进行，报告观察值均属其 0.3.4 环境 |
| 方法边界 | 报告混合本机升级、破坏性文件删除测试、源码分析及 `bridge.py build`；无 MCP job/model 标识，本轮未重演其本机操作 |

## 正向证据：注册失效修复获外部 Creo 10 实证（归 DEV-027/FEAT-029）

报告确认 0.3.4 的 loader/payload 分层（固定注册入口 `build\blend_callback_protk.dat` 指向 `blend_loader/<世代哈希>/loader.dll`，loader 指纹不含 payload）实质修复了其 2026-10-16 报告的"重编译导致注册反复失效"：删除 `build\creo_blend_loader.dll` 后重跑构建，产物 SHA256 与基线一致、`protk.dat` 的 `exec_file` 未变、未新增世代目录；payload 源码变化只新增 payload 目录、不影响注册。这是 [DEV-027](../work-items/DEV-027.md) 核心问题（注册路径与非确定性构建解耦）的首个外部 Creo 10 实测正例，此前仅有本机证据。

该证据只覆盖"注册路径解耦"子范围：同源码重编译的二进制可复现性、外部副本改动/登记不一致分支及目录安全回收仍待各自核实，不据此整体关闭 DEV-027 或替代 [FEAT-029](../work-items/FEAT-029.md) 的生命周期验收。

## 去重映射

| 报告主题 | 归属 | 本次补充与未测边界 |
| --- | --- | --- |
| payload sha 目录持续累积（6 个 / 17 MB，跨两日）、无清理、无"当前"标记 | [DEV-027](../work-items/DEV-027.md) | 注册已解耦后严重度下降，属本卡既有"过期目录清理/固定 current"候选范围的新数据；报告建议（保留最近 N 个、`current.json` 指针、仅清理自有且不在用副本）为候选细化，未选型不实施。本轮核对 0.3.5 源码 `blend_callback.py` 仍只有临时文件 `unlink`，无目录清理逻辑，与报告描述一致 |
| `vcvars64_env` 恰好三键限制未改、报错无裁剪指引 | DEV-021（历史范围）、后续核对归 [DEV-030](../work-items/DEV-030.md) | 报告附 0.3.4 代码片段；本轮核对 0.3.5 `build_support.py` 仍为 `set(value) != set(COMPILER_ENV_KEYS)` 即抛错，报告观察与现行源码一致。放宽为"必须含三键+其余忽略/透传"或改进报错文案沿用 DEV-030 需求核对，本轮不改行为；三键配置在其受限环境编译成功沿用 0.3.3 补录的外部正例 |
| `creo_callback_status` 的 `readiness` 在"从未加载"与"已注册不可查询"两种情形同为 `unknown`，仅 `reason` 可区分 | [FEAT-029](../work-items/FEAT-029.md) | 建议拆分 `not_loaded`/`unknown` 枚举或增加 `action_required` 布尔。本卡范围第 2 点本就要求区分就绪/未加载/版本不匹配/无法确认，该观察说明已交付实现的枚举语义未完全达到自身验收范围，补入本卡；报告确认探测确定性（会话就绪后连查 3 次稳定）及 prepared/ready 分离为正例 |
| 三截面自动匹配混合在 Creo 10 成功（体积 22159.999999999996、保存重载 true） | [BUG-034](../work-items/BUG-034.md)、[FEAT-030](../work-items/FEAT-030.md) | 与 Creo 9 加载 -16 形成环境对照，支持"不由哈希或单一环境推断全部种子不可加载"的既有口径；无 job/model 标识，不外推为完整 Creo 10 运行时验收 |
| 直接放样约 9 秒快速失败 `BLEND_CALLBACK_SETUP_REQUIRED`（0.3.3 为 12 秒） | [FEAT-029](../work-items/FEAT-029.md) | 缺回调就绪路径快速拒绝且错误信息升级为完整状态对象，属本卡正例；不是直接放样建模成功，回调加载后端到端链路仍未验证（反馈人无法在其 Creo 10 完成 GUI 注册安全确认） |
| 84 工具、`creo_callback_status`/`creo_reconcile_model` 新工具在位、产物结构变化（loader 3,272,704 B / payload 351,744 B） | 发布元数据核对 | 与 0.3.4 交付记录一致，本轮不重复验收 |

## 作者提问的处理口径

| 提问 | 本次登记与待办 |
| --- | --- |
| payload 目录能否自动清理（保留最近 N 个）或加"当前"指针 | 沿用 DEV-027 候选方案，选型须保护在用/注册引用/回退副本，本轮未实施、未清理其本机目录 |
| `vcvars64_env` 是否放宽或改进报错 | 归 DEV-030 需求核对；比较严格报错改进、忽略与安全透传的兼容边界后再登记实施范围 |
| `readiness` 能否区分 `not_loaded`/`unknown` 或加 `action_required` | 补入 FEAT-029，随生命周期/预检验收一并核对，不单独建卡 |
| 报告留存 `protk.dat`/`blend_callback_setup.json`/`blend_loader_build.json` 样本可提供 | 登记为可索取材料，本轮未索取；需要 DEV-027 选型证据时再向反馈方获取 |

本轮未修改构建/回调/预检实现、未清理或生成任何 `blend_callback`/`blend_loader` 目录、未执行报告中的删除测试或编译。0.3.5 交付状态、BUG-056 待核实及 FEAT-018/029 验收中保持；报告环境（Creo 10、reg.exe 受限）观察不外推到本机 Creo 12.4 或其他环境。
