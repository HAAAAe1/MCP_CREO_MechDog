# 0.4.0 发布候选与主干交付核对

日期：2026-10-18（Asia/Shanghai）。版本类型：MINOR（新增公开工具，84→85）。条目：0.3.7 / Creo 13 反馈五项闭环（BUG-067/068/069/070、FEAT-042）+ DEV-042/BUG-019 + FEAT-029 指引与 readiness 语义。工作区在发版准备提交后保持干净，受测源码即合入 main 的提交。

## 本轮变更清单

- 代码（详见 [RELEASE_NOTES_0.4.0.md](../RELEASE_NOTES_0.4.0.md)）：native（generic.cpp adopt_native/报错透传、worker.cpp 探针名修复、callback_runtime.h readiness 拆分、sketch_coordinates.cpp、geometry.cpp）；Python（adoption.py 新模块、bridge/generic_bridge/adoption 命名规范化、blend_callback 指引、server.py 85 工具）；测试（test_adoption 9、test_model_naming 6、test_blend_callback +1、test_validation 同步）。
- 文档：README 版本段与一次性回调设置小节、RELEASE_NOTES_0.4.0、RELEASING/INSTALL 版本行、BACKLOG 归档 5 卡、任务卡 8 张、验证记录 6 份、SKETCH_STABILITY/COMPATIBILITY 增补。
- 种子链：manifests `compatible_server_version` → 0.4.0；种子包重建；seeds.py expected_digest 同步（9 枚种子身份不变，仅清单版本标记）。

## 检查与实机证据

- `tools/dev_check.py`：success=true、unit passed（合入前最终跑记录见下）。
- 实机（Windows x64 / Creo 12.4.0.0 / 匹配 SDK）：`tools/test_general.py` GENERAL_CORE_SUCCESS=1；`tools/test_sketch_stability.py` PUBLIC_COORDINATES_PASS（8 用例）；FEAT-042 `tools/test_adoption.py --current` ADOPTION_INTEGRATION_SUCCESS（inspect 身份、apply 保存重载 verified、原件 sha256 不变、接管后编辑、重复接管拒绝）；BUG-069 `001`/`PRTXYZ` 创建与碰撞拒绝实测；BUG-070 探针/MCP 双层干净名；FEAT-029 `creo_callback_status` 实测 not_loaded+新指引。
- 未测范围见 [RELEASE_NOTES_0.4.0.md](../RELEASE_NOTES_0.4.0.md) 已知问题节（Creo 13 外部环境、FEAT-042 未保存修改/sheetmetal、FEAT-029 生命周期矩阵、BUG-057/058 开放等）。

## 附件与发布

- 合入 main 提交：`7fc3537`（fast-forward 自 `codex/bug-067-creo13-feedback`，f56a4cf..7fc3537，远端已推送；分支含 BUG-067/068+050、BUG-069+070、FEAT-042、FEAT-029 指引及 DEV-042/0.3.5 反馈补录 7 个开发提交 + 本发版准备提交）。
- v0.4.0 标签指向：`7fc3537`（远端 `git ls-remote` 核对 main 与 tag 同指）。
- Release 链接：https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.4.0（Pre-release 非草稿，id 416473340）。
- 源码包 SHA256：`a06de4ad87d1a90e75f5ae6fd43424158f57a78843bba89af87a30e08b54ec23`（617 文件；包内核对 seeds.py 指纹/version.py 0.4.0/README 标题/adoption.py 齐备；远端下载核对一致）。
- 种子包 SHA256：`6abf1ae8dbb6e53566f47731f971981e5df0f53c9d96478f00449ccdbf0409f5`（24 文件，9 枚种子身份不变，仅清单版本标记；与 seeds.py expected_digest 一致，远端下载核对一致）。
- 合入后本回填段按惯例留待下次开发提交入库（0.3.7 先例）；本次随交付即时提交并入 main，不改变标签所指源码与附件（仅文档回填）。
