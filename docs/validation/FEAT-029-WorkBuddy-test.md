# FEAT-029 WorkBuddy 最终 MCP 验收场景（提示词留档）

此文保留黑盒验收提示词，不是通过报告。当前部署的独立核心场景已执行，结果见[WorkBuddy 报告](FEAT-029-WorkBuddy-report-2026-10-16.md)与[关闭核对](FEAT-029-closure-2026-10-16.md)，其他阶段按实际覆盖保留未验证。测试发起者负责部署固定安装版本、首次/必要的 GUI 注册、手动启动、安全提示和正常重启；注册入口固定为 `E:\Projects\MCP_CREO_MechDog_Test\build\blend_callback_protk.dat`。各阶段由发起者提供升级前后真实构建及人工操作记录；WorkBuddy 不读取源码、Git、配置文件或日志，不执行本地脚本，不代办部署或安全确认。

当前固定测试安装已由发起者完成持久配置，正常重启后主条目自动出现并已启动。接手当前阶段时直接查询状态，勿要求再次注册 dat；若不是 ready，报告实际返回并等待处理。客户端安装配置文件位于固定测试目录的 `client-config.json`，由发起者配置客户端；WorkBuddy 本身不读取它。先确认公开工具包含 `creo_callback_status` 且 resource_root 为 `E:\Projects\MCP_CREO_MechDog_Test`。公开服务版本仍为 0.3.2 开发源码，版本号不能代替实际部署/加载身份。

当前阶段先执行下面第 1、3～8 项可观察的建模、保护和报告要求。第 2 项升级/重启/回退/并存阶段需要发起者准备对应状态后再做；开发者历史通过不能改写成 WorkBuddy 通过，未在本轮实施的阶段明确记未验证。无需为了接手当前已启动会话再次重复 GUI 注册。

给 WorkBuddy 的执行要求：

1. 只使用已连接的 MCP 工具。先查询 creo_capabilities、creo_startup_status、creo_session_status 和 creo_callback_status，记录公开服务/部署/加载身份、checked_at、readiness、reason、instruction、注册路径。接口缺少的身份记“无法确认”，不从版本号推测已部署修复。会话未连接时报告真实返回并等待发起者处理，不继续建模或自动 retry。
2. 按发起者准备的阶段分别查预检：未初始化、正式注册并手动启动、DLL 未变升级、真实不同 DLL 升级但旧模块仍加载、正常重启并启动同一入口、明确不兼容部署、回退、两个安装并存。逐阶段记录是否重选/修改注册、手动启动、重启次数及其证据来源，不能从文件路径不变推断免注册成功。仅临时注册与持久注册分开报告。
3. ready 要有实时加载身份并与当前部署一致。prepared 不代表就绪；繁忙、不可达、超时及缺少可靠记录应为 unknown 并有下一步，GUI 注册状态未知应如实保留。旧会话记录不能使新会话自动报 ready。两个安装的 resource_root、命令及模块不得串用。没有真实并行调用就报告“并发未验证”。
4. ready 后串行验证两个入口。通过 creo_execute_plan 新建两张独立 XY 圆草图，标签 sk_a/sk_b，Z=0/25，半径 10/6；等待保存重载成功后，用返回的 model_id 和最新 expected_revision 调 creo_loft，sections=["sk_a","sk_b"]、label=blend_probe、interpolation=straight。成功应为原生 Blend，体积约 5131.26800086 mm³（容差 max(0.01,预期值×1e-6)），revision 只推进一次，saved_file_reloaded_and_verified=true。再用新模型的一次计划完成同样草图和 op=loft。所有输入均使用公开工具所列参数形状。
5. 补两/三截面 straight/smooth、已有底座追加及种子对照。三截面采用 Z=0/12.5/25、半径 10/8/6；smooth 不沿用 straight 的体积公式。对照实际模式/截面数、原有特征身份与几何、revision、保存重载；新建种子工具用其公开自动选择能力，不虚填 seed ID。
6. 验证重复截面/非法模式/stale revision 拒绝，模型与 revision 保持；再用创建后必然失败的断言验证真实回滚和后续独立小件。若回调预检拒绝发生在模型变更前，应记录 model_unchanged，不能描述成已执行回滚。新件、已有件、两个放样入口的失败分别报告。
7. 只提交一次，轮询 creo_get_job 终态；记录工具名、完整实际输入、job_id/model_id、终态、原始错误、原生参数/几何、保存重载、revision 和回滚。遇到 unknown_outcome 或提交/轮询传输结果不确定，立即停止新写操作并报告，不自动重提、清理任务或解除模型保护。
8. 每个场景标注“通过/失败/未验证/无法确认”及依据。未由发起者准备的升级/重启/回退/并存阶段、文件占用/预算/清理等内部机制均不得推测通过。报告注明实际公开环境；Creo 10 独立复测不作为本次门槛。
