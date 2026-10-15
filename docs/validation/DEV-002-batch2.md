# DEV-002 第二批：校验与建模辅助模块迁移

日期：2026-10-15（Asia/Shanghai）。代码迁移与离线验收已完成；真实 MCP、启动协调器/lifespan 与 Creo 验收后置，本批及整个 DEV-002 仍为开发中。服务版本保持 0.3.1，没有部署、合并 main 或发布。

## 实现结果

schema、profile_checks、airfoil 的业务实现依次迁入 src/creo_mechdog，根同名文件仅保留薄导出。旧入口的 106 个公开导出与包内对象逐一相同，包含 Pydantic 模型和 TypeAdapter；两种导入顺序均已验证。服务、桥接、测试及相关实机脚本使用包内导入，没有新增业务 sys.path 补丁。

服务源码身份清单同时覆盖三个包内实现和根包装；临时副本中分别修改每个包内实现，runtime 都报告 source_changed_since_startup=true，并保留启动时指纹。相关验收脚本的源码清单同步覆盖新实现。

pyproject.toml 同时安装三个根兼容模块。setup.ps1 原有 editable 安装步骤、源码打包器原有递归白名单已覆盖新增实现和嵌套测试，无需另建安装入口。安装器受控原生失败测试的源码夹具补齐根包装。代码、资源与任务/模型/构建数据的位置及后台入口不变，version.py 继续为唯一版本入口；原生源码无改动。

26 项纯校验/辅助回归迁入 tests/unit，涉及桥接保护、装配图和种子的混合用例保留原位置；36 个受影响原测试的方法体 AST 与格式整理提交一致。新增 8 项检查覆盖导出身份、仓库外导入及无写入/配置读取副作用、源码变更检测、分发内容、轮廓闭合容差/短边/构造几何。完整 discover 从 191 项变为 199 项，无原用例遗漏或重复执行。

## 源码与环境

- 起点：main 的 `515d50b8201829fd2a7e899a5295008305d30263`，dirty=true。起始未提交路径逐项保存在[结构化证据](DEV-002-batch2.json)；原有及开发期间新增的其他工作均保留，没有纳入本次代码提交。
- 分支：`codex/dev002-helpers`。代码受测提交 `fee6ce2ebc91004f32d8458319b0c750586f7a85`，dirty=true（文档及其他既有工作）；其后仅同步本批文档。源码集合 SHA256：`fb3c328272e477ed35fb73ef3ec5cfb2308b7faa8d72b0666a3f451e1214a5f0`。
- Windows 11 x64（10.0.26100）、Python 3.12.14、Pydantic 2.13.5、Ruff 0.17.0、clang-format 23.1.3。受测解释器为 E 盘开发虚拟环境和 E 盘解压副本的全新虚拟环境。
- 本轮不连接 Creo、不调用真实 Toolkit/SDK 编译，不以历史环境推断受测 Creo、SDK 或 MSVC 版本。安装器测试使用模拟 SDK 文件，并验证缺少编译器头文件时按预期失败；该结果不是原生构建成功。

实现内容与 `142fc9e` 的格式整理版本逐字节对比一致，仅 airfoil 的 schema 导入改为包内路径。结构化证据包含本次变更文件及服务 runtime 的逐文件 SHA256、命令、独立安装位置和后置用例清单。

提交分工：`142fc9e` 格式整理；`1f24951` 实现迁移及消费者/安装/身份清单；`19a6189` 单独审查安装配置指纹；`fee6ce2` 测试拆分及迁移回归。风格基线只更新 pyproject.toml 的审查后配置哈希，没有重建、扩充诊断或未格式化文件容许项。

主台账和 DEV-002 任务卡在起点已有未提交编辑，本次仅同步该条目的进展并保留在工作区，没有把这些既有编辑纳入本次提交；架构说明和本批新增证据独立提交。

## 本次离线验证

