# 0.2.6 发布验收

日期：2026-10-14。工作条目：[DEV-011](../work-items/DEV-011.md)。

合并范围：DEV-001、DEV-010、BUG-002、FEAT-019。三个远端分支依次叠加，最新受纳入提交 d0f841a。版本命名由用户指定。

完整命令、报告摘要、源码与二进制指纹见 [结构化证据](RELEASE-0.2.6.json)。环境为 Windows 11 x64（10.0.26100）、Python 3.12.14、Creo 12.4.0.0 / 匹配 SDK / VS 2022 x64。

## 本轮结果

| 命令 / 核对 | 结果 |
| --- | --- |
| .venv/Scripts/python.exe tools/dev_check.py --work-item DEV-011 | 121 项 Windows 单元测试全部通过；70 条存量 Ruff、52 个存量未格式化文件，无新增诊断；未宣称全库严格格式通过 |
| .venv/Scripts/python.exe bridge.py build | 匹配 Creo 12.4 SDK 的 worker / Blend DLL 构建与缓存核对成功 |
| tools/test_creo_startup.py --output build/release-0.2.6/startup.json | 无 Creo 进程开始；先前启动预留未确认，返回 timeout，要求显式重试；失败，无原生任务 |
| tools/test_creo_startup.py --retry --output build/release-0.2.6/startup-retry.json | 确认无 Creo 进程后显式重试，进入 waiting_for_connection，原始日志报告 TimeoutExpired / configuration_error；success=false，jobs=[]，未取得 Toolkit 就绪或建模成功 |
| 本轮独立 stdio MCP 协议核对 | 0.2.6、81 个工具、九个有效种子、开发目录身份和 source_changed_since_startup=false 通过；会话返回 connected=false / building_worker，未作为原生连接通过 |
| tools/package.py / tools/package_seeds.py | 白名单、许可、模板、两份 0.2.6 清单及九个 PRT SHA256 通过；独立 ZIP 实际安装到空目录后九个种子全部有效 |
| 从全新目录解压候选源码并运行其 tools/dev_check.py | 121 项单元与语言守卫通过；解压源码指纹与对应候选一致 |
| 解压源码 setup.ps1 -CheckOnly -CreoRoot <本机 Creo 12.4> -Python <本机 Python> | Python、SDK、MSVC 文件前置检查通过；未执行完整全新安装与建模 |

最终开发检查受测提交 3fa635f1219218d247ca8c6b35af67675d8aec7c，dirty=false，规范化检查源码 SHA256 为 0317ba4787af1844ca0c5ac13d24873a12c50222bf39dd9dfdce5f2d585c6b8f。后续证据与台账归档仅修改文档，运行源码指纹保留。首次检查因 version.py 格式失败；修复 LF 格式并单独移除已解决基线项后复测通过，未扩充任何容许项。

## 复用证据与未测范围

server.py、bridge.py、generic_bridge.py、creo_startup.py、校验/能力/翼型模块及原生 C++ 与 d0f841a 逐文件核对规范化内容一致；seeds.py 仅格式整理、版本文案及独立 ZIP 发布摘要更新，version.py 仅版本和格式更新。历史 [BUG-002](BUG-002.md) / [FEAT-019](FEAT-019.md) 实机验收可作为实现未变的既有证据，保持 2026-10-13 原日期、原环境与原统计，不能代替本轮连接或全量回归。

Creo 10 不在本机，未完成正式基线回归。BUG-005 保留；本轮未取得原生几何、尺寸编辑、保存擦除重载及回滚的新成功证据。general、guards、登记并发原生、Blend、曲面、UDF、工程图、钣金和装配等原生套件没有在 Toolkit 未就绪时继续执行。真实多客户端并发启动、全部客户端退出后的成功重连、全新完整安装后建模、全部参数分支仍未验证。

结论：源码、协议、单元与分发验证通过；本轮原生启动验收失败，保持明确限制的 0.2.6 Pre-release，不能称为 Creo 10 完整验收或已修复 BUG-005。

## 附件摘要

九种子 ZIP：9928ed610478ec8fffcc78a8e7925b7f980464276a207a69aa635cfa3a8d1de6。

源码 ZIP 包含本证据，最终源码 SHA256 在 Release 正文和 .zip.sha256 附件记录，避免在 ZIP 内嵌自身摘要的循环依赖。旧标签与旧附件不覆盖。
