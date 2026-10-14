# v0.2.6 种子库发布说明

本版含九个项目原创 MIT 原生混合种子：2/3/4/6 截面的直线和平滑，以及 5 截面的平滑。数量、模式、原生特征 ID 和 SHA256 在 `seed_manifest.json`，验收摘要在 `validation/`。

建议 Release 附件：

- MCP_CREO_MechDog-0.2.6-source.zip
- MCP_CREO_MechDog-0.2.6-source.zip.sha256
- MCP_CREO_MechDog-0.2.6-seed-library.zip
- MCP_CREO_MechDog-0.2.6-seed-library.zip.sha256

源码包已内附全部种子，独立种子包便于迁移。仓库根目录必须同步更新完整 `seed_library/`，包括原生 PRT、清单、验证和 MIT 许可证。旧 v0.2.4 的独立种子附件只有三个，保留为历史附件，不能代替新版完整库。

目标机需要自备 Creo、匹配 Toolkit SDK、编译器、Python 和可用许可。安装器验证/注册随包库，不从网络自动下载。使用 `creo_list_seeds` 确认九个文件均通过哈希检查；截面数量与模式须匹配请求。

v0.2.6 合并开发规范、登记写入修复和自动启动能力，完整 Creo 覆盖仍未完成。建议保持 Pre-release；本地打包不会自动上传 GitHub。迁移说明见 [README_迁移说明.md](README_迁移说明.md)。
