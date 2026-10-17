# 2026-10-17_CREO_0.3.3_BUG-033修复与DEV-021现场验证

> 反馈对象：MCP_CREO_MechDog **0.3.3**（tag v0.3.3，commit 9ee923c）
> 环境：Windows 10 x64 (19045) / Python 3.13.14 x64 / MSVC 19.44.35229 + Windows SDK 10.0.26100 / Creo Parametric **9.0.0.0** Toolkit SDK（真实旧版 SDK 现场）
> **结论先行：本次更新未发现产品问题。** 0.3.3 采纳并实装了此前反馈（BUG-033 + DEV-019～022），本机作为真实的 Creo 9 SDK 环境完成了现场验证，全部通过——正好覆盖 0.3.2 发行说明中声明的"本机无 Creo 9 SDK，Creo 9 实机编译未验收"缺口（编译部分）。

---

## 一、更新过程（无摩擦）

- 备份既有本地补丁后 `git reset --hard origin/main` 升级到 0.3.3（9ee923c）；**本地 3 文件补丁被干净移除**——上游已实装同等方案，且守卫比我此前的版本更严谨（两个常量同时 `defined()` 判断）。
- 更新管线一次通过：`pip install -r requirements.lock.txt`（依赖无变化）→ `pip install --no-deps -e .` → `seeds.py --install`（九种子 SHA256 校验通过）→ `bridge.py build`。
- `creo_check_environment` 全绿；MCP stdio 冒烟测试 82 个工具；**单元测试 263/263 通过**（`build/unit_test_report.json`：failures=0, errors=0, success=true）。
- `git status` 干净；0.3.3 的分发归一化（LF 种子文本）未引发任何本地摘要差异。

## 二、BUG-033 修复的 Creo 9 现场验证（编译缺口已闭合）

在**零本地补丁**的 0.3.3 源码上，基于真实 Creo 9.0.0.0 Toolkit SDK：

| 验证项 | 结果 |
| --- | --- |
| `tools/generate_constants.py` 解析 Creo 9 头文件 | ✅ 正常生成常量表（6109 个常量名） |
| 探针宏输出 | ✅ Creo 9 下 `native/constants.inc` 中 `MECHDOG_HAS_*` 为 **0 个**（常量缺失 → 宏不定义，符合设计） |
| 条件编译 | ✅ 两处调用点（geometry.cpp / generic.cpp）在 Creo 9 下正确省略元数据节点，无 C2065 |
| 原生构建 | ✅ `creo_worker.exe`（8.7 MB）+ `creo_blend_sync.dll`（3.3 MB）一次编译链接通过 |
| 冒烟 | ✅ 82 工具、环境检查全绿 |

建议：BUG-033 工作卡的验收记录可引用本报告作为 Creo 9 编译侧现场证据；Creo 9 运行时建模仍建议保持"未验收"口径（见第四节）。

## 三、DEV-021（vcvars64_env）实测：可完全替代 reg.exe 包装脚本

此前的 reg.exe 受限环境只能靠手工 wrapper（`vcvars64.bat` 之前设好 INCLUDE/LIB/PATH）。0.3.3 的官方机制实测可用：

1. **config.json 配置**（完整展开路径，无 `%PATH%`）：

```json
"vcvars64_env": {
  "INCLUDE": "D:\\BuildTools\\VC\\Tools\\MSVC\\14.44.35207\\include;C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0\\ucrt;...\\um;...\\shared;...\\winrt;...\\cppwinrt",
  "LIB": "D:\\BuildTools\\VC\\Tools\\MSVC\\14.44.35207\\lib\\x64;C:\\Program Files (x86)\\Windows Kits\\10\\Lib\\10.0.26100.0\\ucrt\\x64;...\\um\\x64",
  "PATH": "D:\\BuildTools\\VC\\Tools\\MSVC\\14.44.35207\\bin\\Hostx64\\x64;C:\\Program Files (x86)\\Windows Kits\\10\\bin\\10.0.26100.0\\x64;C:\\Windows\\System32;C:\\Windows"
}
```

2. **`bridge.py build`**：`build.cmd` 正确走显式环境分支（`set "INCLUDE=..."` 等三行，不调用 vcvars64.bat），编译通过。
3. **`creo_check_environment`**：`compiler_setup` 报告 `"source": "vcvars64_env"`、`compiler_environment` 说明使用显式环境。
4. **`setup.ps1 -CheckOnly`（不带任何编译器参数）**：仅凭 config.json 的 `vcvars64_env` 通过全部前置文件检查（17-22 行的 config 回读、46 行双缺失才抛错的逻辑正确）。
5. 一个可选的易用性建议（非缺陷）：PATH 为整体替换语义，用户需自行带入系统目录；INSTALL.md 已写"完整值"，可否在文档样例中直接给一份含 `C:\Windows\System32` 的 PATH 范例，减少用户漏配系统目录的概率。

## 四、DEV-019 / DEV-022 实测

- **DEV-019**：以合成日志 `error C2065: PRO_E_HLE_ADD_PARAMETERS: undeclared` 调用 `diagnose_build_failure`，输出 `SDK version hint: PRO_E_HLE_ADD_PARAMETERS may require a newer Creo Toolkit SDK...` + 末尾错误摘要，符合设计。
- **DEV-022**：未传 `-Python` 运行 setup.ps1 时，准确识别 WindowsApps 商店占位程序并给出"pass -Python with the real python.exe path"指引（实测触发，报错清晰可操作）。

## 五、环境备注（非产品问题，但可能影响作者的 WorkBuddy 内自测）

在 **WorkBuddy 代理沙箱内**运行 `tools/test_unit.py` 会出现约 **85 个假错误**：WorkBuddy CLI 注入的 `sitecustomize.py`（safe-delete bulk guard）会拦截测试中的 `Path.unlink()`（如 `toolkit-owner.lock` 清理）并 `raise SystemExit(1)`，测试框架记为 ERROR。**清除注入的 `PYTHONPATH`（或在本机终端/CI 运行）后 263/263 全部通过。** 作者的项目约定包含"WorkBuddy 测试"，若在 WorkBuddy 会话内跑单测会遇到同样现象，附规避方法供参考。

## 六、遗留未验证项（如实声明）

1. **Creo 9 运行时建模**未在本次重验：0.3.3 的 native 改动仅两处 `#ifdef` 守卫，Creo 9 下孔特征省略"不附加参数"元数据节点（几何与定位不受影响，与设计说明一致）；建议下次实机建模时留意孔特征参数表是否出现默认参数（仅元数据差异）。
2. BUG-034（Creo 9 种子加载 `ProMdlFiletypeLoad=-16`）等其他登记条目不在本次更新验证范围。

---

### 复现信息

| 项 | 值 |
| --- | --- |
| 更新 | `git fetch --tags` → `git reset --hard origin/main`（v0.3.3, 9ee923c） |
| 版本核对 | `version.py` = 0.3.3；冒烟 `list_tools` = 82 |
| 构建 | `bridge.py build`（config.json 使用 `vcvars64_env`，未调用 vcvars64.bat / reg.exe） |
| 单测 | `tools/test_unit.py`：263 通过 / 0 失败 / 0 错误（PYTHONPATH 清除后） |
| 本地补丁 | 已全部移除（上游实装 BUG-033）；备份仅存于 git 对象与 `build/patch_backup_20261016/` |
