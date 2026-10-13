# 源码安装与接入

## 需要的环境

正式验收基线为 Creo 10，Creo 12 暂列实验兼容；具体已测范围与未测项见 [兼容矩阵](COMPATIBILITY.md)。仅做 Python 单元和语言检查的开发环境见 [开发入口](DEVELOPMENT.md)，不必先运行完整 Creo 安装流程。

- Windows x64；本版实测环境是 Creo Parametric 10.0.0.0。
- Python 3.12+ x64；本版安装实测使用 Python 3.12。
- 与 Creo 安装匹配的 C/C++ Toolkit SDK，包括头文件和 x64 链接库。
- Creo 公制模板 `Common Files/templates/mmns_part_solid_abs.prt` 和 `mmns_asm_design_abs.asm`。安装器与环境检查都要求这两份文件，即使首次只建零件，也需安装公制装配模板。
- Visual Studio C++ Build Tools，包含 MSVC x64 和 Windows SDK；本版实测 VS 2022。
- 可用于当前 Toolkit 开发与运行路径的 PTC 许可。
- 能运行本地 stdio MCP 服务的 AI 客户端。

本项目不提供 Creo、SDK、许可证或已解锁的二进制。项目 MIT 许可证及第三方条件见 [LICENSE](../LICENSE) 和 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。

## 安装步骤

下载源码 ZIP，解压后应能直接看到 `README.md`、`setup.ps1` 和 `server.py`。建议使用较短的可写路径，例如 `C:\MCP_CREO_MechDog`。

在该目录打开 PowerShell，执行：

```powershell
.\setup.ps1 -CreoRoot 'C:\Program Files\PTC\Creo 10.0.0.0'
```

`-CreoRoot` 指向包含 `Common Files` 和 `Parametric` 的安装目录，按实际位置替换。脚本优先使用明确提供的参数，其次使用已有本机 `config.json`；首次安装参考 `config.example.json`。编译器可由 Visual Studio 的 `vswhere` 检测。

可以明确指定所有程序路径：

```powershell
.\setup.ps1 `
  -Python 'C:\Path\To\python.exe' `
  -CreoRoot 'C:\Program Files\PTC\Creo 10.0.0.0' `
  -VcVars64 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
```

`C:\Path\To\python.exe` 必须替换为已安装的 Python。仅检查前置文件与 Python 架构而不执行安装时，在命令末尾加 `-CheckOnly`；这项检查不会连接 Creo，也不验证许可。

如果 Windows PowerShell 的脚本执行策略阻止运行，可在查看源码后，仅对这次安装进程指定策略：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1 -CreoRoot 'C:\Program Files\PTC\Creo 10.0.0.0'
```

脚本保留已有本机配置中的额外选项，创建项目内的 Python 虚拟环境及客户端配置，再安装锁定依赖、更新本机 SDK 常量并编译执行器。同步混合回调 DLL 独立校验缓存，只有自身源码、ABI/SDK、构建参数或 DLL 内容改变才重建。首次加载或 DLL 更新时，Creo 可能显示安全警告，需要使用者手动确认。每次构建先按当前 SDK 更新常量，并将 SDK 头文件内容计入缓存指纹；源码、配置及头文件都不变时复用现有二进制。不需要把 Creo 安装到示例路径；不修改 PTC 安装目录或全局 AI 客户端配置。

安装中断会输出 `INSTALL_INCOMPLETE`、失败阶段、已完成步骤和重跑方法。修复错误后在同一目录重跑相同安装命令即可，不必删除 `.venv`、模型或任务。`client-config.json` 提前生成便于接入与诊断；它存在不代表依赖、原生执行器或许可验证已完成。

## AI 客户端配置

安装成功后打开 `client-config.json`，将其中的 `MCP_CREO_MechDog` 服务添加到支持本地 stdio MCP 的客户端。示例格式：

```json
{
  "mcpServers": {
    "MCP_CREO_MechDog": {
      "command": "C:\\MCP_CREO_MechDog\\.venv\\Scripts\\python.exe",
      "args": ["C:\\MCP_CREO_MechDog\\server.py"]
    }
  }
}
```

