# CREO 10.0.0.0 · MCP 0.3.4：分代修复已生效，payload 目录仍无清理 + vcvars64_env 键集未改

> 反馈人：终端用户（非项目作者）
> 记录日期：2026-10-17
> 实测版本：**0.3.4**（2026-10-17 14:29 发布，`model recovery and callback lifecycle integration`），从 0.3.3 升级
> 环境：Windows 10 x64 / **Creo Parametric 10.0.0.0** / VS2022 BuildTools 14.44.35207 / Windows SDK 10.0.26100.0 / Python 3.13
> 本机特殊约束：`reg.exe` 被安全中心黑名单拦截（依赖配置化编译环境，见 §4）
> 仓库：https://github.com/wudahua/MCP_CREO_MechDog

---

## 0. 摘要

**本版把我 10-16 报告的"回调注册反复失效"真正修好了** —— 这是本轮最重要的结论，先讲清楚。

| 我此前报告的问题 | 0.3.4 状态 |
| --- | --- |
| 回调副本目录按 DLL sha256 命名 → 每次重编译使 Creo 注册失效 | ✅ **已修复**（固定注册入口 + loader/payload 分层 + 不可变镜像，实测验证） |
| `build/blend_callback/` sha 目录无限累积 | ⚠️ **部分缓解**：不再影响注册，但**目录仍持续累积、无清理**（6 个 / 17 MB） |
| `vcvars64_env` 只接受恰好 INCLUDE/LIB/PATH 三键 | ❌ **未修复**（代码仍为 `set(value) != set(COMPILER_ENV_KEYS)` 即抛错） |
| 回调就绪状态无法预检 | 🟡 **已加字段但仍为 `unknown`**（诚实设计，但两种情形同值，见 §5） |

---

## 1. ✅ 修复确认：注册失效问题已实质解决（含实测证据）

### 1.1 新版架构

0.3.4 把原生的"一个回调 DLL"拆成**两层**：

| 层 | 产物 | 变化频率 |
| --- | --- | --- |
| **loader**（固定层） | `build\creo_blend_loader.dll`（3,272,704 B） | 仅 `blend_loader.cpp` / `callback_api.h` / `callback_identity.h` / SDK / config 变化时 |
| **payload**（每次操作） | `build\creo_blend_sync.dll`（351,744 B） | 随建模契约变化 |

注册入口**固定**为：

```
build\blend_callback_protk.dat
```

其内容指向 **loader 世代目录**（本次为 `a1367934…`）：

```
name MCP_CREO_MechDog Blend 3a7d9bd8
startup dll
exec_file E:\...\build\blend_loader\a1367934...\loader.dll
text_dir  E:\...\build\blend_loader\a1367934...
allow_stop true
delay_start true
end
```

关键：`loader_fingerprint` 的计算只纳入 **loader 源码 + 回调头 + SDK + config**，**不含 payload**：

```python
loader_digest = hashlib.sha256(b"MSVC17_MD_LOADER_v1" + abi.digest())
for relative in ("native/blend_loader.cpp", "native/callback_identity.h",
                 "native/callback_api.h", "native/third_party/json.hpp"):
    loader_digest.update(relative.encode() + source.read_bytes())
```

所以**升级 payload 不再需要重新注册** —— 正是我 10-16 建议的方案。

### 1.2 实测验证：删除 loader.dll 后自动恢复且注册路径不变

为验证"注册不会再被非确定性构建打乱"，我做了这个破坏性测试：

```
基线：
  protk.dat exec_file = ...\build\blend_loader\a1367934...\loader.dll
  loader.dll sha256   = 350ab92abf3ce3a7cdca4f2580c5781d6a250b6ea0985e5bcfa4198e3092ff24
  blend_loader/ 目录数 = 1

删除 build\creo_blend_loader.dll  →  跑 bridge.py build

结果：
  loader.dll 已恢复，sha256 = 350ab92a...（与基线完全一致）
  protk.dat exec_file 完全未变
  blend_loader/ 目录数 = 1（未新增世代目录）
```

即：**构建输出丢失时从 pinned 不可变镜像恢复，不重新链接、不改变已注册路径**。这从根上切断了"非确定性构建 → 注册失效"的链条。

