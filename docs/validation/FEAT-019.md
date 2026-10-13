# FEAT-019 开发与实机验证记录

日期：2026-10-13。任务卡：[FEAT-019](../work-items/FEAT-019.md)。状态：已完成，用户接受 WorkBuddy / Creo 12.4 最终 MCP 验收。服务版本保持 0.2.5，无新标签或发布。

## 最终 MCP 验收

用户提供的 [WorkBuddy 原始报告](FEAT-019-WorkBuddy-report.md) 记录 22:31–22:39 的开发版 MCP 实测：运行身份为 E 盘开发目录、源码未漂移，协调器启动后 Toolkit ready / connected / code=0；新建→草图→拉伸→尺寸编辑→倒角→导出/检查链路通过。10000、20000、10000、9980 mm³ 的体积变化符合解析值，保存重载、过期 revision 拒绝及失败回滚有明确结果。报告的 O1～O3 观察保留原样，本次没有修改相关接口。

Codex 以 efc0292、dirty=false 的 E 盘开发版 stdio MCP 只读查询报告中的模型与 6 个修改任务：均 succeeded、保存重载验证 true；最终模型 revision=6、pending_job=null、体积 9980 mm³。详见 [结构化记录](FEAT-019.json) 的 acceptance 字段。WorkBuddy 原始报告没有提供 Git 提交号或完整六项指纹值，不能仅凭版本号补造其提交身份；本次 Codex 查询的公开路径与源码指纹另列。

[产物清单](FEAT-019-WorkBuddy-artifacts.json) 记录原报告及本地预览、STEP、XML 的 SHA256；原产物保留在 E:\Projects\workcreo\FEAT-019_artifacts，不提交二进制、日志或测试模型。完成范围是用户接受的 Creo 12.4 实验兼容，Creo 10 正式基线及真实跨客户端并发启动/退出后重连仍未验证。

本次 Codex 新一轮冷启动确实打开 GUI，但 Toolkit 探测超时并返回 configuration_error（TimeoutExpired），没有提交新模型。该失败独立登记为 [BUG-005](../work-items/BUG-005.md)，不改写 WorkBuddy 成功记录，也不宣称本次 Codex 新建模通过。

## 已实现的行为

MCP lifespan 在后台检测并复用已有 Creo；没有目标进程时，默认通过经用户/会话核对的 Explorer 桌面接口启动配置安装的 exe + PSF。多个服务共享启动锁和持久预留，失败结果不确定时需要显式重试。GUI、名称服务的生命周期与 stdio 主机清理分开；代码不自动关闭 Creo。只有真实 Toolkit 连接成功才进入 ready，其他状态拒绝建模入队。

