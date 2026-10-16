# DEV-002 第二批：校验与建模辅助模块迁移

日期：2026-10-15（Asia/Shanghai）。第二批已完成：代码迁移、199 项完整开发检查、真实 MCP 契约、本机 Creo 12 开发者回归及随后 WorkBuddy 已测场景通过；用户已取消 Creo 10 独立验收门槛，见文末状态同步及 [DEV-018](../work-items/DEV-018.md)。DEV-002 整体继续为开发中。服务版本保持 0.3.1，没有部署、合并 main 或发布。下文离线与后置阶段的待验收描述保留其当时状态，不作为当前要求。

## 实现结果

schema、profile_checks、airfoil 的业务实现依次迁入 src/creo_mechdog，根同名文件仅保留薄导出。旧入口的 106 个公开导出与包内对象逐一相同，包含 Pydantic 模型和 TypeAdapter；两种导入顺序均已验证。服务、桥接、测试及相关实机脚本使用包内导入，没有新增业务 sys.path 补丁。

服务源码身份清单同时覆盖三个包内实现和根包装；临时副本中分别修改每个包内实现，runtime 都报告 source_changed_since_startup=true，并保留启动时指纹。相关验收脚本的源码清单同步覆盖新实现。

pyproject.toml 同时安装三个根兼容模块。setup.ps1 原有 editable 安装步骤、源码打包器原有递归白名单已覆盖新增实现和嵌套测试，无需另建安装入口。安装器受控原生失败测试的源码夹具补齐根包装。代码、资源与任务/模型/构建数据的位置及后台入口不变，version.py 继续为唯一版本入口；原生源码无改动。

26 项纯校验/辅助回归迁入 tests/unit，涉及桥接保护、装配图和种子的混合用例保留原位置；36 个受影响原测试的方法体 AST 与格式整理提交一致。新增 8 项检查覆盖导出身份、仓库外导入及无写入/配置读取副作用、源码变更检测、分发内容、轮廓闭合容差/短边/构造几何。完整 discover 从 191 项变为 199 项，无原用例遗漏或重复执行。

## 源码与环境

- 起点：main 的 `515d50b8201829fd2a7e899a5295008305d30263`，dirty=true。起始未提交路径逐项保存在[结构化证据](DEV-002-batch2.json)；原有及开发期间新增的其他工作均保留，没有纳入本次代码提交。
- 分支：`codex/dev002-helpers`。代码受测提交 `fee6ce2ebc91004f32d8458319b0c750586f7a85`，dirty=true（文档及其他既有工作）；其后仅同步本批文档。源码集合 SHA256：`fb3c328272e477ed35fb73ef3ec5cfb2308b7faa8d72b0666a3f451e1214a5f0`。
- Windows 11 x64（10.0.26100）、Python 3.12.14、Pydantic 2.13.5、Ruff 0.17.0、clang-format 23.1.3。受测解释器为 E 盘开发虚拟环境和 E 盘解压副本的全新虚拟环境。
- 初始离线阶段不连接 Creo、不调用真实 Toolkit/SDK 编译，不以历史环境推断受测 Creo、SDK 或 MSVC 版本。安装器测试使用模拟 SDK 文件，并验证缺少编译器头文件时按预期失败；该结果不是原生构建成功。用户确认正式版测试结束后的实机结果另列于下文。

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

## 离线结束时的后置范围

1. 32 项启动协调器/lifespan 用例，待隔离限制解除后执行未过滤的统一检查。
2. WorkBuddy 结束后，从 E 盘开发副本执行真实 stdio MCP 协议检查。tools/test_mcp.py 即使不传 --create，也会启动服务 lifespan/协调器并调用会话相关工具，当前未执行；标准输出仅含协议消息、真实入口与启动身份仍待确认。
3. Creo 12 的 tools/test_sketch_stability.py、tools/test_portable_modeling.py 及受影响原生回归：翼型/轮廓、参数与几何、保存重载 true、revision、负例恢复和回滚。当前未连接会话，也未取得这些成功结论。
4. Creo 10 由协助者单独验收；Creo 12、离线测试或历史记录均不替代它。本轮没有执行 WorkBuddy MCP 黑盒验收。

以上为初始离线阶段记录；其中完整开发检查、真实协议及本机 Creo 12 回归已按下文补验，WorkBuddy 和 Creo 10 仍待完成。后续批次再迁移 seeds/capabilities 等剩余依赖及服务/启动/桥接实现。

## 2026-10-15 后置补验

用户确认 C 盘 WorkBuddy 正式版测试已经结束后执行。受测提交 `d6c193ee0813b4b3f1f70addce9cd02f0c56745e`，dirty=true；Python/原生源码均未再修改，统一源码指纹仍为 `fb3c328272e477ed35fb73ef3ec5cfb2308b7faa8d72b0666a3f451e1214a5f0`。本段为开发者验收，不冒充 WorkBuddy 黑盒结果。逐项输入、24 个 job_id/model_id、终态、revision 和文件指纹见结构化证据的 post_acceptance。

