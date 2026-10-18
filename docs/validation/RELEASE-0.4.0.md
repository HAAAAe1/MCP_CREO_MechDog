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

- 合入 main 提交：见合入后回填。
- v0.4.0 标签指向：见合入后回填。
- Release 链接：见发布后回填。
- 源码包 SHA256：见发布后回填。
- 种子包 SHA256：`6abf1ae8dbb6e53566f47731f971981e5df0f53c9d96478f00449ccdbf0409f5`（24 文件，9 枚种子身份不变，仅清单版本标记；与 seeds.py expected_digest 一致）。
