# 2026-10-18_CREO_0.3.7_首次创建竞争致toolkit锁Errno13与诊断脚本现场数据

> 反馈对象：MCP_CREO_MechDog **0.3.7**（tag v0.3.7，commit f56a4cf；功能与 0.3.6 一致）
> 环境：Windows 10 x64 (19045) / Python 3.13.14 x64 / MSVC 19.44.35229 + Windows SDK 10.0.26100 / Creo Parametric **9.0.0.0** Toolkit SDK
> 结论先行：0.3.6/0.3.7 更新顺利（84 工具、Creo 9 SDK 编译通过、种子校验通过）。**BUG-057 有现场进展**：贵方随 0.3.6 附带的 `tools/reproduce_toolkit_lock.py` 在本机（0.3.5 报告的原始复现机）运行 200 轮 × 3 场景，数据把失败机制精确锁定在**锁文件"首次创建"竞争**——文件已存在时 200/200 干净 busy，文件不存在时 200/200 出现 `Errno 13`。单元测试相应有两个确定性失败，与该机制一一对应。文末附修复建议。

---

## 一、核心问题：Errno 13 只发生在锁文件"不存在→并发首建"场景（诊断数据已锁定）

### 1. 诊断脚本现场数据（`tools/reproduce_toolkit_lock.py --iterations 200`，本机为 0.3.5 报告原始复现机）

完整 JSON 报告见附件 `build/bug057_repro_20261018.json`，三场景汇总：

| 初始状态 | 迭代 | 结果 | Errno 13 次数 | doserrno |
| --- | --- | --- | --- | --- |
| **absent（文件不存在）** | 200 | 每轮均 `acquired + open_error` | **200/200** | 5（ACCESS_DENIED） |
| **empty（0 字节已存在）** | 200 | 每轮均 `acquired + lock_busy` | **0** | — |
| **one_byte（1 字节已存在）** | 200 | 每轮均 `acquired + lock_busy` | **0** | — |

对照控制组还确认了错误签名映射：共享冲突（exclusive sharing）→ `open` 阶段 `Errno 13, doserrno=32`；delete-pending → `open` 阶段 `Errno 13, doserrno=5`。absent 场景观测到的正是 **doserrno=5**。

### 2. 数据指向的机制结论

- 锁文件**已存在**时，`open("a+b")` + `msvcrt.locking` 的竞争行为完全正确：200/200 干净 `lock_busy`，无一次 open 错误——字节锁机制本身没有问题。
- 锁文件**不存在**时，两个线程同时 `open("a+b")` 触发 CREATE 竞争，败者稳定得到 `Errno 13`（doserrno=5），**而不是预期的"双方打开成功、字节锁分出 busy/acquired"**。这正是 0.3.5 报告中 `test_actual_competing_admissions_only_one_succeeds` 失败、以及可推测的生产路径（服务冷启动/临时目录首用瞬间）的触发条件。
- 这同时解释了"作者本机 10 轮未复现、外部机器稳定复现"：CREATE 竞争窗口的命中概率强依赖机器时序（线程调度/磁盘/安全软件），属**机器相关**而非代码路径必然；但一旦命中，`toolkit.lock` 后续打开会持续失败，即 BUG-056 早期观测的"通道静默失效"形态。

### 3. 单元测试的确定性失败（0.3.7 套件 356 个中 2 个，均同机制）

| 测试 | 结果 | 失败点 |
| --- | --- | --- |
| `test_actual_competing_admissions_only_one_succeeds`（0.3.5 已报） | ERROR，连续复现 | `bridge.py:291 lock.open("a+b")` → `PermissionError [Errno 13]` |
| `test_first_creation_concurrent_admission_keeps_lock_file`（0.3.6/0.3.7 新增） | FAIL，连续复现 | 期望 `["acquired","busy"]`，实际 `["acquired", PermissionError(13)]` |

第二个测试名恰为"**first creation** concurrent admission"——与诊断脚本 absent 场景完全同构，相互印证。该测试在贵方环境（`dev_check` 全绿）与本机（稳定失败）结果相反，建议将其标注为时序敏感并在 CI 策略上考虑：要么对 open 竞争做容忍（见下），要么把它按"CREATE 竞争窗口"专项管理。

### 4. 修复建议（数据支持，成本低）

1. **启动时预创建锁文件**：服务初始化（单线程期）先 `touch toolkit.lock`（如 0.3.7 诊断已证明：文件存在时 600/600 观测全部正确）。此后运行期不再有 CREATE 竞争窗口。与"锁文件常驻不删"是同一思路的两半，本次数据补齐了"预创建即可消除 Errno 13"的实证。
2. **open 短重试兜底**：`lock.open("a+b")` 对 `PermissionError` 做 3 次 × ~50ms 重试再放行异常，吸收残余竞争窗口（重启后临时目录重建、多客户端同时冷启动等场景）。
3. 若希望彻底与 CRT 打开语义解耦，可用 `CreateFileW` + `FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE` 打开（诊断脚本已内置 native_open_control 对照，本次数据中 winerror=32/5 的映射可直接复用）。

---

## 二、0.3.6/0.3.7 更新验证记录

| 步骤 | 结果 |
| --- | --- |
| 升级 | 工作树干净，`git checkout -B main origin/main`（v0.3.7, f56a4cf） |
| 版本/工具 | `version.py` = 0.3.7；84 工具（0.3.6 无原生改动，worker 缓存复用） |
| 管线 | 依赖（无变化）→ editable 包 → 种子库（指纹链同步后校验通过）→ `bridge.py build` 全绿 |
| 冒烟 | `creo_check_environment` 全绿（Creo 9.0.0.0 SDK + vcvars64_env） |
| 单元测试 | 356 中 354 通过；2 失败均为上文同一机制 |
| BUG-056 | 注意到已按 nmsd 根因关闭（遗留进程清理后 38 次探测建模零掉线）——与本机 toolkit.lock 竞争问题相互独立，两边都闭合了拼图 |

## 三、0.3.6 行为变化提醒（客户端侧）

`creo_reconcile_model` apply 在**原生派发前**失败（会话切换/证据过期/输入校验）时，终态从 `unknown_outcome` 改为确定性 `failed`（`reason: reconciliation_refused`、`failure_phase: before_native`、`recovery_pending_released`），可直接重新 inspect→apply。此前把该分支当 unknown 等待的客户端逻辑应更新；WorkBuddy 侧注意 compact 结果新增 `reason`/`failure_phase` 字段。

## 四、遗留未验证

- Creo 9 运行时建模仍维持"未验收"口径（本次仅编译与单元层）。
- 上述 Errno 13 修复落地后，本机可立即复跑两个失败测试 + 600 轮诊断脚本做关闭验证，随时可提供。
