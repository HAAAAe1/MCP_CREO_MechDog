# 2026-10-17_CREO_0.3.4_恢复工具MCP层null失效与种子筋放样第五轮依旧

**测试日期**：2026-10-17（16:00 – 16:55，GMT+8）
**MCP 版本**：0.3.4（GitHub 最新，Pre-release；84 工具，新增 `creo_reconcile_model` / `creo_callback_status`）
**Creo 版本**：Creo Parametric 9.0.0.0（本机唯一安装，release_numeric=41）
**测试平台**：Windows 10，stdio，Toolkit 连接已验证
**对照基线**：本人 2026-10-15（0.3.0）、2026-10-16（0.3.2）、2026-10-17（0.3.3）三轮报告

> 说明：本次**由我代执行了 0.3.4 的升级**（本机原为 0.3.3）。升级过程与校验记录见第一节，供作者核对分发链路。

---

## 一、升级与部署核验（代执行）

| 步骤 | 结果 |
|---|---|
| `creo_check_update` | 本机原运行 **0.3.3**，GitHub 最新 **0.3.4**（`update_available`）——即用户所说"更新了"实际指远端发布，本机尚未安装 |
| 源码 ZIP | SHA256 `e64c4246…33fb5f` 与发布说明**一致** ✓ |
| 种子库 ZIP | 首次下载 **不完整**（454,656 字节 / 哈希不符）；重下后 493,394 字节、`e7e59429…901d59` **一致** ✓ |
| 备份 | 0.3.3 全量备份至工作区 `.backup_0.3.3_20261017/`（56 MB，含 config/执行器/源码，可回退） |
| 源码覆盖 | version.py = 0.3.4，保留 config.json / models / jobs / build 回调副本 ✓ |
| 种子库同步 | **9 个种子 PRT 逐文件 SHA256 与 0.3.3 完全相同**（0 变更） |
| 依赖 | requirements / lock / pyproject 与上版**无差异** |
| 执行器重建 | `setup.ps1 -Python <venv> -CreoRoot D:\CREO\Creo 9.0.0.0` 成功（Creo 9 SDK + 本机 vcvars），`creo_worker.exe` 8.86 MB ✓ |
| 运行身份 | `creo_callback_status.service.source_fingerprints_at_startup.version.py` = 实际文件 SHA256，`source_changed_since_startup: false` ✓（**新机制好用**） |

## 二、新功能验收（0.3.4 核心）

### ✅ `creo_callback_status`：完全满足上轮建议，实现质量高

上轮（0.3.2）我建议"在 session_status 暴露 blend_callback 状态"，本版不仅实现，还超出预期：

- 一次性返回 `readiness` / `registration_status` / `artifact_status` / `next_action` / `reason`；
- 完整身份：`dll_sha256`、`loader_sha256`、`loader_fingerprint`、`protocol: 3`（旧版为 2）、`contract: blend-selection-v3-ordered-curves-mm`；
- 明确区分 **prepared（工件已部署）** 与 **ready（运行时已加载）**，并说明"GUI 注册不可查询"这一根本限制；
- 给出持久注册配置路径与迁移提示（"Legacy protocol-2 registrations require migration"）；
- 附带服务侧源码指纹清单，可用于核对实际运行身份。

本机实测：`readiness: unknown` / `artifact_status: prepared` / `next_action: start_or_register_application_manually`——与真实情况一致（本机从未注册回调）。**这是本版最有价值的改进。**

### ⚠️ `creo_reconcile_model`：inspect 优秀，apply 在 MCP 协议层有阻塞性缺陷

**inspect 模式（✅ 优秀）**：对历史 failed 模型（`wb_reg_pat`，0.3.2 断言失败遗留）返回：

- 正确识别 `status: failed` / `revision: 0` / `baseline: null`（无基线新件）；
- 追溯原作业 `original_job_id` 并核对 runner/worker 存活（记录 pid vs 实际 pid，均 `stopped: true`）；
- 四种动作的可用性与不可用原因逐一给出（仅 `abandon_new` 可用）；
- `evidence_token` + 600 秒有效期 + `automatic_replay_allowed: false`。

**apply 模式（❌ 存在 bug）**：

