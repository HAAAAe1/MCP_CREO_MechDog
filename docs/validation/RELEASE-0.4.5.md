# v0.4.5 发布核对记录

日期：2026-10-21。

- 版本与条目：0.4.5（PATCH）。BUG-076 首批可定位诊断、FEAT-006/008 空窗口结构化与预检全阶段诊断、FEAT-043/044 `opened_session_model`、FEAT-008/023 README 摘要接口一览；计划文件与两份 0.4.2 反馈原件归档入库。
- 主干提交：`9b7358d`（merge `codex/bug076-feedback042-firstbatch`：cb31acc 实施 + 15ef38f 隔离回归 + 2b7d3a3 定版）。受测源码即该提交（工作区除未跟踪的本机目录外无差异；`build/development_check.json` 记录检查时指纹，dirty 内容仅为 build/ 本机生成物）。
- 标签：`v0.4.5` → `9b7358d0703e3f05b4977245bb91aaa2e3b1e25a`（已推送）。
- Release：[v0.4.5](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.4.5)（id 419181692，正式发布非草稿），body 含版本说明、验收摘要、环境、未测范围与附件 SHA256。
- 附件与校验和（merge 后 main 工作区打包，远端下载复核一致）：
  - `MCP_CREO_MechDog-source-v0.4.5.zip`（693 文件）SHA256 `423fbcc1d9a25a761ca07a43a7a4cdf5d8bd44afa59656b84046fdce8c8d6573`；包内 version.py=0.4.5、seed_manifest compatible_server_version=0.4.5、seeds.py digest 与种子包一致。
  - `MCP_CREO_MechDog-seeds-v0.4.5.zip`（24 文件/9 种子）SHA256 `4edaf07af5dfc39ddebe57476296f4782134b0018d1576563e80261289ea88a1`（与 seeds.py `expected_digest` 回填一致，确定性打包复核）。
- 验收：481 项单元 + `tools/dev_check.py` 通过；实机 Creo 12.4（stdio 直连）空窗口结构化拒绝、open_file `opened_session_model` 两作业、正常 inspect 发布 evidence。详见 [BUG076-FEEDBACK042-2026-10-21](BUG076-FEEDBACK042-2026-10-21.md)。
- 环境：本机 Windows x64 / Python 3.12 / Creo 12.4.0.0 / 匹配 SDK 与 MSVC。
- 未测范围：BUG-076 原环境（Creo 10）证据未取得（条目保持开放）；16 MiB 实机文件未构造；装配/钣金收养；WorkBuddy 公开黑盒（建议发布后复核）。
