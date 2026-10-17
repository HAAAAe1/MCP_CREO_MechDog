# FEAT-029 开发记录（2026-10-16）

状态：开发中，候选实现已部署；实机生命周期和 WorkBuddy 未验收。基于 main@6a55119，在 `codex/feat-029-callback-lifecycle` 独立工作区开发，dirty=true。原 E 盘 BUG-008 工作区未迁移或覆盖。源码版本仍为 0.3.2 的未发布开发改动，未合入 main、未创建本项 Release。

## 固定安装与文件名

用户明确要求固定目录，并指定使用 `blend_callback_protk.dat`；反馈旧名称有多个点，Creo 导入无法识别。已按要求调整，不把尚未独立复现的文件名解析原因登记为已确认根因。

- 固定验收安装：`E:\Projects\MCP_CREO_MechDog_Test`。
- 唯一公开入口：`E:\Projects\MCP_CREO_MechDog_Test\build\blend_callback_protk.dat`。
- registry_file、registry_shortcut 和生成的 config.pro 片段均引用该名称；生成逻辑不再输出旧名称。仅本轮固定测试安装中的同内容旧文件移入 build/legacy_registration 保存，不对既有用户安装执行自动迁移或删除。
- 安装的 Python 包 resource_root 已实际核对为上述固定目录；其本机 client-config.json 已生成，未修改用户已有 MCP 客户端连接配置。开发 worktree 不再作为用户注册入口。

## 实现与保护

固定注册文件指向不可变引导模块；引导只在使用者手动启动时选择、校验和载入同一安装下的不可变回调载荷。Toolkit 只链接到已正式注册的引导，通过显式主机 API 表供载荷调用，不调用私有 Toolkit 初始化，也不在查询/建模时加载、卸载 DLL或改变安全策略。已加载旧模块不会被覆盖；停止后保留映像，下一次启动要求正常重启 Creo。

新公开 `creo_callback_status` 区分产物、服务、部署和实际会话身份。只有实时 nonce 应答及载荷/引导哈希、路径、协议 3、loader ABI 1、显式契约、命令和资源根目录全部匹配，才能报 ready。GUI 注册状态保持 unknown。连接/探测/断开 helper 预算 9 秒；繁忙、会话不可达、超时、旧记录及陈旧服务不误报就绪。

两个放样入口在模型变更前预检，不满足则返回 BLEND_CALLBACK_SETUP_REQUIRED。确认未开始修改时返回 model_unchanged，并保留受管模型的 ready/revision；不得冒称回滚成功。已经修改后的失败继续使用原检查点恢复和 unknown 保护。

## 本次验证

环境：Windows x64，Python 3.12.14，本机已安装 Creo 12.4.0.0 及匹配 SDK；MSVC 文件版本 19.44.35213.0。安装目录和 SDK 的版本不等于已连接会话的实际版本，本次未取得会话 release_numeric。

| 命令/检查 | 本次结果 | 证明范围 |
| --- | --- | --- |
| `python -m unittest tests.unit.test_blend_callback -q` | 16 项通过 | 产物不可变、升级/回退/代际、固定文件名与配置、未知/繁忙/超时/断连保护；使用夹具，不是 Creo 升级 |
| `python tools/dev_check.py --work-item FEAT-029` | 258 项 Windows 单元通过，无新增语言/格式问题 | 对应源码指纹见 JSON；存量风格基线未重建 |
| `python bridge.py build` | 开发工作区与固定验收安装 SDK 构建通过；固定目录后续构建复用 | worker、载荷和引导编译/缓存及文件准备，不证明 GUI 加载或几何成功 |
| `python -m tools.test_callback_lifecycle --phase baseline --no-startup --output build/feat029-public-fixed-name.json` | 真实 stdio 返回 83 个工具；resource_root/入口名称正确；readiness=unknown、reason=connection_failed、Toolkit=-4 | 开发观察进程关闭后台启动/更新，只读调用实际公开工具；不等于 WorkBuddy，不能把 -4 推断为许可根因 |
| `python tools/test_direct_loft.py --retry --expect-setup-required --work-item FEAT-029 --output build/feat029-not-loaded.json` | 较早尝试在连接基线停止，未创建模型/放样作业 | 当时源码身份保留在原报告，不能作为当前升级或拒绝保护的实机通过证据 |

机器可读的[开发摘要](FEAT-029-development-2026-10-16.json)、[开发检查](FEAT-029-development-check-2026-10-16.json)和[公开预检原始记录](FEAT-029-public-preflight-2026-10-16.json)分别保存结果、源码/产物身份和原始公开返回。部署源码来自工作分支的受控副本；固定验收目录没有 Git 元数据，不能伪造它的提交号。

## 未完成范围与下一步

用户需在 Creo 正式流程中注册固定入口、手动启动并自行确认安全提示；此前给出的临时 worktree 路径与旧文件名不再使用。确认后再运行真实预检、直接/计划放样与种子对照，并逐阶段验证真实不同 DLL 升级、持久注册/重启、旧模块、协议不兼容、回退、并存、失败保护和保存重载。当前没有任何新方案的原生建模成功，不把单元、编译和 prepared 算作生命周期完成。

WorkBuddy 交接按 [测试场景](FEAT-029-WorkBuddy-test.md)仅通过 MCP 观察；无法公开确认的内容记无法确认，未执行的阶段记未验证。原 Creo 10 来源保留，不要求独立 Creo 10 复测。候选升级说明见 [用户文档](../CALLBACK_LIFECYCLE.md)，完整范围继续以 [工作卡](../work-items/FEAT-029.md)及[台账](../BACKLOG.md)为准。
