# CREO 10.0.0.0 · MCP 0.4.1：json.hpp 换行致注册失效未根治（本轮侥幸未触发）+ vcvars64_env 第五次未修

> 反馈人：终端用户（非项目作者）
> 记录日期：2026-10-20
> 实测版本：**0.4.1**（2026-10-19 23:30 发布，PATCH，含新增公开工具），从 0.4.0 升级
> 环境：Windows 10 x64 / **Creo Parametric 10.0.0.0** / VS2022 BuildTools 14.44.35207 / Windows SDK 10.0.26100.0 / Python 3.13
> ⚠️ **验证范围声明**：沿用 2026-10-17 用户约束（停止新的 Toolkit 连接/故障注入），本轮**未发起任何 Creo 连接、未做建模回测**。
> 结论主要来自编译、文件层面对比与静态读码。
> 仓库：https://github.com/wudahua/MCP_CREO_MechDog

---

## 0. 摘要

| 项 | 0.4.1 状态 |
| --- | --- |
| 升级本身（校验/覆盖/安装/编译） | ✅ 全部成功，86 工具 / 9 种子 |
| **本轮回调注册是否失效** | ✅ **未失效**（我上轮问题的**第一次正面验证**：清单文件未动 → 注册稳定） |
| **`json.hpp` 换行差异的根治** | ❌ **未根治**：`third_party/json.hpp` 仍在 loader/payload 指纹清单里，只是本版恰好没改它（**隐患仍在**） |
| `vcvars64_env` 只接受恰好三键 | ❌ **第五次未修**（代码与报错文案与 0.4.0 逐字相同） |
| 附件 SHA256 由 Release body 直接给出 | ✅ **已修**（我上轮建议的，采纳得好） |
| `build/blend_callback/`、`blend_loader/` 目录清理 | 🟡 仍无机制（本轮未新增，维持 7 / 2） |
| `vcvars64_env` 之外的新发现 | 🟡 见 §5（worker 指纹覆盖 native 全量 `.h`，与 loader 清单不同步） |

---

## 1. ✅ 重要正面结论：升级完全没触碰注册（首次直接验证）

### 1.1 现象

我 10-18 报告"`json.hpp` 仅 CRLF→LF 差异就触发 loader 世代换代、注册失效一次"，
且建议把 `json.hpp` 移出 loader/payload 指纹清单。0.4.1 **没有采纳该建议**（见 §2），
但本版也没再改动 `json.hpp` —— 于是获得了**一次难得的对照实验**：

`bridge.py build` 后与 0.4.0 基线对比：

| 观测项 | 0.4.0 基线 | 0.4.1 | 结果 |
| --- | --- | --- | --- |
| `blend_callback_protk.dat` sha 前 16 | `fc62f1548f4a1895` | `fc62f1548f4a1895` | **未变** |
| `loader_fingerprint` | `d26fa82164596688…` | `d26fa82164596688…` | **未变** |
| `payload_fingerprint` | `55322290a7ebdf83…` | `55322290a7ebdf83…` | **未变** |
| `creo_blend_loader.dll` sha 前 16 | `350d68a5982f984b` | `350d68a5982f984b` | **未变（未重编）** |
| `creo_blend_sync.dll` sha 前 16 | `07c5e5c5d7538a94` | `07c5e5c5d7538a94` | **未变（未重编）** |
| `build/blend_loader/` 目录数 | 2 | 2 | 未新增 |
| `build/blend_callback/` 目录数 | 7 | 7 | 未新增 |
| `creo_worker.exe` | 8,979,456 B | **9,013,760 B** | **已重编**（正常，`generic.cpp` 有改动 + 新增 `inspection_units.h`） |

即：**跨一次小版本升级（worker 都重编了），Creo 侧注册一个字都不用动。**

这从正面印证了 0.3.4 分代架构的设计意图：**只要 loader/payload 指纹清单里的文件不变，注册就是稳定的。**

### 1.2 结论与推论