配置为 auto_start_creo、creo_startup_timeout_seconds、creo_startup_psf；安装与公共状态工具说明见 [安装文档](../INSTALL.md#mcp-自动启动-creofeat-019)。会话只读查询可识别用户手动打开的实例，连接丢失时返回未就绪，不暗中启动替代实例。多会话或失效指定 ID 不随机回退。

格式提交 6a623e7、实现 a180ad9、基线缩减 5042d05、会话只读保护 4b18579。分支 codex/feat-019-creo-autostart 从 0702029 承接 BUG-002 与开发规范，远端 main 尚未包含这些依赖。

## 开发检查

Windows 11 x64、Python 3.12.14、匹配 Creo 12.4 SDK / MSVC x64。用户接受本机 Creo 12.4 实验环境；Creo 10 正式基线未执行。

| 检查 | 结果与范围 |
| --- | --- |
| python tools/dev_check.py --work-item FEAT-019 | 全部 119 项单元通过；71 条存量 Ruff、54 个存量未格式化文件，没有新增诊断；未宣称严格全库格式通过 |
| 新增启动回归 | 配置、就绪保护、手动复用、丢失连接只读处理、启动预留、超时、失效选择、桌面身份与资源释放、干净目录、跨进程协调 |
| 双进程协调重复 15 次 | 通过；真实 Python 进程/Windows 文件锁，Toolkit 与 GUI 为受控替身，不能作为原生启动证据 |
| python bridge.py build | 匹配 Creo 12.4 SDK 构建/缓存核对成功；构建不等于连接或建模成功 |
| 源码包从全新目录解压检查 | 118 项时点的单元和语言检查通过；首次曾暴露缺少 build 父目录，已修复并补回归；后续只读保护的 119 项最终包在全新目录再次通过 |
| 真实 MCP 初始化与入队保护 | 81 个工具，握手约 1.42 秒；未就绪的新建请求返回错误，任务列表不增加，既有 Creo 进程身份保留；最终结果见结构化证据 |

最终单元/语言检查的受测提交为 5042d05、dirty=true，规范化源码指纹 77bf6a8e493432dcd7c29aa1227d808e37a9078cc9c0e51f243c7530fff488f6；其源码内容已提交为 4b18579。逐文件指纹与命令保存在 [结构化证据](FEAT-019.json)，不只用 HEAD 代替受测内容。

## 实机结果与失败现场

早期实现确曾冷启动、取得 Toolkit 连接、协调两个 MCP 服务并复用同一实例；创建的 20×10×2 mm 草图拉伸零件体积 400 mm³，任务 a422bf88763843408ab0d4d88e1ed6e3 保存重载通过。参数修改任务 6654c693a32440019bc12e70adbe096c 在 ProMdlnameBackup 返回 -1 后失败并回滚，未通过保存重载。这是早期源码的部分证据，不能代表最终实现。

这一轮还观察到 stdio 客户端退出时清理 GUI 子进程，随后改为桌面启动。后续各轮均实际拉起 Creo，但 Toolkit 返回 -4，始终未进入 ready、没有提交建模。曾出现异常退出确认对话框，用户已处理；用户随后确认主窗口正常、没有对话框。

用户保存并正常退出，按平常方式手动启动后，默认 30 秒连接仍返回 -4；独立简单 SDK 探针也返回 -4。调用者与 Creo 的 Windows 用户登录、会话及权限级别相同。显式 PRO_DIRECTORY / PRO_MACHINE_TYPE 以及英文环境的对照未恢复连接。问题同时存在于手动会话中，根因尚未确认。当前手动会话保留，没有再次关闭或替换。

PTC 将 ProEngineerConnect 的 -4 定义为无法找到符合条件的会话或无法读取名称服务中的会话信息；不能仅凭这个值断言许可、版本或“没有进程”。[PTC API 说明](https://support.ptc.com/help/creo_toolkit/protoolkit_pma/r13/portuguese_br/creo_toolkit/488.html)

各轮本地原始报告保留在 build/FEAT-019-startup-*.json、build/FEAT-019-mcp-admission.json 和 build/FEAT-019-manual-baseline.json，报告名包含 pass 的历史文件也以 success 字段为准。公开摘要保留各轮源码指纹、报告 SHA256、任务和错误，不提交日志、二进制、许可或测试模型。

## 历史未完成项（WorkBuddy 最终验收前）

2026-10-13 后续补充：新增公开运行身份查询，真实 stdio MCP 返回 E:\Projects\MCP_CREO_MechDog\.venv\Scripts\python.exe 与同目录 server.py，初始化源码未发生变化；当前 Codex 挂载的旧接口没有 startup/runtime 字段。独立客户端验收一直明确启动开发目录，不以旧挂载接口作为 FEAT-019 验收对象。新增两项身份/源码变化回归后，121 项 Windows 单元和语言检查通过，受测提交 c839caa、dirty=true，源码总指纹 159d0391cb8119357778bc55c022a1961a2b7fb9a4b28249016f3e110c11b5bf。

再次以零 Creo 进程开始开发版冷启动，GUI 已自动出现，Toolkit 未就绪并有界超时，没有提交建模任务。该轮结束后安装版及开发版分别探测，同样返回 -4。本次新增身份查询及 [WorkBuddy 提示词](FEAT-019-WorkBuddy.md) 可以消除客户端版本混淆，但尚未修复实机连接故障。未保留未经稳定验证的桌面任务转发改动；当前只通过桌面启动 GUI，原生任务执行路径保持此前实现。

最终源码的冷启动后就绪、已有会话成功复用、全部客户端断开后重新连接、原生草图/拉伸、参数修改和保存重载尚未通过。配置开关、失效 ID、多会话、失败路径的当前证据主要为受控单元测试，不冒充所有实机场景通过。Creo 10 及 WorkBuddy 最终 MCP 黑盒验收未执行。

下一步先恢复可用的 Toolkit 连接基线，再运行 tools/test_creo_startup.py；另一台匹配 SDK/许可的机器可直接获取本分支重新构建。最终 WorkBuddy 验收只调用公开 MCP 工具，使用 [专用提示词](FEAT-019-WorkBuddy.md)，不检查源码或运行本地脚本。完整闭环成功后再关闭任务卡；FEAT-001、FEAT-002、BUG-001 保持独立范围。
