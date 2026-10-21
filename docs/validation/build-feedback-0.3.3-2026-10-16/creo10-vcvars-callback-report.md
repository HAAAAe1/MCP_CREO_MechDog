# 2026-10-16 CREO 10.0.0.0 0.3.3 vcvars64_env 键集过严与 Warning C4273 噪音及回调目录无限累积.md

> 反馈人：终端用户（非项目作者）
> 记录日期：2026-10-16
> 实测版本：从 **0.3.2** 升级到 **v0.3.3**（2026-10-16 19:14 发布，"SDK 编译与安装诊断"）
> 关键背景：本机 `reg.exe` 被安全策略黑名单拦截，`vcvars64.bat` 探测不到 Windows SDK，历来无法直接编译。
> 仓库：https://github.com/wudahua/MCP_CREO_MechDog

---

## 0. 环境信息

| 项 | 值 |
| --- | --- |
| OS / Creo | Windows 10 x64 / Creo Parametric **10.0.0.0**（`D:\Program Files\PTC\Creo 10.0.0.0`） |
| 编译器 | VS 2022 BuildTools 17.14.40 / 工具集 14.44.35207 |
| Windows SDK | 10.0.26100.0 |
| Python | 3.13 x64，`.venv` editable（工程根含空格） |
| 本机特殊约束 | **`reg.exe` 被安全中心黑名单硬拦**，`vcvars64.bat` 因此探测不到 Windows SDK → INCLUDE/LIB 缺 UCRT/Kits |
| 本次源码 | official `MCP_CREO_MechDog-0.3.3-source.zip`，sha256 `a4e7f89f4ea91c923aceaac3b00f963cc54c9c51c198edf89e03d31f1e5c608f` ✅（附件 `.sha256` 与发布说明双一致） |
| 种子包 | `7e1332dd87ec0a90dd20600594e88580721df50eaff66f4e588a7ad771e79e70` ✅ 同上 |

---

## 1. ✅ 好消息先说：0.3.3 的 `vcvars64_env` 真正解决了本机的编译阻塞

这是本版最实用的修复。发布前本机必须靠**自维护的本地适配脚本** `_local/rebuild-native.cmd`
（在 `vcvars64` 之后手工注入 SDK include/lib）才能编译；官方路径会报：

```
RuntimeError: MSVC/Windows SDK environment preflight failed; inspect ...\build\build.log
(SDK discovery or registry access may be blocked)
Build error summary (last 15 error lines):
No error-level lines found in the build log tail.
```

本版按 `docs/INSTALL.md` 使用 `config.json` 的 `vcvars64_env`：先抓取 `vcvars64` 当前环境、
再把 UCRT/Windows Kits 路径前置进去，然后 `python bridge.py build`：

```
E:\WorkBuddy Space\MCP MCP_CREO_MechDog\build\creo_worker.exe      ← 官方路径直接成功
```

- 产物：`creo_worker.exe` 8,866,816 B + `creo_blend_sync.dll` 3,384,832 B
- 指纹 `3b2bce41108ec4fa8358b02efd0a8b54a1df0720881009fc01d2ed9d2141968d`，与 `build_native()` 缓存一致
- 回归：3 截面自动匹配 succeeded / `saved_file_reloaded_and_verified=true` / volume **22159.999999999996**
- 版本 0.3.3 / 82 工具 / 9 种子 / 直接放样仍 12 s 快速失败 `BLEND_CALLBACK_SETUP_REQUIRED`（BUG-007 保持修复）

**结论：这个方向完全正确。** 但也正因为真的用上了，才暴露了下面两个具体问题。

---

## 2. 🔴 问题一：`vcvars64_env` 只接受恰好 3 个键（其余键一律拒绝）

### 现象

按 DEV-021 的描述"支持完整 INCLUDE/LIB/PATH"，我第一次把抓取到的完整环境（含 `WindowsSdkDir`、
`WindowsSDKVersion`、`UniversalCRTSdkDir`、`VCToolsInstallDir`、`WindowsLibPath` 等）写进 config.json —— 这本是
**为了把 SDK 存在性提示给 preflight**，结果直接报错：

```
File "...\src\creo_mechdog\build_support.py", line 24, in validate_compiler_env
    raise ValueError("vcvars64_env must contain exactly INCLUDE, LIB and PATH")
ValueError: vcvars64_env must contain exactly INCLUDE, LIB and PATH
```

只有裁剪成 **INCLUDE / LIB / PATH 三键**后才通过。

### 为什么值得修

`INCLUDE`/`LIB` 里实际已包含 UCRT 与 Kits 路径（本机实测裁剪后编译成功），所以能编过；
但 **`tools/compiler_preflight.py` 若依赖 `WindowsSdkDir` / `WindowsSDKVersion` 之类来判断 SDK 是否就绪**，
在"只给 3 键"的合法输入下就无法独立判断 SDK 齐全与否 —— 只能靠 cl 去撞。这就让"安装诊断"的定位打了折扣。

### 建议（任一即可）

- 放宽为"**必须包含 INCLUDE/LIB/PATH，其余键忽略但不得报错**"（或原样保留到环境里一并传给子进程 —— 毕竟真实 `vcvars64` 环境本就有十几个变量）；
- 若要严格，也请把错误信息改成可操作的：
  `vcvars64_env 只接受 INCLUDE/LIB/PATH；收到多余键: WindowsSdkDir, ...（如需 SDK 提示，请把 SDK 路径并入 INCLUDE/LIB）`。

---

## 3. 🟠 问题二：`bridge.py build` 打印的"构建错误摘要"只报 warning，易误导