| 命令或场景 | 实际结果与边界 |
| --- | --- |
| 格式整理后运行五组受影响原 unittest | 36 项通过，再提交格式整理；没有先迁移再混入存量格式改动 |
| 开发虚拟环境 editable 重装，仓库外导入 | 实现来自本开发副本 src；旧/新类型相同，包优先和旧入口优先均通过；导入没有创建文件或读取 config.json/client-config.json |
| 迁移前后直接调用 `server.mcp.list_tools()` | 82 个工具完整定义（包括输入 schema、描述、注解等）一致；操作 JSON Schema 一致。此调用没有启动 MCP transport 或 lifespan，不计为真实协议验收 |
| 翼型与现有校验回归、实现内容对比 | 默认形状、厚度、pivot_fraction、旋转/平移、连续参数更新及轮廓拒绝语义保持；实现内容无业务改动 |
| `tools/dev_check.py --work-item DEV-002 --skip-unit` | 语言守卫通过，无新增诊断；检查 83 个 Python/15 个 C++ 文件，仍有 40 条存量 Ruff、29 个存量未格式化文件，不声明 strict 全通过 |
| `build/dev002-batch2/run_offline.py`（本机验收脚本） | discover 全部用例后排除 test_creo_startup 全模块及 test_total_deadline_and_lifespan_shutdown；其余 167 项全部通过，32 项后置；脚本额外阻止真实 session_status、launch_creo、CreoStartup.start |
| `tools/package.py --output build/DEV-002-batch2-source.zip` | 使用尚不存在的输出名，277 个白名单文件；包含三个实现/包装及嵌套测试，排除配置、任务/模型/构建、egg-info、SDK 和生成的原生二进制；随库许可和原生种子保留 |
| 新目录解压、全新 venv、在解压源码目录安装 requirements-dev.txt | 独立安装成功；从源码目录外导入实现、旧包装、唯一 version.py，全部实际位于解压副本，资源/数据根也指向解压副本 |
| 解压副本重复离线验收及语言检查 | 同一 167 项通过，同一 32 项后置；源码集合和全部 runtime 文件指纹与开发副本一致；解压副本 Git 身份为 null，没有借用父仓库提交身份 |

原始本机报告在 build/dev002-batch2 和解压副本 build/dev002-batch2；不提交日志、虚拟环境、测试模型或 ZIP。可长期复核的摘要和后置用例完整名称见[结构化证据](DEV-002-batch2.json)。全量、未过滤的 `tools/dev_check.py --work-item DEV-002` 没有运行，不能将语言检查和筛选后的单元结果表述为全量统一检查通过。

源码 ZIP SHA256：`3be2cfc5e7d095cf5ea06156aecefbcd9cc7f8b158e99a7cd3ce1fd3a19da820`。ZIP 捕获的是本次代码和状态同步前的文档快照，不包含随后编写的本验收摘要；独立验收源码与最终分支代码一致。

离线测试、独立安装和分发产物使用 E 盘 .tmp/build。首次开发包 editable 安装曾使用系统 Temp，随后已设置 E 盘 TEMP/TMP/PIP_CACHE_DIR 重跑；没有写入 C:\MCP_CREO_MechDog 正式部署、依赖、配置或连接器。WorkBuddy 的正式版验收证据单独记录。

## 后置范围

1. 32 项启动协调器/lifespan 用例，待隔离限制解除后执行未过滤的统一检查。
2. WorkBuddy 结束后，从 E 盘开发副本执行真实 stdio MCP 协议检查。tools/test_mcp.py 即使不传 --create，也会启动服务 lifespan/协调器并调用会话相关工具，当前未执行；标准输出仅含协议消息、真实入口与启动身份仍待确认。
3. Creo 12 的 tools/test_sketch_stability.py、tools/test_portable_modeling.py 及受影响原生回归：翼型/轮廓、参数与几何、保存重载 true、revision、负例恢复和回滚。当前未连接会话，也未取得这些成功结论。
4. Creo 10 由协助者单独验收；Creo 12、离线测试或历史记录均不替代它。本轮没有执行 WorkBuddy MCP 黑盒验收。

上述后置项完成前，第二批保持开发中，不宣称 DEV-002 整体完成。后续批次再迁移 seeds/capabilities 等剩余依赖及服务/启动/桥接实现。