> 说明：本次也观察到 `native/blend_sync.cpp` 等 payload 源码变化后，`build/blend_callback/` 会新增 payload 目录，但**注册指向的 loader 不变**，因此不影响 Creo 侧注册。这一点我认为是正确设计。

---

## 2. 🟠 残留问题：payload 目录持续累积，无清理、无"当前"标记

### 现象

`build/blend_callback/` 现在有 **6 个** sha 目录，**17 MB**，跨越两天：

| 目录（前 12 位） | 创建时间 |
| --- | --- |
| `96430578b3ac` | 2026-10-16 00:28 |
| `0e46ef9d7657` | 2026-10-16 14:12 |
| `e60521d26658` | 2026-10-16 14:16 |
| `b4e47bcab137` | 2026-10-16 19:47 |
| `6f60397ab04a` | 2026-10-16 22:03 |
| `274677813dad` | 2026-10-17 16:43（当前） |

`src/creo_mechdog/blend_callback.py` 里只有 `temporary.unlink(missing_ok=True)`（用于原子替换临时文件），**没有任何目录清理逻辑**。

### 影响

- 已**不再影响 Creo 注册**（注册走 loader），所以严重度下降；
- 但每次 payload 变化固定新增一个目录，**只增不减**：长期使用会持续占盘（当前 17 MB / 6 个，按天累积）；
- 目录名就是哈希，**没有任何"当前"标记**，用户/排障者无法一眼分辨哪个是正在用的 payload（虽然 `blend_callback_setup.json.module_file` 可以查，但需要工具配合）。

### 建议

1. 在 `prepare_callback()` 发布新 payload 后，清理**除当前**以外的旧 payload 目录（保留最近 N 个更稳妥，便于回退）；
2. 或在 `build/blend_callback/` 下写一个 `current.json`/符号式指针，标明当前 payload 哈希；
3. 若担心用户手工放置的文件被误删，可按"仅清理由本工具生成、且不在使用中"的保守规则处理。

---

## 3. ❌ 未修复：`vcvars64_env` 仍只接受恰好三个键

10-16 已报告过。本版代码未变：

```python
COMPILER_ENV_KEYS = ("INCLUDE", "LIB", "PATH")

def validate_compiler_env(value: object) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != set(COMPILER_ENV_KEYS):
        raise ValueError("vcvars64_env must contain exactly INCLUDE, LIB and PATH")
```

本机按三键配置可正常编译（见 §4），所以**功能不受阻**。但从"安装诊断"的角度：

- 用户按直觉把真实 `vcvars64` 的完整环境（含 `WindowsSdkDir` / `WindowsSDKVersion` / `UniversalCRTSdkDir` / `VCToolsInstallDir`）写进配置时，会直接被 `ValueError` 打断，且错误信息**没有告诉用户"应该只保留三键"**；
- 这些键恰恰是 `compiler_preflight` 判断 SDK 是否齐全最直接的依据。强制丢弃后，preflight 只能靠 cl 去撞。

### 建议（同上轮）

- 放宽为"**必须包含 INCLUDE/LIB/PATH，其余键忽略或原样透传到子进程**"；
- 若坚持严格，请在错误信息里给出可操作指引，例如：
  `vcvars64_env 只接受 INCLUDE/LIB/PATH；收到多余键: WindowsSdkDir, ...（SDK 路径请并入 INCLUDE/LIB）`。

---

## 4. ✅ 编译路径：本机已完全走官方配置（`vcvars64_env` 生效）

0.3.3 引入、0.3.4 继续沿用 `compiler_setup_script()` —— 有 `vcvars64_env` 时直接在 `build.cmd` 里 `set` 三键，不再 `call vcvars64.bat`：

```python
def compiler_setup_script(settings: dict) -> str:
    env = validate_compiler_env(settings.get("vcvars64_env"))
    if env is not None:
        return "\n".join(f'set "{key}={env[key]}"' for key in COMPILER_ENV_KEYS)
    vcvars = validate_local_path(settings.get("vcvars64"), "vcvars64")
    return f'call "{vcvars}"\nif errorlevel 1 exit /b 1'
```

本机（`reg.exe` 被拦、`vcvars64` 探不到 SDK）用三键配置 **`python bridge.py build` 一次成功**，三个产物齐全。**旧的自维护脚本 `_local/rebuild-native.cmd` 已彻底不需要。**

