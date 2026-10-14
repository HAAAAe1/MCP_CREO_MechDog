# MCP_CREO_MechDog 0.2.6

发布日期：2026-10-14。MIT 源码预发布版本，标签 v0.2.6。

本版将 codex/development-standards、codex/bug-002-registry-write、codex/feat-019-creo-autostart 的全部 15 个提交合并到 main。版本号遵循用户指定的 0.2.6。

## 变更

- FEAT-019：MCP 后台检测并按需启动 Creo；共用启动锁和预留，真实 Toolkit 连接成功后才允许建模。新增 creo_startup_status，能力查询提供运行目录与源码身份。只读会话查询在连接丢失后返回未就绪。
- BUG-002：Windows 登记 JSON 使用共享读取、单步原子替换和有界重试，保留 revision、任务终态和回滚保护。
- DEV-001 / DEV-010：统一开发台账、风格基线守卫、Windows CI、发布规则和 WorkBuddy MCP 黑盒验收约定。
- DEV-011：同步服务版本、两份种子清单和独立种子 ZIP 安装摘要；源码包内附九个 MIT 原生混合种子。seeds.py 单独格式整理，并移除已解决的基线项。

## 验证与限制

兼容性说明补充（2026-10-14）：可使用 Creo 10 或 Creo 12。Creo 10 为正式验收基线；Creo 12 已验证可用，已有成功实机记录使用 12.4.0.0，包括自动启动与 Toolkit 就绪、零件/草图/拉伸、尺寸驱动、倒角、保存重载和导出，以及 BUG-002 的登记并发轮询与失败回滚。用户确认补充 Creo 12 可用性说明，具体已测功能与未测范围见 [兼容矩阵](COMPATIBILITY.md)。安装时使用目标 Creo 对应的 Toolkit SDK 重新构建。

本次命令、源码身份、包校验和及解压验证见 [发布验收](validation/RELEASE-0.2.6.md)。2026-10-13 的 [BUG-002](validation/BUG-002.md) 与 [FEAT-019](validation/FEAT-019.md) 实机证据保留原日期，不作为本轮重新测试。

本版发布验收环境为 Creo 12.4；该次冷启动复测失败，未完成 Creo 10 实机回归。此前 Creo 12.4 成功记录按原日期保留，不能将其视为该次发布回归通过。BUG-005（Codex 客户端/会话环境下冷启动后 Toolkit -4 或探测超时）仍待核实。真实多客户端并发启动、全部客户端退出后的成功重连、全部建模模块和参数分支未完成本版覆盖，故保持 Pre-release。

## 升级

等待已有任务完成，停止目标客户端的 MCP 服务，保留本机 config.json、client-config.json、models/ 和 jobs/。更新完整源码与随包 seed_library/，使用目标 Creo 的匹配 SDK 重新运行 setup.ps1，再重启 MCP 服务。核对 creo_capabilities.version 为 0.2.6、81 个可用工具、运行目录/源码身份，以及九个有效种子；目标机仍需实际建模与保存重载验证。

新版独立种子包与新版清单配套；旧独立 ZIP 不适用于新版 ZIP 安装入口。既有外置种子目录在保留原 PRT 的同时更新随 0.2.6 发布的 seed_manifest.json，再注册/验证。原生种子文件及其 SHA256 未变，历史验证未重标。

## 附件

- MCP_CREO_MechDog-0.2.6-source.zip 与 .zip.sha256
- MCP_CREO_MechDog-0.2.6-seed-library.zip 与 .zip.sha256

源码包已包含完整种子库；独立种子包供单独迁移。旧标签及旧附件保留原样。
