# CREO 10.0.0.0 · MCP 0.4.2：连续第二版注册稳定（良性），但 json.hpp 与 vcvars64_env 两处隐患仍未动

> 反馈人：终端用户（非项目作者）
> 记录日期：2026-10-20
> 实测版本：**0.4.2**（2026-10-20 13:31 发布，PATCH，`creo_open_file` + capabilities 分页），从 0.4.1 升级
> 环境：Windows 10 x64 / **Creo Parametric 10.0.0.0** / VS2022 BuildTools 14.44.35207 / Windows SDK 10.0.26100.0 / Python 3.13
> ⚠️ **验证范围声明**：沿用 2026-10-17 用户约束（停止新的 Toolkit 连接/故障注入），本轮**未发起任何 Creo 连接、未做建模回测**。
> 仓库：https://github.com/wudahua/MCP_CREO_MechDog

---

## 0. 摘要

| 项 | 0.4.2 状态 |
| --- | --- |
| 升级本身（校验/覆盖/安装/编译） | ✅ 全部成功，87 工具 / 9 种子 |
| **本轮回调注册是否失效** | ✅ **连续第二版未失效**（五项指纹全未变，见 §1） |
| **`json.hpp` 移出 loader/payload 指纹清单** | ❌ **未实施**（清单仍含它，`bridge.py` 中 grep 计数 1；隐患持续） |
| `vcvars64_env` 只接受恰好三键 | ❌ **第六次未修**（`build_support.py` 报错行逐字未变） |
| `creo_capabilities` 默认 compact 分页（FEAT-023） | ✅ 新增（这是**第二个**"默认响应改摘要"的接口，迁移提示见 §4） |
| payload/loader 目录清理 | 🟡 仍无机制（本轮未新增：7 / 2） |

---

## 1. ✅ 注册稳定性连续第二版验证通过

0.4.2 只改了 `native/generic.cpp`（原生真实改动仅此一个），指纹清单五文件
（`blend_loader.cpp` / `blend_sync.cpp` / `callback_identity.h` / `callback_api.h` / `third_party/json.hpp`）**全部 SAME**。

`bridge.py build` 后与 0.4.1 基线对比：

| 观测项 | 0.4.1 基线 | 0.4.2 | 结果 |
| --- | --- | --- | --- |
| `blend_callback_protk.dat` sha 前 16 | `fc62f1548f4a1895` | `fc62f1548f4a1895` | **未变** |
| `loader_fingerprint` | `d26fa82164596688…` | `d26fa82164596688…` | **未变** |
| `payload_fingerprint` | `55322290a7ebdf83…` | `55322290a7ebdf83…` | **未变** |
| `creo_blend_loader.dll` sha 前 16 | `350d68a5982f984b` | `350d68a5982f984b` | **未变（未重编）** |
| `creo_blend_sync.dll` sha 前 16 | `07c5e5c5d7538a94` | `07c5e5c5d7538a94` | **未变（未重编）** |
| `build/blend_loader/` 目录数 | 2 | 2 | 未新增 |
| `build/blend_callback/` 目录数 | 7 | 7 | 未新增 |
| `creo_worker.exe` | 9,013,760 B | **9,042,432 B** | **已重编**（正常） |

**连续两个版本（0.4.1、0.4.2）升级，用户都无需重新注册回调。** 这说明 0.3.4 引入的分代架构在"清单文件不变"的前提下是稳定的 —— 问题只剩 §2 那一处清单内容本身。

---

## 2. ❌ 两项遗留仍未处理（分别第三次 / 第六次提出）

### 2.1 `third_party/json.hpp` 仍在 loader/payload 指纹清单

`bridge.py` 中 loader/payload 指纹清单仍为四文件（含 `native/third_party/json.hpp`），与 0.4.0/0.4.1 一致。

- 0.4.0 的实际事故（仅 CRLF→LF 差异 → 世代换代 → 注册失效一次）依然可能重现；
- 0.4.1、0.4.2 连续两版"没踩到"，只是因为这两版没改 `json.hpp` —— **机制性风险未消除**。

**建议**（维持 10-18 / 10-20 两轮报告）：把 `json.hpp` 移出 loader/payload 指纹清单、改计入 worker 的 `source.sha256`；
或指纹前对清单文件做换行归一化；或在 CI 加"`native/third_party/` 禁格式化"校验。

### 2.2 `vcvars64_env` 只接受恰好三键

`build_support.py` 的报错行逐字未变：

```
raise ValueError("vcvars64_env must contain exactly INCLUDE, LIB and PATH")
```

**第六次提出**（0.3.3 / 0.3.4 / 0.3.5 / 0.4.0 / 0.4.1 / 本版）。本机三键配置可用，功能不受阻；
但这条是 `reg.exe` 被拦环境下唯一的编译入口，报错不指引"应只保留三键"。

---

## 3. ✅ 本轮已验证（非连接类）

| 项 | 结果 |
| --- | --- |
| 源码包 sha256 | `8360c558d599871011e9c4ebedfad54aa4e8888c3ba1d34bbe2fac9201514db0` ✅（与 Release body 一致） |
| 种子包 sha256 | `ba0e04203ff36772e25c1c7ca10055c70e9483de201a4b8618703f1ccc3564a0` ✅ 同上 |
| 覆盖 | 656 文件；复核新增/真实差异/换行差异均为 0 |
| editable 安装 | `Successfully installed MCP_CREO_MechDog-0.4.2` |
| 编译 | `vcvars64_env` 三键一次成功；`creo_worker.exe` **9,042,432 B** |
| `@mcp.tool` 装饰器 | **87**（静态计数） |
| 新工具 | ✅ `creo_open_file` 在 `server.py`；包内新增 `open_file.py`、`capability_pages.py` |
| 种子清单 | 9 |
| 注册稳定性 | ✅ 连续第二版未失效（§1） |

### 未验证（按实机冻结约束）

`creo_open_file` 实机打开/缺件装配 `RETRIEVE_INCOMPLETE`、`creo_capabilities` 分页实测、
FEAT-006/008 `reason_code`/`refusal_details` 实际返回 —— 全部需要 Creo 连接，**均未验证**。

---

## 4. 🟡 需要注意的迁移点：`creo_capabilities` 也改成默认摘要了

FEAT-023：`creo_capabilities` 默认返回 compact 摘要页（约 10 KB，旧全量 106 KB），`detail=full` 走七 section 分页
（32 KiB 单页、600 秒冻结快照、oversize 显式标记）。

这是继 0.3.1（`creo_list_models`/`creo_inspect_model`）之后**第二个改为"默认摘要 + 分页"的接口**。
对 Agent/客户端意味着：

- 依赖全量 capabilities 的旧调用方会**静默拿到摘要**（少了细节但不报错），需要显式 `detail="full"` 并沿 `cursor` 遍历；
- 建议在 README 的显著位置汇总一张**"默认摘要化接口一览表"**（现散落在各版发布说明里），降低使用方踩坑成本。

---

## 5. 需要作者回复的问题

1. **§2.1（第三次提出）**：`json.hpp` 是否移出 loader/payload 指纹清单？本机已连续两版验证"清单不变 → 注册稳定"，
   只剩这一处机制性风险。
2. **§2.2（第六次提出）**：`vcvars64_env` 键集是否放宽/改进报错？
3. **§4**：能否在 README 汇总"默认摘要化接口一览"（现已有 `creo_list_models`、`creo_inspect_model`、`creo_capabilities` 三个）？
4. 需要材料可随时提供：新旧 `blend_callback_protk.dat` / `blend_loader_build.json` / `blend_sync_build.json` / `build.log`。
