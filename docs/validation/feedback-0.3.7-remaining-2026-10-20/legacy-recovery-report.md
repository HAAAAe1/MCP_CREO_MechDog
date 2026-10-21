# 2026-10-18_CREO_0.3.7_恢复动作对旧模型永久失效与种子筋第七轮依旧

**测试日期**：2026-10-18（16:21 – 16:35，GMT+8）
**MCP 版本**：0.3.7（GitHub 最新，Pre-release；84 工具）。0.3.7 为纯文档版本，**功能等同 0.3.6**（本轮实际验收对象为 0.3.6 的功能交付）
**Creo 版本**：Creo Parametric 9.0.0.0（release_numeric=41）
**平台**：Windows 10，stdio
**对照基线**：2026-10-15（0.3.0）、10-16（0.3.2）、10-17（0.3.3）、10-17（0.3.4）、10-18 上午（0.3.5）五轮报告

---

## 一、本轮结论

| 项 | 结果 |
|---|---|
| **BUG-059**（上轮我报的 P1：refused 误标 unknown_outcome） | ✅ **已修**（新字段 `reason` / `failure_phase` / `recovery_pending_released` 落地；见第三节的两点保留） |
| **BUG-057** 诊断脚本（本版新交付） | ✅ **脚本可用且本机稳定复现 Errno 13 机制**（1000/1000），自我限定表述严谨 |
| `creo_reconcile_model` 成功路径 | ✅ 回归正常（`abandon_new` → abandoned，pending 清空） |
| **BUG-058**（上轮我报的通道 -11 / 无主窗口） | ⚠️ 本轮**未复现**（约 14 分钟连续建模稳定）；确认为间歇问题，已登记为开放项 |
| **新发现**：无进程身份的历史作业 → 恢复动作**永久不可用** | ❌ 见第四节（P1，本机实测） |
| 叶片种子 / 筋 | ❌ **第七轮依旧**（Creo 9） |
| loft 回调 / component_constraints | ❌ 行为未变（第 5/6 轮） |
| 切除守卫（BUG-054）、孔、参数、关系、工程图 PDF、种子校验 | ✅ 全部通过，数值精确 |

## 二、部署一致性核验

| 项 | 结果 |
|---|---|
| `creo_check_update` | `current_version: 0.3.7` = `latest_version`，`up_to_date` ✓ |
| `creo_capabilities.version` | `0.3.7`，`tool_count: 84` ✓ |
| 执行器是否需重建 | **不需要**：`native/*.cpp` 最新时间 10-17 21:29，`creo_worker.exe` 10-17 21:31，源码与二进制一致（0.3.6/0.3.7 无 C++ 改动）✓ |
| 种子库 | 9 枚可用，`validate_seed(two_smooth)` 哈希与清单一致 ✓ |
| 新增诊断字段 | `creo_session_status` 新增 `creo_process_snapshot`（进程 pid / 镜像路径 / 创建时间 / `matches` 标记）——对 BUG-058 定位有实质帮助 ✓ |

## 三、BUG-059 验收（上轮 P1）

代码路径已按发布说明实现：`_record_failure()` 以 `worker_started` 区分——未派发 → `failed` + `stage=reconciliation_refused` + `failure_phase=before_native`（持锁时）/ `channel_admission`（未持锁）；已派发 → `unknown_outcome` + `failure_phase=native_worker_started`，并新增 `recovery_pending_released`。

**本机实测**：
1. **成功路径回归** ✓：inspect → apply（省略 pending）→ `succeeded` / `reconciliation_committed`，模型 `abandoned`、`recovery_pending: null`。
2. **过期令牌** ✓：`Evidence token is missing or expired; inspect again`，**不创建作业**（工具层直接拒绝，无半开状态）。
3. **准入后被拒（尝试构造）**：向 `model.json` 注入一个无关字段后再 apply，**工具层先一步返回** `Stale evidence: registry, files, deployment or process identity changed`，作业未创建。