| 调用方式 | 参数 | 结果 |
|---|---|---|
| **MCP 工具调用** | `expected_revision=0, expected_pending_job_id=null` | ❌ `Stale expected_revision or expected_pending_job_id` |
| **本地 Python 直连** | 同上 | ✅ 成功（`status: queued` → 手动驱动到 `succeeded`，模型变为 `abandoned`，历史保留） |

**根因（已定位到代码级）**：MCP 协议层把 JSON 的 `null` 传成**空字符串 `""`**，于是 `reconciliation._validate_evidence()` 中：

```python
if model["revision"] != revision or model.get("pending_job") != pending:
    raise ValueError("Stale expected_revision or expected_pending_job_id")
```

`None != ""` 恒为 True → 必然报 stale。本地复现对照：

```
pending=None  → 通过校验（继续后续 owner 检查）
pending=''    → Stale expected_revision or expected_pending_job_id   ← 与 MCP 调用完全一致的错误
```

**影响面（严重）**：`expected_pending_job_id: null` 正是工具文档描述的标准用法（"pending_job (null when absent)"），而**绝大多数待恢复模型的 pending_job 都是 null**。这意味着：**本版最重要的新功能 `creo_reconcile_model` 的 apply 路径，经 MCP 调用对最常见场景完全不可用**，只有绕过 MCP 直接调 Python 才能成功。

**建议修法（任选其一，成本都很低）**：
1. 服务端归一化：`expected_pending_job_id = expected_pending_job_id or None`（在 `reconcile()` 入口一行）；
2. `_validate_evidence` 比较前统一：`pending = pending or None`；
3. 若确认是 FastMCP/客户端序列化问题，也可在 schema 层把该字段声明为 `str | None` 并显式接受 `""` 视作 None。

建议同时为 `creo_reconcile_model` 补一个"MCP 工具层"的端到端测试（当前作者自述"本版不新增 Toolkit 连接、原生建模、故障注入或 WorkBuddy 复测"——本 bug 恰好只会在真实 MCP 调用路径暴露，本地单元测试无法发现）。

## 三、历史问题状态（第五轮）

| 问题 | 首次反馈 | 0.3.2 | 0.3.3 | **0.3.4** |
|---|---|---|---|---|
| 叶片种子 Creo 9 无法加载 | 0.3.0 | ❌ 未修 | ❌ 未修 | ❌ **仍 -16**（种子 PRT 哈希与 0.3.2/0.3.3 完全一致） |
| 筋特征 Creo 9 失败 | 0.3.0 | ❌ 未修 | ❌ 未修 | ❌ **仍失败**（同错误 "Rib regeneration failed on the requested material side"） |
| loft 需人工注册启动回调 | 0.3.2 | ❌ 未修 | ❌ 未修 | ⚠️ **行为未变**，但错误信息升级为完整状态对象（含 registry_file / protocol 3 / next_action），可操作性明显提升 |
| component_constraints 位置不求解 | 0.3.2 | ❌ 未修 | ❌ 未修 | ❌ **仍不求解**（transform 保持旧固定位 (-30,20,0)+30°，`underconstrained: false` 与实际矛盾） |
| round 参数名不一致（`radius` vs `size`） | 0.3.3 | — | 报告项 | ❌ **未修**（`RoundOp.size` 与独立工具 `radius` 仍两套） |

**说明**：种子与筋连续五轮未修，与发布说明一致（0.3.4 明确"九个种子原生 PRT 及其几何身份保持不变"、未涉及筋；且"Creo9/Toolkit9 实机编译与运行时未验收"）。本报告再次确认：**Creo 9 环境下这两项功能不可用，需要有明确的版本支持声明或修复计划。**

## 四、其他观察（本轮新增）

1. **`creo_dump_feature_tree` 的 feature 参数只接受别名 label，不接受原生特征名**。传原生名 `"H34"` 报 `Unknown feature label: H34`，传创建时 label `"h34"` 成功。错误信息未提示"请使用创建时的 label 或别名"，建议在错误中列出可用别名或说明匹配规则。
2. **`creo_list_models` 首次实际触发分页**（`complete: false` + `next_cursor`，本机 20+ 模型超过 32 KiB 预算）。分页机制工作正常；建议在返回中始终带 `complete` 字段（已在做）并在文档强调"第一页不等于全量"。
3. **`toolkit_busy` 结构化诊断**：并发调用时返回 `owner_determined: false` + `retry_guidance`（"未接受请求，1 秒后重试"）。合理；若能填出具体 `blocking_job_id` 会更好（本例 dump 任务正在跑，但未能定位）。
4. **`creo_reconcile_model` inspect 的 token 每 10 分钟过期**，apply 需在窗口内完成——实际使用中"inspect → 人工决策 → apply"很容易超过 10 分钟，建议延长或允许 apply 时自动重校验。

