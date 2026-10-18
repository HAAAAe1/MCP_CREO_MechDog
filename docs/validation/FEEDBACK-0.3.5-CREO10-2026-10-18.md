# CREO 10.0.0.0 · MCP 0.3.5：vcvars64_env 键集第三次未修 + BUG-056 通道静默失效阻塞实机验证

> 反馈人：终端用户（非项目作者）
> 记录日期：2026-10-18
> 实测版本：**0.3.5**（2026-10-17 20:57 发布，`cut guards and recovery MCP contract fixes`），从 0.3.4 升级
> 环境：Windows 10 x64 / **Creo Parametric 10.0.0.0** / VS2022 BuildTools 14.44.35207 / Windows SDK 10.0.26100.0 / Python 3.13
> ⚠️ **本轮验证范围声明**：按本机用户约束（`AGENTS.md`：BUG-001 关闭但卡死根因未定，**继续停止新的 Toolkit 连接/故障注入**），
> 本轮**未发起任何 Creo 连接、未做原生建模回测**。以下结论仅来自源码包校验、编译、文件层面与静态检查，
> 所有需要实机的项目**一律记为未验证**，不作通过结论。
> 仓库：https://github.com/wudahua/MCP_CREO_MechDog

---

## 0. 摘要

| 项 | 0.3.5 状态 |
| --- | --- |
| 升级本身（覆盖/安装/编译） | ✅ 全部成功，84 工具 / 9 种子 |
| **升级是否影响回调注册** | ✅ **完全不受影响**（本轮最强证据，见 §1.2） |
| BUG-054 cut 零去料守卫 | ✅ 实现确认（读码核对，未实机） |
| **`vcvars64_env` 只接受恰好三键** | ❌ **第三次未修**（0.3.4 报告过，代码与报错文案均未变） |
| **BUG-056 通道约 37–41 秒静默失效** | ⚠️ **发布说明自认未修**，且它正是本机无法继续实机验证的直接原因 |
| `build/blend_callback/` payload 目录累积 | 🟡 本轮未新增（payload 未变），但**清理机制仍不存在** |

---

## 1. ✅ 升级与验证

### 1.1 升级执行

| 项 | 结果 |
| --- | --- |
| 源码包 sha256 | `f8d5e7102d2e6ce7f1f0ca8d7de29080ef01f9e41b369310a2e270e1abece00a` ✅ 附件与发布说明双一致 |
| 种子包 sha256 | `de845c3a249c3c78ba389f33e84945c8e0df745b93daa743f2597527fba5f5c5` ✅ 同上 |
| 覆盖 | 546 文件；复核后新增/真实差异/换行差异均为 0 |
| editable 安装 | `Successfully installed MCP_CREO_MechDog-0.3.5` |
| 编译 | 走 `config.json: vcvars64_env`（三键）**一次成功** |
| `creo_worker.exe` | **8,953,856 B**（0.3.4 为 8,952,320 B，因 `generic.cpp` 改动重编） |
| `build/source.sha256` | `0901019b6bb93547a6353eb6a766d6c3233bcc051cd03ec83a1a37aef22c7814` |
| `@mcp.tool` 装饰器 | **84**（静态计数，与发布说明一致） |
| 种子清单 | **9**（`two_straight` … `six_smooth`） |

### 1.2 ⭐ 强证据：一次完整版本升级**完全没有触碰回调注册**

0.3.4 报告里我留下一个未验证项："升级场景下注册是否真的不受影响"。本轮正好具备验证条件：
**0.3.5 只改了 `generic.cpp`，`blend_loader.cpp` 与 `blend_sync.cpp` 均未变**。于是可以纯文件层面对比升级前后：