- 结论：注册稳定性 = "清单文件不变"。0.4.1 的升级实践证明了这一点。
- 推论（也是本报告的重点）：**稳定性目前依赖"清单文件恰好不被无关改动触及"这个前提，而不是靠机制保证** —— 见 §2。

---

## 2. ❌ 核心问题：`json.hpp` 仍留在指纹清单里，隐患未根治

我 10-18 的报告建议（三选一）：
1. 把 `native/third_party/json.hpp` 移出 loader/payload 指纹清单（其 sha 改计入 worker 的 `source.sha256`）；
2. 或指纹计算前对清单文件做换行归一化；
3. 或统一 `third_party/` 换行并提交说明。

**0.4.1 三项均未实施。** 0.4.1 的 `bridge.py` 中指纹清单与 0.4.0 完全一致：

```python
for relative in (
    "native/blend_loader.cpp",     # 或 blend_sync.cpp（payload 侧）
    "native/callback_identity.h",
    "native/callback_api.h",
    "native/third_party/json.hpp",     # ← 仍在此处
):
```

### 为什么仍未根治

`json.hpp` 是 vendored 第三方库，是**最容易被格式化工具、编辑器换行转换、补丁触碰**的文件。
0.4.0 就是一次典型事故（相对 0.3.5 只有 LF→CRLF，内容逻辑零变化）。
0.4.1 只是"这次没碰它"所以侥幸没触发。

**风险是持续的**：未来任何一次发版，只要有开发者/CI 在三级库上加一次格式化、或换一个 checkout 换行策略，
`protk.dat` 就会重新生成、loader 世代换代，**用户在 Creo 里注册的条目再次失效**。

而 0.4.0 的 README 已把"注册一次 + config.pro 持久化"写进对用户的承诺（FEAT-029 指引），
这种"承诺与实现之间存在缺口"的体验，正是我两次报告的同一件事。

### 建议（维持上轮，按优先级）

1. **最小改动、最有效**：把 `native/third_party/json.hpp` 从 loader/payload 指纹的四文件清单中删除，
   改为让它只参与 worker 的 `source.sha256`（worker 重编便宜、不涉注册）；
   loader/payload 的语义是"ABI/契约层面变了才换代"，vendored 库的换行变化显然不属于该类。
2. 或在指纹计算前对清单内文件统一换行归一化后再哈希（同时能缓解 0.3.2 报告的 worker 指纹换行敏感问题）；
3. 若都不做，至少在 `native/third_party/` 的 README/注释里写明"此文件禁止格式化"，并在 CI 加一条校验。

> 补充一个可佐证的对照：`native/inspection_units.h`（0.4.1 新增）会参与 worker 指纹（`rglob` 扫全部 `.h`，
> 本机实测 24 个原生文件），**但不参与** loader/payload 指纹（显式四文件清单）——
> 这说明"新增协作头文件"模式下设计是自洽的，唯独第三方库被放进了清单，属于可以低成本修正的一处不一致。

---

## 3. ❌ `vcvars64_env` 只接受恰好三键 —— 第五次未修

`src/creo_mechdog/build_support.py` 仍为：

```python
def validate_compiler_env(value: object) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != set(COMPILER_ENV_KEYS):
        raise ValueError("vcvars64_env must contain exactly INCLUDE, LIB and PATH")
```

与 0.3.3 / 0.3.4 / 0.3.5 / 0.4.0 **逐字相同**，报错文案未改。本机按三键配置编译正常（功能不受阻），
但这条是 `reg.exe` 被拦环境下**唯一的编译入口**，报错不指引"应只保留三键"会持续给新用户造成困惑。
**建议同前：放宽为"必须含 INCLUDE/LIB/PATH，其余忽略/透传"，或改进报错文案。**

---

## 4. ✅ 一项建议被采纳（反馈闭环的正面记录）

我 10-18 在文档 §4 建议：附件 SHA256 不要只写"见发布后回填"，应回归 Release 页面 body。
**0.4.1 已采纳** —— Release body 直接给出：