## 五、本环境通过项与数值对账

| 项 | 对账 |
|---|---|
| 孔（Ø6×10，offset 70/50） | 体积 Δ = −282.74 = π×3²×10 ✓（BUG-033 修复在 0.3.4 继续有效） |
| 参数（布尔/实数/字符串） | `ACC34_OK` type 53 = False ✓；`ACC34_NAME` type 51 ✓ |
| 关系 | `ACC34_B` = 42 = 7×6 ✓ |
| 布尔并集 | 2 bodies → 1，体积守恒 242575.710 → 242575.708 ✓ |
| 翼型截面 | NACA 0012 生成成功 ✓ |
| 工程图 PDF 导出 | 16,327 字节，有效 PDF ✓ |
| 特征树导出 | `feature_544.xml` 生成 ✓（别名 h34） |
| UDF inspect | T / DM / REF_CSYS 读取成功 ✓ |
| 种子库 | 9 个 available，哈希与清单一致 ✓ |
| 源码身份核验 | `version.py` 指纹 = 实际文件 ✓ |

## 六、给作者的建议（第 5 轮，按优先级）

1. **【新增 P0】修复 `creo_reconcile_model` apply 的 null→"" 误判**（一行归一化即可）。这是本版唯一新功能的阻塞性缺陷，且只在真实 MCP 调用路径暴露——建议补 MCP 端到端测试。
2. **种子库版本适配**（第五轮）：无论是否修复，请在 README / COMPATIBILITY 中明确写"种子库由 Creo 12.4 构建，Creo 9/10 无法加载 `creo_new_airfoil_blade`"，并在 `creo_list_seeds`/`validate_seed` 中标注 `seed_build_version`，让调用方在建模前就知道不可用。
3. **筋的 Creo 9 兼容性**（第五轮）：若短期无法修复，请把 `creo_rib` 标注为"仅 Creo 12.4 验证"，并在失败信息中附带"当前 Creo 版本未验证"的判断（而非让用户以为是轮廓问题）。
4. **回调状态在建模前主动提示**：`creo_callback_status` 已就绪，建议 `creo_loft` / `creo_new_airfoil_blade` 在**入队前**就返回该状态摘要（而非执行到原生阶段再失败），可显著改善"先等 30 秒再报错"的体验。
5. **component_constraints 触发重求解**（第三轮）。
6. 小项：统一 round 参数名、`dump_feature_tree` 错误提示可用别名、延长 reconcile token 有效期。

## 七、总体评价

0.3.4 的工程方向是对的：**BUG-001 恢复机制 + 回调生命周期**两大块正是自动化场景最痛的环节，`creo_callback_status` 的实现质量很高（身份、协议、prepared/ready 分离、迁移提示都考虑到了），`creo_reconcile_model` 的 inspect 与证据链设计也相当严谨。

但有两个问题削弱了本版价值：

1. **`creo_reconcile_model` 的 apply 在 MCP 调用路径上因 null 处理失效**——最核心的新能力无法通过 MCP 使用；
2. **作者自述本版未做任何实机建模/连接复测**，而版本边界中"Creo9/Toolkit9 未验收"意味着本机（Creo 9）环境的所有历史问题（种子、筋）都无法通过本版改善。

**核心建议**：在发布前增加一条"MCP 工具层烟雾测试"（真实经 FastMCP 调用各新工具一次），即可拦住本次这类只在协议层出现的缺陷；同时把 Creo 9 从"已纳入支持范围但未验收"改为可核验的冒烟矩阵（种子加载、筋、loft 状态查询三项）。

---

*测试留痕：本轮作业 request.json / native.log / job.json 保留于 `F:\WorkBuddy CREO Space\MCP_CREO_MechDog\jobs\`；0.3.3 备份于工作区 `.backup_0.3.3_20261017/`；前三轮报告见工作区同名 md。*