---

## 5. 🟡 观察：`creo_callback_status` 的 `readiness` 在两种情形下同值

新增工具 `creo_callback_status`（84 工具之一）返回：

```json
{
  "readiness": "unknown",
  "registration_status": "unknown",
  "reason": "no_runtime_identity_record",
  "protocol": 3,
  "artifact_status": "prepared",
  "instruction": "GUI registration cannot be queried. If this generation is already registered,
                  start it in Auxiliary Applications; otherwise register registry_file once ..."
}
```

**这是诚实的**：Creo 的 GUI 注册状态确实无法通过 Toolkit 查询，返回 `unknown` 而不是编一个值，比之前完全没有字段好。会话就绪（`connected: true`、建模成功）后连查 3 次仍稳定为上述值，说明探测本身是确定性的。

但存在一个可用性细节：

- **"从未加载过"** 与 **"已注册但无法查询"** 两种情形，`readiness` 都是 `unknown`，只能靠 `reason` 字段区分（本次为 `no_runtime_identity_record`）；
- 对 Agent 来说，"看到 `unknown` 该不该继续提交放样"仍需要解析 `reason` 才能判断。

**建议**：把 `readiness` 的枚举语义显式化，例如 `not_loaded`（无运行时身份记录 = 可确定未加载）/ `unknown`（有此记录但无法确认）；或在 `instruction` 之外给一个 `action_required: boolean`。

---

## 6. 本次实测汇总

### 升级执行

| 项 | 结果 |
| --- | --- |
| 源码包 sha256 | `e64c4246a0f0173bf3f434543e355192ed0cca1208831a4aa7a1ad86bb33fb5f` ✅ 附件与发布说明双一致 |
| 种子包 sha256 | `e7e59429aa94e38e25002e2041b816747bca9cf6c766ed14ad8a65f44b901d59` ✅ 同上 |
| 覆盖 | 509 文件，复核**新增/真实差异/换行差异均为 0** |
| editable 安装 | `Successfully installed MCP_CREO_MechDog-0.3.4` |
| 三次编译 | `creo_worker.exe` **8,952,320 B** / `creo_blend_sync.dll` **351,744 B** / `creo_blend_loader.dll` **3,272,704 B** |
| `build/source.sha256` | `f744338a702928d4c1b7d264…`（`build_native()` 缓存命中，免重建） |

### 功能验证

| 项 | 结果 |
| --- | --- |
| `version` / `tools` / `seeds` | **0.3.4** / **84** / **9** |
| 新增工具 | ✅ `creo_callback_status`、`creo_reconcile_model` |
| 回归：3 截面自动匹配混合 | succeeded / `saved_file_reloaded_and_verified=true` / **volume 22159.999999999996** |
| 直接放样 `op:"loft"` | **9 s** 快速失败 `BLEND_CALLBACK_SETUP_REQUIRED`（0.3.3 为 12 s，未回退成挂死） |
| 注册入口稳定性 | ✅ 删除 loader.dll 后自动恢复、sha 一致、`protk.dat` 不变（§1.2） |

### 原生产物结构变化（供作者对照）

`blend_sync.dll` 从 3,384,832 B **降至 351,744 B**，新拆出的 `blend_loader.dll` 为 3,272,704 B —— 符合"loader 固定层 + payload 精简"的设计意图。

---

## 7. 需要作者回复的问题

1. **§2**：`build/blend_callback/` 的旧 payload 目录是否能自动清理（保留最近 N 个）？或加一个"当前 payload"指针文件？
2. **§3**：`vcvars64_env` 是否放宽为"必须含 INCLUDE/LIB/PATH，其余忽略/透传"？若不放宽，请改进报错文案。
3. **§5**：`creo_callback_status.readiness` 能否区分 `not_loaded` 与 `unknown`，或增加 `action_required` 布尔？
4. 我已把 `protk.dat` / `blend_callback_setup.json` / `blend_loader_build.json` 三份产物样本留在本地，需要可随时提供。
5. 补充说明：本机 Creo 10 上我**无法完成 Creo 侧的 GUI 注册**（需本人操作安全确认），所以"回调真正加载后直接放样成功"这条端到端链路仍未验证，不做通过结论。