**两点保留（建议）**：
- **`before_native` 分支仍无法从外部验证**：客户端能触发的拒绝基本都被工具层证据绑定拦下，worker 侧的 `model_changed` / `session_selection_changed` 需要"准入成功后再变更"，实际不可达。这与发布说明"真实会话切换、原生恢复未在本轮测试"一致，但意味着**该分支至今只有隔离测试覆盖**。建议在 `MODEL_RECOVERY.md` 明确"如何人为触发 before_native 场景"（例如提供一个受控的测试开关），便于外部验收。
- 作业 compact 结果中，成功路径不带 `failure_phase`（合理），但**没有 `schema`/字段说明**，客户端难以判断"字段缺失"是"成功"还是"旧版本"。建议在工具描述里列出这些字段的含义与出现条件。

## 四、新发现：无进程身份的历史作业 → 四种恢复动作永久不可用（P1）

**复现**：对 `wb_fulltest_blade`（0.3.0 时代创建的 failed 模型）执行 `creo_reconcile_model` inspect：

```json
"owners": [{
  "job_id": "bf58899a193d4c68adc3a21fe370bde4",
  "runner": { "stopped": false, "reason": "No recorded process identity" },
  "worker": { "stopped": false, "reason": "Native owner identity is unavailable" },
  "stopped": false
}],
"actions": {
  "restore_baseline": { "available": false, "reason": "Previous runner/worker is active or cannot be proven stopped" },
  "accept_saved":     { "available": false, "reason": "Previous runner/worker is active or cannot be proven stopped" },
  "accept_live":      { "available": false, "reason": "Previous runner/worker is active or cannot be proven stopped" },
  "abandon_new":      { "available": false, "reason": "Previous runner/worker is active or cannot be proved stopped" }
}
```

**问题**：这些早期作业的 `job.json` 里没有记录 runner/worker 的 pid 与创建时间（进程身份），导致 `_owners()` 永远返回 `stopped: false`，从而**所有**恢复动作永久不可用。该模型既不能恢复、也不能放弃，只能由用户手工删除文件——而工具本身的策略是"不删除用户文件"。

**建议**（低成本、影响面明确）：
1. 对"标识缺失"与"进程确实存活"作区分：`stopped: false` 附带 `reason` 已有，但动作可用性判断把它们等同了。可增加一档判定：**无身份记录 + 作业创建时间早于当前 Windows 启动时间 + 无同名进程存活 → 视为 stopped（evidence: identity_absent_stale）**；
2. 或至少允许 `abandon_new` 在 `identity_absent` 时可用（放弃不需要证明"未在写"，只需保证不再引用）；
3. 若两者都不做，建议在 inspect 返回中给出明确的可操作指引（"该模型记录早于进程身份机制，需手动清理 `models/<id>/` 目录"），否则调用方会反复重试同一条死路。

## 五、BUG-057 诊断脚本验收（本版新交付）✅

`python tools/reproduce_toolkit_lock.py` 在本机（Windows 10 / Python 3.13.14 / AMD64）运行完成：

- `scope.filesystem_only: true`、`service_imported: false`、`toolkit_connected: false`——确实不触碰服务与 Toolkit；
- **`competition_open_error_observed: true`**：delete-pending 场景 **1000/1000** 稳定复现 `PermissionError` / `errno 13` / `ucrt_doserrno 5`，并附带原生 `CreateFileW` 对照（`winerror: 5`）；
- `temporary_directory_cleaned_after_all_handles_and_threads_closed: true`——无残留；
- `interpretation` 明确写"仅证明机制，不构成 BUG-057 根因结论"——**表述克制、可信**。

**评价**：这是我在这一系列版本里见到的**质量最高的交付物之一**：可复现、隔离、自解释，且不夸大结论。建议把这种"受控机制演示 + 明确免责"的模式推广到其他难以复现的问题（如 BUG-058）。

## 六、历史问题状态（第七轮）

| 问题 | 首次反馈 | 0.3.6/0.3.7 |
|---|---|---|
| 叶片种子 Creo 9 无法加载 | 0.3.0 | ❌ **仍 -16**（`ProMdlFiletypeLoad`） |
| 筋特征 Creo 9 失败 | 0.3.0 | ❌ **仍失败**（"Rib regeneration failed on the requested material side"） |
| loft 需人工注册回调 | 0.3.2 | ⚠️ 行为未变（`BLEND_CALLBACK_SETUP_REQUIRED`，信息完整） |
| component_constraints 位置不求解 | 0.3.2 | ❌ **仍不求解**（transform 保持 (-30,20,0)+30°，`underconstrained: false`） |
| round `radius`/`size` 参数名不一致 | 0.3.3 | ❌ 未修 |