| 验证 | 结果 |
| --- | --- |
| `tools/dev_check.py --work-item DEV-002` | 未过滤的完整检查通过，199 项单元全部成功，含此前后置的 32 项；无新增语言问题 |
| 真实 legacy stdio initialize / tools/list / capabilities | 82 个完整工具定义与迁移前基线一致；服务、解释器、包、资源和数据均核对为 E 盘副本，源码未漂移；捕获的 11 条 stdout 均为 JSON-RPC，诊断写 stderr |
| Creo 12.4 / release_numeric=44 | 通过现有 Explorer 隐藏启动开发者脚本，实时 session_status 返回 connected=true、Toolkit code=0，随后 startup_status=ready 才提交建模 |
| 六组草绘 | 创建、原生尺寸编辑、几何/体积及 STL 边界验证全部通过；大轮廓和 XY 胶囊还通过几何替换及两次预期失败的恢复检查 |
| 五截面翼型 | 非默认 pivot_fraction=0.4，创建、连续两次参数编辑、原特征 ID 保持、revision 递增、保存重载及 STL 截面通过；最大偏差 0.04784164 mm，小于 0.15 mm |
| 作业与恢复 | 24 个已接受作业：22 成功、2 预期失败；17 次成功模型修改均保存重载 true，5 次只读导出/refresh 保持 revision；两个负例的回滚标志、原保存文件哈希及实时恢复均通过 |
| 开放轮廓 | 公开 new_loft_part 拒绝 open/branched 轮廓，未创建 job；原始输入和错误单独补录 |

| 草绘场景 | 初始/尺寸编辑 revision | 已测边界最大偏差 mm |
| --- | --- | --- |
| report19 大轮廓 | 1 / 2（几何替换后 3） | 0.002093 |
| polygon12 | 1 / 2 | 0.000376 |
| capsule_xy | 1 / 2（几何替换后 3） | 0.000482 |
| capsule_xz（30°） | 1 / 2 | 0.002054 |
| circle_yz | 1 / 2 | 0.002107 |
| rectangle_coordinates | 1 / 2 | 0 |

两个失败作业的顶层响应没有 revision 字段，结构化证据保留 null；通过随后 refresh 的 revision=3 确认保持，未把推测值填成接口返回。导出和 refresh 是只读任务，保存重载 false 不作模型修改失败判定；17 次模型修改的成功判定均要求 true。

环境补录：Creo 12.4.0.0 及同目录 Toolkit SDK；构建日志确认 MSVC 14.44.35207，MSVC/UCRT/Windows SDK 预检通过。本机缓存曾在预检中重新构建，原生源码无改动；日志中的既有 C4244 警告保留，执行器/DLL 和构建源指纹见 JSON。C 盘正式部署、连接器及用户已有模型未改动，新增 7 个测试模型和产物均在 E 盘。

补验边界：普通 Codex 宿主的直接 worker 状态仍返回 -38；普通 stdio 曾出现 startup configuration_error（TimeoutExpired）及 session_status 工具错误。桌面路径也观察到启动器超时，但后续实时 session_status 成功，并将公开启动状态更新为 ready。本次依既有 [BUG-005](../work-items/BUG-005.md) 桌面诊断路径取得几何证据，没有交付宿主连接或启动超时修复，也没有把历史 WorkBuddy 成功视为本次连接成功。

原 `tools/test_mcp.py` 在 building_worker 阶段立即断言 connected，实际失败，未记为通过。旧草绘/翼型脚本依赖默认全量 get_job 和三个种子，本批专用脚本保留其几何断言，显式读取 full 终态并适配现有九个种子；所有调用仍经过真实 MCP。首次测试脚本将只读导出误作修改，修正后按原 job_id 继续，已完成作业未重复提交。另保留 1 次明确未入队的 busy 拒绝及稍后重试，关联 BUG-009；未重试 unknown_outcome、未清 pending_job、未改调度/恢复逻辑，没有实施或声称并发验收。

本机开发验收已完成。下一步让 WorkBuddy 的测试连接指向 E:\Projects\MCP_CREO_MechDog，先用 MCP capabilities 核对运行身份，再做黑盒验收；不以同为 0.3.1 的版本号证明新代码已连接。Creo 10 仍由协助者独立验收，第二批保持验收中，整个 DEV-002 继续开发中。

## 2026-10-15 WorkBuddy 结果与验收范围调整

用户提交 [E 盘开发副本的 WorkBuddy 黑盒报告](DEV-002-batch2-WorkBuddy-acceptance-20261015.md)，运行路径、包根与迁移模块启动指纹均已核对；Creo 12.4 下草绘尺寸驱动、三截面翼型连续编辑、两截面种子放样和导出等已测场景通过。报告列出 12 个成功作业，9 个写作业均保存重载 true，3 个只读导出保持 revision。DEV-018 文档整理时只读核对这 12 个现存 job.json，终态、写/只读分类、revision 和重载标志与报告一致；这次核对不计作新的 MCP 或 WorkBuddy 测试。

随后用户要求取消整个项目的 Creo 10 独立验收要求，朋友有具体测试问题再反馈。此前外部 Creo 10 复测安排至此取消，历史未测事实保留。第二批按本机开发与 WorkBuddy 已测范围完成，不新增并发或宿主连接修复门槛；BUG-009、BUG-005 及其他缺陷继续独立跟踪。DEV-002 整体仍开发中，未部署 C 盘、未合并 main 或发布。

原 WorkBuddy 报告保持原文：圆柱导出实际在显式保存前执行，revision 4/5 不表示倒退；查询前 5 个模型不能单独证明全部模型/作业均未创建，开放轮廓证据限于公开拒绝及响应无 ID；中间翼型截面的几何精度没有直接采样验证。以上限制不扩大本批或其他条目的通过范围。
