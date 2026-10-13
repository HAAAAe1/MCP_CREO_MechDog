# FEAT-019 开发与实机验证记录

日期：2026-10-13。任务卡：[FEAT-019](../work-items/FEAT-019.md)。状态：开发中，最终实机验收未完成。服务版本保持 0.2.5，无新标签或发布。

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

## 未完成项

最终源码的冷启动后就绪、已有会话成功复用、全部客户端断开后重新连接、原生草图/拉伸、参数修改和保存重载尚未通过。配置开关、失效 ID、多会话、失败路径的当前证据主要为受控单元测试，不冒充所有实机场景通过。Creo 10 及 WorkBuddy 最终 MCP 黑盒验收未执行。

下一步先恢复可用的 Toolkit 连接基线，再运行 tools/test_creo_startup.py；另一台匹配 SDK/许可的机器可直接获取本分支重新构建。最终 WorkBuddy 验收只调用公开 MCP 工具，使用 [专用提示词](FEAT-019-WorkBuddy.md)，不检查源码或运行本地脚本。完整闭环成功后再关闭任务卡；FEAT-001、FEAT-002、BUG-001 保持独立范围。