| 观测项 | 升级前（0.3.4） | 升级后（0.3.5） | 结论 |
| --- | --- | --- | --- |
| `build/blend_callback_protk.dat` sha256 前 16 位 | `2fa27ef800b9385f` | `2fa27ef800b9385f` | **未变** |
| `protk.dat` 的 `exec_file` | `...\blend_loader\a1367934…\loader.dll` | 同左 | **未变** |
| `loader_fingerprint` | `a136793470db13e4…` | `a136793470db13e4…` | **未变** |
| `loader_sha256` | `350ab92abf3ce3a7…` | `350ab92abf3ce3a7…` | **未变** |
| `creo_blend_loader.dll` 大小 | 3,272,704 B | 3,272,704 B | **未重编** |
| `creo_blend_sync.dll` 大小 | 351,744 B | 351,744 B | **未重编** |
| `payload` 指纹 / sha | `121c8884…` / `27467781…` | `121c8884…` / `27467781…` | **未变** |
| `build/blend_loader/` 目录数 | 1 | 1 | 未新增 |
| `build/blend_callback/` 目录数 | 6 | 6 | 未新增 |

**即：跨一次版本升级（含 worker 重编），Creo 侧注册不需要任何重做。**
这从实证上补上了 0.3.4 分代架构的关键一环 —— 我此前报告的"每次重编译注册失效"确实已解决。

> 说明：本结论**不含**"回调加载后直接放样成功"这条链路（需 Creo GUI 注册 + 实机连接，本轮按约束未做）。

### 1.3 BUG-054 实现确认（读码）

`native/generic.cpp` 的 `extrude_or_revolve` 由 `void` 改为返回 `J`，并把 cut 零去料变成硬失败：

```cpp
static J extrude_or_revolve(const J &op, bool revolve) {
    ...
    bool cut = op.value("mode", "add") == "cut";
    double before_volume = cut ? volume() : 0.0;
    ...
    J details = J::object();
    if (cut) {
        CK(ProSolidRegenerate((ProSolid)board, PRO_REGEN_NO_FLAGS));
        double removed = before_volume - volume();
        log("CUT_MATERIAL_REMOVED_MM3=%.12f\n", removed);
        if (removed <= std::max(1e-9, fabs(before_volume) * 1e-12))
            throw std::runtime_error("Extrude/Revolve cut removes no material; check the sketch position, "
                                     "direction and depth against existing geometry");
        details["material_removed_mm3"] = removed;
    }
    ...
    return details;
}
```

（原文错误信息为 `"Extrude"/"Revolve"` 二选一拼接。）这与发布说明的"零去料不再静默成功、失败回滚、有效切除返回 `material_removed_mm3`"一致。
**判定阈值**为 `max(1e-9, |before_volume| × 1e-12)`，量级极小，等价于"完全未去料"，我认为是合理选择。

---

## 2. ❌ `vcvars64_env` 只接受恰好三键 —— 第三次未修

### 现状

`src/creo_mechdog/build_support.py` 与 0.3.4 **逐字相同**：

```python
COMPILER_ENV_KEYS = ("INCLUDE", "LIB", "PATH")

def validate_compiler_env(value: object) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != set(COMPILER_ENV_KEYS):
        raise ValueError("vcvars64_env must contain exactly INCLUDE, LIB and PATH")
```

- 报错文案**也未改**（仍不提示"应只保留三键、把 SDK 路径并入 INCLUDE/LIB"）；
- 我在 **2026-10-16**（0.3.3 报告）与 **2026-10-17**（0.3.4 报告）各报过一次，本版仍原样。

### 为什么仍值得改

本机因 `reg.exe` 被安全中心拦截，`vcvars64` 探测不到 SDK，只能靠 `vcvars64_env` 显式给环境 —— 这条路是**唯一可行的编译方式**，所以它的易用性直接影响"能不能装上"。
而用户按直觉把真实 `vcvars64` 的完整环境（含 `WindowsSdkDir` / `WindowsSDKVersion` / `UniversalCRTSdkDir` / `VCToolsInstallDir`）写进去时，会被一句 `must contain exactly INCLUDE, LIB and PATH` 直接打断，且不知道该保留哪些。

**建议**（同上两轮）：
1. 放宽为"**必须包含 INCLUDE/LIB/PATH，其余键忽略或原样透传给子进程**"；
2. 或至少把报错改成可操作的，例如
   `vcvars64_env 只接受 INCLUDE/LIB/PATH；收到多余键: WindowsSdkDir, WindowsSDKVersion（SDK 路径请并入 INCLUDE/LIB）`。

