# 常驻回调的固定注册、升级与预检（FEAT-029 功能分支）

日期：2026-10-17集成。原独立分支2026-10-16已按本机开发者生命周期与WorkBuddy核心场景通过，详见[原关闭记录](validation/FEAT-029-closure-2026-10-16.md)。当前E盘集成只完成离线/SDK编译验证，实机因卡死限制未复跑，见[本次记录](validation/FEAT-029-integration-2026-10-17.md)。此功能尚未发布，不属于公开0.3.3；本机只启用MCP_CREO_MechDog_dev，下述_Test路径属于历史证据，不能当成当前部署身份。

## 固定安装入口

保持同一个安装目录，注册入口始终是 `<安装目录>\build\blend_callback_protk.dat`。本轮验收固定使用 `E:\Projects\MCP_CREO_MechDog_Test\build\blend_callback_protk.dat`。不要把 `.codex\worktrees` 临时目录作为长期安装位置，也不要每次升级重新解压到另一个目录后声称原注册仍适用。

1. 使用该安装的 Python 和服务，构建后查询 `creo_capabilities.direct_blend_callback`，核对 resource_root 与上述固定目录一致。
2. 首次在 Creo“辅助应用程序”中选择 `registry_file`，手动启动并自行处理 DLL 提示。不要直接注册 `module_file` 回调载荷。
3. 要跨 Creo 重启保留注册入口，将生成的 `build/blend_callback.config.pro` 中的 `protkdat <绝对注册文件路径>` 合入实际加载的 `config.pro`。片段本身不会被 Creo 自动读取。桌面启动时可查看快捷方式的“起始位置”；MCP 自动启动的起始目录为 `<安装目录>\build\creo_session`。若两种方式使用不同目录，应分别配置，或使用两者都会读取的用户配置。文件名须为 `config.pro`。已有其他插件设置时保留它们，避免重复声明同一应用。服务只生成片段，不隐式修改配置。
4. 配置在 Creo 启动时读取。保存模型并正常退出整个 Creo，再按实际使用的方式打开，检查“辅助应用程序”条目是否自行出现；若消失，说明持久配置尚未生效，应核对实际加载目录，不能把再次选择 dat 算作免重复注册通过。注册文件采用 `delay_start true`，条目出现后仍需手动启动。引导模块在这时校验并载入本次部署选定的回调载荷；应先核对部署来源，再自行处理安全提示。`NEVER` 等安全策略仍由使用者或管理员处理。
5. 调用 `creo_callback_status`。只有 `readiness=ready` 才提交直接放样。所有查询结果都是带 checked_at 的瞬时观察，其他操作可能随后改变会话。

