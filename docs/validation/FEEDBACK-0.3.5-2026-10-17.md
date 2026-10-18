# 2026-10-17_CREO_0.3.5_toolkit_lock并发窗口致恢复登记测试稳定失败

> 反馈对象：MCP_CREO_MechDog **0.3.5**（tag v0.3.5，commit 8ce644f）
> 环境：Windows 10 x64 (19045) / Python 3.13.14 x64 / MSVC 19.44.35229 + Windows SDK 10.0.26100 / Creo Parametric **9.0.0.0** Toolkit SDK
> 结论先行：0.3.5 在 Creo 9 SDK 上编译与安装全部通过（84 工具、探针宏正确、无本地补丁）。**发现 1 个确定性测试失败**：`test_actual_competing_admissions_only_one_succeeds` 在本机连续 3 次稳定报 `PermissionError [Errno 13]`，指向 `toolkit_lock` 的 Windows 文件句柄竞争窗口，疑似 BUG-001/BUG-056 通道稳定性问题的同源机制，建议纳入排查。

---

## 一、核心问题：toolkit_lock 的 `a+b` 常开句柄与 unlink 收尾存在竞争窗口（Windows）

### 1. 现象（可稳定复现）

`tools\test_unit.py`（307 个测试）中仅 1 个失败，连续 3 次运行稳定复现（非偶发抖动）：

```text
ERROR: test_actual_competing_admissions_only_one_succeeds
  (unit.test_reconciliation.Reconciliation)
File "src\creo_mechdog\reconciliation.py", line 577, in apply
    with bridge.toolkit_lock(operation="submit_reconciliation", model_id=model_id):
File "bridge.py", line 291, in toolkit_lock
    with lock.open("a+b") as f:
PermissionError: [Errno 13] Permission denied:
  'C:\\Users\\ADMINI~1\\AppData\\Local\\Temp\\tmpXXXX\\toolkit.lock'
```

复现命令：`.\.venv\Scripts\python.exe -m unittest tests.unit.test_reconciliation`（连续 3 次，全部同位置失败；其余 20 个测试通过）。该测试为 BUG-001 恢复功能引入（5628a33，2026-10-17），用双线程 Barrier 制造真实的 `rec.apply` 并发准入竞争。

### 2. 根因分析（机制推测，供核实）

`toolkit_lock`（bridge.py:282-323）的收尾顺序是：

```python
finally:
    try:
        # Remove before unlock: deleting afterwards could erase the next owner.
        (ROOT / "toolkit-owner.lock").unlink(missing_ok=True)
    finally:
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
```

竞争序列推测：

1. 线程 A 持锁，退出 `finally`，`unlink(toolkit-owner.lock)` 执行，**随后字节锁尚未释放的微小窗口内**让出 GIL；
2. 线程 B（另一竞争者）此刻刚进入 `toolkit_lock`，`lock.open("a+b")` 打开 `toolkit.lock`——注意 `toolkit.lock` 本身**从不删除**，`a+b` 打开一个未被删除的文件不应报 Errno 13；
3. 因此 Errno 13 更可能出现在**共享冲突**上：Windows 的 `io.open`（CreateFile）默认无 `FILE_SHARE_DELETE`。若 B 打开的瞬间，A 或测试夹具（`TemporaryDirectory` 清理、`patch` 退出、或 `write_json` 的原子替换对 `toolkit.lock` 同目录的临时文件操作）正持有/处理该文件的删除语义，`CreateFile` 会因 sharing violation → 映射为 `Errno 13`。

关键疑点：`toolkit.lock` 从不 unlink，但测试的 `TemporaryDirectory` 退出会递归删除整个临时目录——若某次 `toolkit_lock` 迭代与其他夹具清理交错（例如前一个测试的锁文件句柄尚在 delete-pending 状态），新测试在**同一路径名**上 `open("a+b")` 就会命中 delete-pending 窗口。这与 BUG-056 描述的"WorkBuddy 期间通道在验证后约 37~41 秒失效，根因待核实"在机制上同源：**都是 Windows delete-pending / sharing violation 作用于通道锁文件**。