以脚本生成的实际路径为准。客户端如果使用其他配置格式，保留相同的执行命令和参数。stdio 客户端会启动本地子进程，因此不需要手动长期运行 `server.py`；不要将 GitHub 仓库 URL 填成 MCP 服务地址。[官方 MCP Python SDK 本地主机说明](https://py.sdk.modelcontextprotocol.io/get-started/real-host/)

启动客户端中的 MCP 服务，后台自动复用已有会话或启动配置的 Creo。处理启动时出现的登录、许可及其他模态对话框，然后让 AI：

1. 调用 `creo_capabilities`，确认当前版本为 `0.2.5`，81 个工具可用；查看 `families`、`seed_library` 和 `unavailable_operations`。直接混合及已有零件追加已开放，受范围限制；见 [版本说明](RELEASE_NOTES_0.2.5.md)。
2. 调用 `creo_check_environment`，确认 SDK、模板和编译器路径正确。
3. 调用 `creo_startup_status` 等待 `state == "ready"`，再调用 `creo_session_status` 确认 `connected == true`。等待时建模请求明确拒绝，未创建任务。
4. 提交一个新零件建模计划；只提交一次，使用 `creo_get_job` 查询任务进度。
5. 确认任务 `status == "succeeded"`，修改结果包含 `saved_file_reloaded_and_verified == true`。

可以使用提示词：

> 用 MCP_CREO_MechDog 新建毫米零件：在 XY 面画一个直径 20 mm 的圆，拉伸 30 mm，保留原生草图和拉伸特征。先检查环境和 Creo 会话，再提交一次计划并查询到完成，最后报告原生 PRT 文件及保存重载验证结果。

连接成功证明当前连接路径可用；实际特征成功仍需建模验证。PTC 对 Toolkit 许可及编译应用解锁的要求独立于本项目 MIT 许可。[PTC Toolkit 解锁说明](https://support.ptc.com/help/creo_toolkit/protoolkit_pma/r12/usascii/creo_toolkit/user_guide/Unlocking_a_Creo_Toolkit_Application.html)

## 常见问题

### MCP 自动启动 Creo（FEAT-019）

`config.json` 可设置以下选项，重跑安装会保留已有值：

| 选项 | 缺省值 | 作用 |
| --- | --- | --- |
| `auto_start_creo` | `true` | 自动检测、复用；确认没有目标会话时启动 Creo。`false` 时由使用者手动打开 |
| `creo_startup_timeout_seconds` | `120` | 原生准备完成后的连接等待，整数 10～600 秒 |
| `creo_startup_psf` | `null` | 使用安装内 `Parametric/bin/parametric.psf`；可指定绝对 `.psf` 路径 |

后台初始化不会等待 Creo 启动完成才响应 MCP 握手。`creo_startup_status` 返回 `checking`、`building_worker`、`starting`、`waiting_for_connection` 或终态；只有实际 Toolkit 连接成功才返回 `ready`。原生准备另有 180 秒等待上限及构建子进程超时。等待或失败时建模入口拒绝入队，历史任务查询和能力查询仍可用。

服务通过现有 Explorer 的 `ShellExecute` 启动配置安装内的 `parametric.exe`，PSF 经 Windows 参数编码单独传入，支持含空格路径，不拼接 `cmd.exe` 命令。自动启动需要同一用户、同一 Windows 会话中可访问的 Explorer 桌面。Creo 作为独立桌面程序保留，关闭 MCP 客户端不会主动关闭它。GUI 继承 Explorer 的桌面环境，并使用自身 PSF；原生 worker 所需的 Windows 环境变量会从当前用户环境补齐，许可值不进入诊断。没有可用桌面时可手动启动 Creo，再请求重新检测。

同一用户会话、安装和 PSF 的多个服务共享 `%LOCALAPPDATA%/MCP_CREO_MechDog/startup/<目标摘要>/` 下的锁、`state.json` 和 `startup.log`。启动预留先于实际拉起写入；先前结果不确定且当前没有进程时，需要显式调用 `creo_startup_status(retry=true)`。重试会复查实际进程，正在启动或已有 Creo 时继续等待，不重复创建。日志不包含许可或敏感会话 ID。冷启动时先依据进程检查拉起 GUI，再进行真实 Toolkit 探测，避免首次探测创建的名称服务随 MCP 主机退出而被清理。Explorer 启动接口不提供子进程退出码；请求异常记录为失败，无就绪确认则有界超时，不将启动请求返回当作成功。

`timeout` 时先处理 Creo 对话框或检查启动环境，再请求重试。`selection_required` 时核对安装和 `creo_session_id`：多会话不随机选择，失效的指定 ID 不会被替换为其他实例。开关关闭后，手动打开 Creo，再调用 `creo_startup_status(retry=true)` 或 `creo_session_status` 重新检测。工具不会自动关闭会话或恢复失联任务；后者仍属 BUG-001 的独立范围。

| 现象 | 处理 |
| --- | --- |
| 找不到 Python 或运行的是商店占位程序 | 安装 Python 3.12+ x64，使用 `-Python` 指定实际 `python.exe` |
| 缺少 Toolkit 头文件或库 | 给对应 Creo 安装补装匹配的 Toolkit SDK |
| 找不到 `vcvars64.bat` | 安装 C++ Build Tools 及 Windows SDK，使用 `-VcVars64` 指定位置 |
| 依赖下载失败 | 检查访问 PyPI 的网络，再运行安装脚本 |
| 原生编译失败 | 查看 `build/generate_constants.log` 和 `build/build.log`；编译前检查 `cl.exe`、`link.exe`、UCRT 的 `stdio.h`、Windows SDK 的 `windows.h` 及 x64 库 |
| `vcvars64` 成功但缺少 `stdio.h` / SDK 库 | Windows SDK 可能未安装，或注册表 / `reg.exe` 探测被客户端策略拦截。由管理员修复安装或允许必要探测；也可将经审核的本机编译环境包装脚本传给 `-VcVars64`。安装器不会修改全局安全策略 |
| 文件检查通过但 Toolkit 连接失败 | 确认只打开一个 Creo 会话，处理模态对话框，再核查当前 PTC 许可；检查 `license_diagnostics`，路径拼写错误可能导致许可文件不存在 |
| 客户端发现工具但调用报缺少 `config.json` | 在同一源码目录完成 `setup.ps1`，核查客户端 command/args |
| 参数变化后版本不匹配 | 查询最新模型 revision；修改现有零件时提供 `expected_revision` |
| Creo 路径长度错误 | 将源码放入较短路径，并重新安装及生成客户端配置 |

模型保存在 `models/` 或任务输出目录，任务记录位于 `jobs/`。迁移电脑或移动项目目录后重新运行安装脚本并更新客户端配置；已有模型与记录需要一起保留。`.venv/` 不应从另一台电脑直接复制。

许可诊断仅返回状态，不返回许可值、服务器名或文件位置。环境变量 `PTC_D_LICENSE_FILE` 未设置，或其中所有本地路径都不存在时，子进程会尝试使用 `parametric.psf` 的有效路径或服务器配置；不改系统环境变量。有效文件、目录、`端口@服务器` 及仍含有效项的列表保持原配置。文件存在或服务器字符串可解析仍不证明能取得 Toolkit 许可，需要实际建模验证。

## 从 0.2.0 升级到 0.21

停止 MCP 客户端中的服务并等待正在运行的建模任务结束。保留项目内 `config.json`、`models/`、`jobs/`，用 0.21 的公开源码更新代码及文档，重新运行安装脚本，再重启客户端服务。模型类型未记录的旧模型按零件处理；原有底板接口仍保留。

0.21 是预发布候选版；放样仍未完成，不能作为支持所有 Creo 操作的稳定版。完整边界见 [COVERAGE_0.21.md](COVERAGE_0.21.md)。


## 升级到 0.2.5

升级流程同上，保留本机配置、模型和任务目录，等待原生任务完成后更新代码并重跑 `setup.ps1`。不必手动删除 `native/constants.inc`；构建会自动更新。新接口及限制见 [版本说明](RELEASE_NOTES_0.2.5.md)。更新源码后重启客户端中的 MCP 服务，调用 `creo_capabilities` 确认 `version == "0.2.5"`。只打开一个 Creo 会话；高级配置 `creo_session_id` 可固定 Toolkit 连接目标，重启会话后需重新取得有效 ID，程序拒绝连接回退。重跑安装保留已有 ID，不会自动猜测新的连接目标。

包含本次建模增量的源码内附 MIT 种子库，安装器验证并注册，`creo_new_loft_part` 按数量/模式自动选择，不要求手填路径和特征 ID。库内有九个原生 PRT：2/3/4/6 截面的直线和平滑，以及 5 截面平滑；详细步骤见 [SEED_LIBRARY.md](SEED_LIBRARY.md)。新电脑需要重新安装并验证，不直接复制旧 `.venv`、二进制、配置或会话 ID；同机换客户端可以共用安装目录，见 [MIGRATION.md](MIGRATION.md)。