---

## 3. ⚠️ BUG-056（P1）：通道静默失效 —— 它正在阻塞本机的实机验证

发布说明原文：

> **已知问题：BUG-056（P1）尚未修复。** 通道曾在验证后约 37～41 秒静默失效，随后已有无 Creo 会话观测，根因待核实。

这条对本机的影响是**直接且当下**的：
- 本机 Creo 会话此前出现过卡死（BUG-001），按用户决定已关闭该条目，但**根因未定**；
- 因此本机被要求**停止新的 Toolkit 连接与故障注入**，直到根因核对完成；
- 结果是：**从 0.3.4 起，本机已无法通过实机回测来验证任何建模相关修复**（包括本轮 BUG-054 的 cut 守卫）。
  我只能验证"装得上、编得出、清单对、注册不受影响"，**不能验证"切得对"**。

这不是抱怨，而是希望作者知道：**BUG-056/BUG-001 这类通道稳定性问题，是比建模功能更靠前的阻塞项**。
一个能让"37 秒后静默失效"复现的最小步骤（哪怕只有日志时间线）会非常有价值 —— 目前我只能确认"现象存在、根因未知"。

**建议**：
1. 若已有可疑的时序窗口（例如锁释放与终态发布之间的间隙、`ProEngineerConnect` 探针的超时余量），
   请在 `docs/work-items/BUG-056.md` 里记录**可判定的观测点**（日志关键字、时间戳关系），便于外部环境对齐；
2. 提供一条"**不建立 Toolkit 连接**的自检路径"（例如仅校验部署产物与配置一致性），
   这样受限环境至少能确认安装正确性，而不必冒着卡死风险去连 Creo。

---

## 4. 🟡 `build/blend_callback/` payload 目录仍无清理

本轮 `blend_sync.cpp` 未变，所以目录数**保持 6 个**（未新增）。但这只说明"没变化时不新增"，**清理机制依然不存在**：

- `src/creo_mechdog/blend_callback.py` 中仍然只有 `temporary.unlink(missing_ok=True)`（原子替换用），无目录清理；
- 当前 6 个 payload 目录、约 17 MB，跨 10-16 → 10-17；
- 目录名即哈希，无"当前"指针。

由于注册已改走 loader，这些目录**不再影响功能**，纯属磁盘与可读性问题。建议同 0.3.4 报告：发布新 payload 后清理旧目录（保留最近 N 个），或写一个 `current.json` 指针。

---

## 5. 本轮**未验证**清单（按约束明确声明）

以下项目因"停止新的 Toolkit 连接"约束**未执行**，不作通过结论：

| 项目 | 状态 |
| --- | --- |
| BUG-054 cut 零去料的实机行为（失败回滚、revision 不推进、`material_removed_mm3` 数值） | **未验证** |
| BUG-055 `expected_pending_job_id` 的 MCP 契约（null / 省略 / 空串拒绝） | **未验证** |
| `creo_reconcile_model` 的恢复动作矩阵 | **未验证** |
| 回调加载后直接放样端到端 | **未验证**（且需 Creo GUI 注册，属用户本人操作） |
| BUG-056 通道稳定性 | **未验证**（且正是本约束的起因） |

---

## 6. 需要作者回复的问题

1. **§2**：`vcvars64_env` 是否放宽（或改进报错）？这是第三次提出，且它是受限环境下唯一的编译入口。
2. **§3**：BUG-056 是否有可判定的观测点/最小复现？本机因它全面停掉了实机验证，任何线索都有帮助。
3. **§3**：能否提供一条**不建立 Toolkit 连接**的安装自检路径（部署产物 + 配置一致性）？
4. **§4**：payload 目录清理是否排期？
5. 需要材料我随时可提供：`blend_callback_protk.dat`、`blend_loader_build.json`、`blend_sync_build.json`、`build.log`、升级前后目录清单。