### 3. 对 BUG-056 的提示价值

BUG-056 记录"Toolkit 通道静默掉线（约 37-41 秒后），根因待核实、无会话观测"。本机现象提供了一个具体可疑机制：如果任何路径（owner 文件 unlink、临时目录清理、杀进程后的句柄回收）让 `toolkit.lock` 进入 delete-pending，后续所有 `lock.open("a+b")` 将持续 PermissionError，表现即"通道静默失效、无法重连"。建议 BUG-056 排查时优先核查锁文件是否曾进入 delete-pending 状态（可查 NTFS `$I30` 或用 handle.exe 抓现场）。

### 4. 修复方向建议（供参考）

1. **锁文件不删除、常驻**：`toolkit.lock` 改为首次创建后永久存在的锁对象（内容写创建时间即可），彻底消除 delete-pending 可能；owner 信息文件照旧 unlink。当前代码对 `toolkit.lock` 已经不删，需排查是否存在其他路径（如清理逻辑、用户手动、杀进程后回收）触发删除。
2. **打开重试**：`lock.open("a+b")` 外层加短重试（如 3 次 × 50ms，`PermissionError` 时 `time.sleep` 后重开），把瞬时 sharing violation 吸收掉；重试预算与现有 `ToolkitBusy` 语义不冲突（busy 是"持锁者存在"，Errno 13 是"打开失败"，二者应分开报错）。
3. **跨进程句柄属性**：若将来用 ctypes 打开，可加 `FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE`（与 BUG-002 中登记文件读句柄的修法同源，`tests`/`bridge` 已有先例）。

---

## 二、0.3.5 更新过程记录（除上述外全部顺利）

| 步骤 | 结果 |
| --- | --- |
| 升级方式 | 本地工作树（0.3.4 发布包内容 + 本机备注）已先完整快照到本地分支 `backup/pre-0.3.5-worktree`，再 `git checkout -B main origin/main` |
| 版本 | `version.py` = 0.3.5；`creo_check_environment` 全绿；**84 个工具**（0.3.3 为 82） |
| 原生构建 | `bridge.py build` 在 Creo 9 SDK 上一次通过；`constants.inc` 探针宏 0 个（BUG-033 修复行为正确） |
| 种子库 | 9 个种子 SHA256 校验通过 |
| 单元测试 | **307 个中 306 通过，1 错误**（即上文核心问题；该测试为 0.3.4/0.3.5 期间 BUG-001 恢复功能新增） |
| 客户端 | command/args 未变，mcp.json 无需修改 |

## 三、0.3.4→0.3.5 重点变化提醒（用户可见行为）

1. **切除守卫（BUG-054/DEV-033）**：实体 cut 现在核对实际去料体积，**零去料会报错并回滚**（过去可能静默成功）；有效切除返回 `material_removed_mm3`。旧工作流中"碰巧没切到"的切除计划会开始报错，属预期行为收紧。
2. **恢复契约（BUG-055/DEV-034）**：`expected_pending_job_id` 接受 null/省略；**空字符串会被拒绝**（WorkBuddy 客户端曾观察到 null 被序列化为空串的限制——在 WorkBuddy 里调用恢复时建议直接省略该字段）。
3. **BUG-056 未修复**：通道约 37~41 秒静默掉线的根因仍开放；本文核心问题的机制推测可作为其排查线索。

## 四、遗留未验证

- Creo 9 运行时建模仍未验收（本次仅更新与编译）；切除守卫、恢复 MCP 的实机行为需在 Creo 会话中另行验收。
- 本报告的 Errno 13 根因为机制推测，未能附 handle.exe/ProcMon 现场；如需，可在复现环境补抓。