PTC 的[注册说明](https://support.ptc.com/help/creo_toolkit/protoolkit_pma/r13/usascii/creo_toolkit/user_guide/Registering_a_Creo_Toolkit_Application.html)列明配置项与注册文件搜索位置；这支持持久配置的流程，但不能代替本机实际重启验证。不能由一次 GUI 临时注册推断跨重启持久性。

本机补验发现：Creo 12.4 默认快捷方式从 `C:\Users\Public\Documents` 启动，原先该目录没有 `config.pro`，使用者确认重启后条目消失。已在该目录及固定测试安装的 MCP 启动目录各创建一次配置，均引用同一个 `blend_callback_protk.dat`。使用者从原快捷方式重开后确认主条目自动出现，再手动启动，实时预检和直接/计划放样通过；MCP 自动启动目录目前仅完成配置准备。配置加载顺序见 PTC [配置文件说明](https://support.ptc.com/help/creo/creo_pma/r12/usascii/configuration_options/About_Configuration_Files.html)，本轮观察见[实机记录](validation/FEAT-029-live-2026-10-16.md)。

## 升级与回退

正常升级：等待已知任务结束，停止旧 MCP 服务，在同一固定安装目录更新源码与构建产物，保留配置、models、jobs 和 build 中的旧回调/引导副本。重启 MCP，查询预检。旧模块仍加载时会报告版本不匹配；完成已知任务后正常重启 Creo，手动启动同一注册入口，再查预检和做一次保存重载建模验证。MCP 不自行重启 Creo、卸载模块或清除任务。

回调载荷变化不会修改已发布 DLL，也不改变公开注册文件路径。引导模块、SDK 或主机 API 代际变化时会保留新的不可变引导副本，并更新相同注册文件的内容。持久配置应在下一次 Creo 启动重新读取该文件；仅有会话内临时注册时，可能仍需人工重选相同路径。原协议 2 的旧注册需迁入固定入口一次。这些分支须分别记录“重新注册”“手动启动”“重启 Creo”，不能合称免操作升级。

回退时恢复旧源码及对应构建，再准备同一安装目录的产物；正常重启 Creo并手动启动，预检须与回退版本一致。保留旧 DLL 本身不代表已成功回退。安装 A/B 各自保留 resource_root、命令和注册入口，不能把 A 的就绪外推给 B；多安装并存不等于并发验收。

升级准备不是跨所有元数据文件的事务。若准备失败，保留旧副本和错误，重新运行对应版本的构建准备并核对部署选择、注册文件与预检，恢复一致后再启动；不能删除未知任务或修改 loaded 字段来“修复”状态。

## 公开状态

| 字段/状态 | 含义与操作 |
| --- | --- |
| artifact_status=prepared | 当前部署的 DLL、引导、元数据已通过文件校验；不说明 Creo 加载情况 |
| readiness=ready | 当前选定会话实时回应随机 nonce，完整匹配载荷/引导哈希、路径、协议、契约、命令和资源根目录；没有活动中的回调请求 |
| not_loaded | 曾记录的应用标识在本次可连接会话中不活动；注册状态仍未知，已登记则启动，未登记则注册 |
| version_mismatch | 当前可验证模块与部署不一致，或 worker/部署契约不一致；按 reason、next_action 和 instruction 处理 |
| unknown | 没有可靠初始化记录、实时应答失败、繁忙、无法连接、探测超时或服务源码已变；不能推断未注册，更不能报就绪 |
| registration_status=unknown | MCP 不读取 GUI 的注册清单，不证明配置文件已被 Creo 加载 |
| service / deployed / loaded | 分别为启动时服务源码身份、磁盘部署身份和实时会话身份；三者不能混用 |

`creo_callback_status` 不构建、不启动 Creo、不加载或卸载 DLL、不修改模型。原生连接/查询/断开 helper 预算为 9 秒；繁忙立即返回占用信息，启动协调器运行时直接返回其快照。超时只停止本次只读 helper，不终止 Creo。不复用磁盘旧记录作为实时应答。

两个直接放样入口在模型加载/变更前预检，并在使用回调前再次核对；预检拒绝用 `BLEND_CALLBACK_SETUP_REQUIRED` 返回原因，`model_unchanged=true` 表示没有开始修改，不能当成回滚已执行。真正修改后的失败仍走原检查点恢复。`unknown_outcome` 必须先核对任务和模型，禁止自动重提。

## 实现边界

注册文件指向不可变引导模块，引导只在使用者启动应用时读取 deployment.json，并按 SHA256 派生、校验同一安装下的载荷路径。Toolkit 只链接到正式注册的引导模块；载荷通过显式主机 API 表使用 Toolkit，不创建另一个未经注册的 Toolkit 运行时。模型查询和建模没有加载路径。为防残留命令指针失效，停止应用后不释放载荷映像，再次启动要求正常重启 Creo。

兼容判定包含实际模块及引导哈希、loader ABI、显式选择契约、协议、命令、模块路径与安装资源根目录；不以相同协议号宣称兼容，也不在会话里静默热切换。本机首次启动、真实不同 DLL 升级、持久注册/重启、部署回退、并存、失败保护和直接/计划/种子建模有开发者实机证据；WorkBuddy 独立验证当前部署核心场景。独立生命周期复跑、真实引导/SDK 变化、旧协议迁移及其他环境等未测范围见[关闭记录](validation/FEAT-029-closure-2026-10-16.md)，离线测试不代替这些实机结果。