```
MCP_CREO_MechDog-0.4.1-source.zip   c1ef110462ec0e20818431dc8945411f39d12f9a8d2f66ce4052e65a7c528bcc（638 文件）
MCP_CREO_MechDog-0.4.1-seed-library.zip 68da44c3a3b089b922b7920b43de19943181b7e2cde990f1e19ad30cd7ad1148（24 文件）
```

实测与下载件一致 ✅。附件命名也回到了 0.3.x 的 `-source.zip` / `-seed-library.zip` 风格。
**这条闭环值得在文档里明确记一笔**，便于作者保持该做法。

---

## 5. 🟡 次要观察

### 5.1 worker 指纹与 loader/payload 清单对新增头文件的处理不一致

- worker 的 `source.sha256`：`rglob("native")` 扫**全部** `.cpp/.h/.hpp/.inc`（本机实测 24 个文件，含新增的 `inspection_units.h`）；
- loader/payload 指纹：**显式四文件清单**（不含 `inspection_units.h` 这类协作头）。

效果上是对的（协作头只该让 worker 重编，不该让注册换代），但**"第三方库被单列进 loader 清单"** 与这个原则冲突。合并进 §2 的建议 1 即可顺带统一。

### 5.2 payload/loader 目录仍无自动清理

本轮未新增（仍为 7 / 2），但 `src/creo_mechdog/blend_callback.py` 依旧只有临时文件 `unlink`，无目录清理。
在 §2 修好后世代切换频率会大降，此项优先级随之降低；建议连同 §2 一起处理。

---

## 6. 本轮已验证（非连接类）

| 项 | 结果 |
| --- | --- |
| 源码包 sha256 | `c1ef110462ec0e20818431dc8945411f39d12f9a8d2f66ce4052e65a7c528bcc` ✅（与 Release body 一致） |
| 种子包 sha256 | `68da44c3a3b089b922b7920b43de19943181b7e2cde990f1e19ad30cd7ad1148` ✅ 同上 |
| 覆盖 | 638 文件；复核新增/真实差异/换行差异均为 0 |
| editable 安装 | `Successfully installed MCP_CREO_MechDog-0.4.1` |
| 编译 | `vcvars64_env` 三键一次成功；`creo_worker.exe` **9,013,760 B** |
| `@mcp.tool` 装饰器 | **86**（静态计数，与发布说明一致） |
| 新工具 | ✅ `creo_list_session_models` 在册；包内新增 `session_models.py` |
| BUG-072 单位诚实化 | ✅ `native/generic.cpp:4` `#include "inspection_units.h"`；`:401` 输出 `units_query_code` |
| BUG-073 sketch 引用规范化 | ✅ `schema.py:32` `_normalize_sketch_ref`：纯数字串 `int()` 化 + 范围校验（`SketchRef` BeforeValidator） |
| 种子清单 | 9 |
| **注册稳定性对照实验** | ✅ 见 §1.1：5 项指纹全未变、目录不增 |

### 未验证（按实机冻结约束）

无盘 `prepare→apply` 全链路、`creo_list_session_models` 实机会话枚举、BUG-072 英寸摘要、BUG-073 四写法实机、
回调加载后 ready 分支 —— 全部需要 Creo 连接，**均未验证**。

---

## 7. 需要作者回复的问题

1. **§2（核心）**：是否把 `native/third_party/json.hpp` 移出 loader/payload 指纹清单（改仅计 worker 指纹）？
   本轮的对照实验已经证明"清单文件不变 → 注册稳定"，剩下的风险全部集中在这一处第三方文件上。
2. **§2**：若暂不放清单外，是否可加一条换行归一化（指纹前统一 LF）或 CI 校验（`native/third_party/` 禁格式化）作为过渡？
3. **§3**：`vcvars64_env` 键集（第五次提出）。
4. **§5.1**：是否顺带把"新增协作头文件只影响 worker 指纹"这一原则写进 CODING_STANDARD 或注释，避免后人再往回调清单里加文件？
5. 需要材料可随时提供：新旧两版 `blend_callback_protk.dat`/`blend_loader_build.json`/`blend_sync_build.json`、`build.log`。
