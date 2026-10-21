# 0.4.4 发布核对记录

日期：2026-10-21。版本类型：PATCH（无新增公开工具，工具数 87 不变）。

- 主干提交：`85bb793`（main，fast-forward 自 `codex/dev-027-030-improvement-plan` 的 `ea063a2` + 发版准备提交）；tag `v0.4.4` → `85bb793`，与本地/远端 main 核对一致。
- GitHub Release：[419092342](https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.4.4)（pre-release），说明取自 `docs/RELEASE_NOTES_0.4.4.md`。
- 附件（由 85bb793 工作区生成，解压抽查通过后上传，远端下载 SHA256 逐字节核对一致）：
  - `MCP_CREO_MechDog-0.4.4-source.zip`：684 文件，SHA256 `eed874c0cbe70314f1a2fc92bfe1e0cd34a5caf8a218d3953cb4f569ac1ff259`
  - `MCP_CREO_MechDog-0.4.4-seed-library.zip`：24 文件 / 9 种子，SHA256 `00b1bae07f4b751bce8138450ee2776bf18f09f66d4bf75bcef3fca5e83a0724`（`seeds.py` expected_digest 已同步）
- 验收摘要：469 项单元 + `tools/dev_check.py` 通过；实机构建链（0.4.3 缓存迁移复用/json.hpp 行尾双向零重建/内容变化重建/显式三键+额外键）、`tools/test_general.py` GENERAL_CORE_SUCCESS=1、FEAT-044 补验收（钣金/`.asm.N`/目视）、FEAT-023 补验收（过期/跨实例/篡改 cursor/87 条 13 页遍历）全过，见 [DEV-027-030-IMPROVEMENT-2026-10-21](DEV-027-030-IMPROVEMENT-2026-10-21.md)。
- 环境：本机 Windows x64 / Python 3.12 / Creo 12.4.0.0 / 匹配 SDK 与 MSVC。未测范围见版本说明（外部 Creo 10 受限环境、`asm_mx.asm.16` 原环境、显示失败注入/unknown/真实并发、DEV-027 二进制可复现性与目录回收）。
- 归档：第二份反馈原件按原字节入库并核对 blob SHA256 `92590f8c…cef17` 一致；`native/third_party/json.hpp` 保持 HEAD 字节零修改（`-text` 逐字节存储核对）。