`DEV-019` 的机制是"失败时附错误摘要 / 保留末尾 15 条 error"。本次实测**成功路径**的 `build/build.log` 里，
尾部被塞满的是一段 `blend_sync.cpp(220)` 触发的 **C4273（DLL 链接不一致 / 内联展开）类 warning 模板实例化瀑布**：

```
E:\...\native\blend_sync.cpp(220): note: 参见
"std::basic_string<...>::basic_string" 的第一个可用函数定义
C:\...\MSVC\14.44.35207\include\xstring(812): note: 参见正在编译的函数模板实例化 ...
     with [ _InIt=wchar_t *, _OutIt=char *, _Size_type=unsigned __int64 ]
C:\...\include\xstring(968): note: ..._Copy_n_unchecked4<wchar_t*,_Size,char*>...
（连续多页）
```

log 尾部看到这堆 `note:`，**人肉判断很容易误以为编译失败**。而实际上 `BUILD_RC=0`，exe 正常产出。

（附带一句：编译输出里的**日志尾部 128 KiB / 末尾 15 条 error** 的摘要在"成功"时也会把这堆 note 写进
`build.log` —— 建议在成功时**只记录 vcvars/preflight 与 cl/link 摘要**，或把 `note:` 行也过滤掉。）

### 建议

1. `build.log` 的成功/失败判定用 exit code，日志里明写 `RESULT=success` / `RESULT=failed` 一行；
2. 错误摘要只挑 `error` / `fatal` 行；`note:` 在已知为 warning 上下文时裁剪；
3. 顺便考虑给 `blend_sync.cpp` 那处消除 C4273 噪声（见下条）。

---

## 4. 🟠 问题三（沿用，恶化）：回调 DLL 非确定性构建 × sha 目录 = 目录无限累积

这是 0.3.2 已报告的核心问题，**本版再次实测并观察到恶化**：

`build/blend_callback/` 目录数随重编译增长：

| 版本/时点 | 目录数 |
| --- | --- |
| 0.3.1 首次 | 1 |
| 0.3.2 首次 | 2 |
| 0.3.2 复测（连编两次） | 3 |
| **0.3.3 本次官方编译后** | **5** |

而 `native/blend_sync.cpp` 在 0.3.1 / 0.3.2 / 0.3.3 三个版本里**逐字节相同**（sha `c2c6d4a6…`），
却已经产生了 4 个互不相同的 DLL 副本。

**本次附带证据**：正是由于这个非确定性，用户每次升级后都必须重新在 Creo「辅助应用程序」注册
新 `protk.dat`（旧注册指向已失效路径），否则直接放样立即失败。

**建议**（维持 0.3.2 报告的方案，附优先级）：

1. **注册路径与 DLL 哈希解耦** —— 副本目录用固定名 `build/blend_callback/current/`，`protk.dat` 指向它；
   当前 DLL 哈希记录在旁（`callback_manifest.json`）；
2. **自动清理过期 sha 目录**（只留当前 1 个），否则无限累积；
3. 需要 sha 目录时，也请把 `build_native()` 的**缓存判据**从"exe 指纹 + DLL 实际 sha"改为
   "exe 指纹 + 记录的 callback fingerprint"，避免源码未变却因 DLL 非确定而重复重建；
4. 长期项：用 `/Brepro` 之类手段让 DLL 可复现。

---

## 5. 🟢 观察项（非缺陷）

- **BUG-033 常量探针**：本机 Creo 10 SDK 的 `constants.inc` 生成正常，未出现旧 SDK 硬引用缺失场景；实测未复现其目标问题，但机制看起来正确（本版 `capabilities` 33 键，未见 pra 常量节点缺失）。
- 官方编译成功后，本机 `_local/rebuild-native.cmd` 已**不再需要**（仅作历史备份保留）。
- 0.3.3 把 `tests/test_general_validation.py` 移出发布（本机旧文件随之不再需要），`tools/test_general.py` 保留。
- DEV-022（WindowsApps 占位提示）/ DEV-020（VS 组件缺失诊断）在本机未触发，未验证。

---

## 6. 本次实测汇总

| 项 | 值 |
| --- | --- |
| `version` / `tools` / `seeds` | **0.3.3** / **82** / **9** |
| `creo_worker.exe` / `creo_blend_sync.dll` | 8,866,816 B / 3,384,832 B |
| `build/source.sha256` | `3b2bce41108ec4fa8358b02efd0a8b54a1df0720881009fc01d2ed9d2141968d` |
| 3 截面自动匹配体积 | `22159.999999999996` mm³ |
| 直接放样失败耗时 | 12 s（`BLEND_CALLBACK_SETUP_REQUIRED`，BUG-007 保持修复） |
| `build/blend_callback/` 目录数 | **5**（源码相同的第 4、5、6 次编译产物） |
| 用官方路径编译 | ✅ 通过（`bridge.py build` + `vcvars64_env`） |

## 7. 需要作者回复的问题

1. **Q1**：`vcvars64_env` 能否放宽为"必须含 INCLUDE/LIB/PATH，多余键忽略/透传"？
   若保持严格，请把报错指引写清楚（当前只抛"must contain exactly ..."，用户无从知道该不该保 SDK 相关键）。
2. **Q1 延伸**：`compiler_preflight` 是否应单独识别 `vcvars64_env` 中的 SDK 目录，从而在"三键但缺 SDK"时
   给出比 `cl` 失败更早的诊断？
3. **Q2**：`build.log` 成功时能否精简、并显式写 `RESULT=success`？错误摘要能否只挑 error/fatal 行？
4. **Q3**：`build/blend_callback/` 的 sha 目录无限累积 + 非确定性构建，是否已排期修复（0.3.2 已报）？
5. 需要更多材料（`vcvars64_env.json` 原始/裁剪两份、`build.log`、`build_native()` 二次编译对比序列）可随时提供。