补充：0.3.6 已把"外部 Creo 9 通道 -11、无主窗口进程"登记为 **BUG-058 开放**，把钣金增料/草图弧方向/曲面算子等能力缺口登记为 BUG-046/FEAT-034/FEAT-039——**反馈闭环是有效的**。但种子与筋仍无版本支持声明，`creo_validate_seed` 的返回依旧只有 `Hash matches the verified seed manifest`，**没有 `seed_build_version` 字段**（我 0.3.5 建议项），用户仍无法在建模前知道"这枚种子在 Creo 9 用不了"。

## 七、通过项与数值对账

| 项 | 对账 |
|---|---|
| 孔 Ø6×10（offset 80/50） | 体积 118711.947 → 118429.204，Δ = −282.743 = π×3²×10 ✓ |
| 参数 | `A37`=11 (type 52)、`A37_OK`=false (**type 53**，布尔类型保持正确) ✓ |
| 关系 | `A37_B` = 55 = 11×5 ✓ |
| 切除守卫（BUG-054 回归） | 零去料 → `failed` + `rollback: true` + revision 保持 6 + 体积保持 118429.204 ✓ |
| 工程图 PDF | 16,319 字节，导出成功 ✓ |
| 种子校验 | `two_smooth` 哈希匹配、`available: true` ✓ |
| 恢复成功路径 | `abandoned`，`recovery_pending: null` ✓ |
| 运行身份 | `creo_process_snapshot` 两个进程 `matches: true`（镜像路径与创建时间可核）✓ |

## 八、给作者的建议（第 7 轮，按优先级）

1. **【P1 新增】无进程身份的历史作业需要出口**（第四节）：区分"无法证明停止"与"记录早于身份机制"，或允许此类模型 `abandon_new`。当前是真正的死路。
2. **【P1】提供 `before_native` 分支的可触发路径**（第三节）：建议文档给出受控触发方法，或加一个仅测试用的开关，让外部能验证 BUG-059 的核心分支。
3. **种子库 Creo 9 适配（第七轮）**：`validate_seed`/`list_seeds` 增加 `seed_build_version`，`creo_new_airfoil_blade` 失败信息中明确"种子由 Creo 12.4 构建，当前 Creo 9 无法加载"。
4. **筋的 Creo 9 兼容（第七轮）**：同上，区分"版本不支持"与"轮廓/材料侧问题"。
5. **BUG-058 复现条件**（间歇）：本轮 14 分钟未复现，上轮 33 秒复现。建议记录"空闲时长 / 是否有并发请求 / Creo 是否有可见窗口"三元组，`creo_process_snapshot` 已经把最后一项做实了。
6. **component_constraints 位置重求解（第 4 轮）**；round 参数名统一。
7. 小项：`creo_capabilities` 单次返回 **104 KB**，建议支持 `detail=compact`（仅工具名与版本），否则部分客户端会触发负载上限。

## 九、总体评价

0.3.6/0.3.7 属于**收口型版本**：BUG-059 把我上轮报的语义矛盾修掉了，BUG-057 的隔离诊断脚本做得很专业，`creo_process_snapshot` 也为 BUG-058 提供了真实的定位抓手。台账把"待复现/待核实/待开发/剩余验收"重构分类、并把外部反馈逐条登记为 BUG/FEAT 编号，这个工程习惯值得肯定。

**最需要改变的是"死路"和"无声明"这两类体验**：一个模型一旦进入"无法证明停止"或"种子版本不匹配"的状态，用户在当前工具集内没有任何出口。前者建议给 `abandon_new` 开口，后者建议把版本约束前置到 `validate_seed`。这两项改动都不大，但能显著减少反复踩坑。

---

*留痕：本轮作业 request.json / native.log / job.json 保留于 `F:\WorkBuddy CREO Space\MCP_CREO_MechDog\jobs\`；诊断脚本原始输出已记录；前五轮报告见工作区同名 md。*
