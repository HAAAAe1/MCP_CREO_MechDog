# DEV-002 第二批 WorkBuddy 黑盒验收

日期：2026-10-15（Asia/Shanghai）。范围：DEV-002 第二批迁移完成后，WorkBuddy 对 E 盘开发副本的首次黑盒验收。不含 Creo 10 验收、不含并发验收、不替代 [DEV-002-batch2.md](DEV-002-batch2.md) 的开发者离线与本机 Creo 12 回归证据。

验收方式：只通过已连接的 MCP 工具调用，不读取、分析或修改源码，不执行仓库单元测试、开发检查或本地探针脚本。环境、会话与工具身份全部取自 MCP 公开返回。

## 运行身份核对（creo_capabilities）

| 字段 | 实际返回 |
| --- | --- |
| name / version | MCP_CREO_MechDog / 0.3.1（pre-release 候选；最新公开 0.3.0，提示“无需降级”） |
| python_executable | `E:\Projects\MCP_CREO_MechDog\.venv\Scripts\python.exe` |
| server_entry | `E:\Projects\MCP_CREO_MechDog\server.py` |
| code_root / resource_root / data_root | `E:\Projects\MCP_CREO_MechDog` |
| python_package_root | `E:\Projects\MCP_CREO_MechDog\src\creo_mechdog` |
| tool_count / enabled_tool_count | 82 / 82，disabled_tools_hidden=true，unavailable_tools=[] |
| unit / angle_unit | mm / degrees |
| evidence_directory | `E:\Projects\MCP_CREO_MechDog\build` |
| source_changed_since_startup | false |

启动时源码指纹覆盖本批迁移的三个包内实现与三个根包装：`src/creo_mechdog/{schema,profile_checks,airfoil}.py` 与根 `{schema,profile_checks,airfoil}.py`，另有 `server.py`、`bridge.py`、`creo_startup.py`、`src/creo_mechdog/{__init__,paths,references,update_check,blend_callback}.py`、`version.py`、`generic_bridge.py`、`native/worker.cpp`。

结论：受测实例的解释器、服务入口、代码根、包根、资源与数据根全部指向 E 盘开发副本，且启动指纹包含本批迁移实现。C 盘正式部署同样标称 0.3.1，因此版本号不构成连接对象的判别依据，本轮以路径与指纹为准。原始 capabilities 载荷 98 741 字符，本次只做字段核对，未逐字归档。

## 环境与会话

- `creo_check_environment`：`creo_root=C:\Program Files\PTC\Creo 12.4.0.0`；`parametric.exe`、Toolkit 头文件与 `ptasyncmd.lib / protkmd_NU.lib / protk_dllmd_NU.lib / ucore.lib / udata.lib`、`pro_comm_msg.exe`、公制零件/装配模板全部 `exists=true`，`ready_to_build=true`；`compiler_setup=C:\MCP_CREO_MechDog\vcvars64_local.cmd`（仅原生构建使用，本轮未触发）；`license_setting_present=true`、`license_usable=unverified_here`；`transport=stdio`；`complete_creo_coverage=false`。
- `creo_session_status`：`connected=true`、`connection_state=connected`、`toolkit_code=0`、`release_numeric=44`、`worker_exit_code=0`、`feature_creation_license=requires_actual_modeling_test`；连接时当前模型 `▩D2_AIRFOIL_61500F70001`（开发者本机回归遗留模型）。
- `creo_startup_status`：`state=ready`、`message="Toolkit connection verified; modeling is available"`、`auto_start_enabled=true`、`selected_session_configured=false`、`launched_by_coordinator=false`。即复用已存在的桌面会话，服务没有自行启动 Creo。
- `creo_list_seeds`：9 个种子全部 `available=true` 且 `actual_sha256` 与清单一致（2/3/4/6 截面的 straight+smooth、5 截面 smooth）；库目录 `E:\Projects\MCP_CREO_MechDog\seed_library`。

## 黑盒建模场景

全部成功写作业均返回 `success=true`、`toolkit_code=0`、`saved_file_reloaded_and_verified=true`，`rollback_succeeded=false`（成功路径未触发回滚，符合既有 BUG-012 语义歧义记录）。

| # | 工具与输入 | job_id / model_id | revision | 关键结果 |
| --- | --- | --- | --- | --- |
| 1 | new_part `wb_accept_circle` | f35d096029da48da8131f3a400b686e7 / 78f753c6c03b4e969c84c7c7baaa34e4 | 1 | 空件，has_solid=false，4 特征 |
| 2 | create_sketch XY 圆 R25（显式命名尺寸 `d_outer_r`） | 121f8242c94640f8817cd655296c92b5 | 2 | sketch 特征 id 40 |
| 3 | extrude depth=20 add | 67d5dcf78a2b40f2ae3cb8067c84a6c6 | 3 | volume 39269.90816987242 mm³ |
| 4 | set_sketch_dimensions `d_outer_r` 25→30 | 68f3a26e043c42d488f21113003bd4dd | 4 | volume 56548.66776461628 mm³ |
| 5 | inspect section=sketch_dimensions | — | 4 | feature_id 40 / id 2 / type 3 / value 30.0 |
| 6 | save_model | 7026ee17733c4ffc90e0a0be8521ed9d | 5 | 保存并重载验证 true |
| 7 | export STL | 8d535a1a55e7468a9dddbe256ba478a9 | 4（不变） | 只读任务，saved_reloaded=false |
| 8 | new_airfoil_blade 3 截面 smooth，pivot_fraction=0.4 | 836979cb41e14cdeb45d5e8d50a07f5a / 3a2f6711cbe448499c84cc40eb9e4701 | 1 | 三截面全部 succeeded；loft_seed 特征 ID 71（three_smooth）；volume 7660.186835279178 mm³ |
| 9 | set_airfoil_parameters sec2 chord 30→36 | 5f7e895f6c6e4983b93bccc13666d26d | 2 | volume 9785.15236573262 mm³ |
| 10 | set_airfoil_parameters sec3 twist 20°→30° | bf417696609947b6ac51f9891a08ebc8 | 3 | volume 9780.27586539833 mm³ |
| 11 | inspect section=features | — | 3 | `WB_BLADE` 特征 ID 仍为 71；截面草绘 ID 96/106/116 稳定 |
| 12 | export STL | e176247b25de46d9a5954ae12a05b4c0 | 3（不变） | 只读任务 |
| 13 | new_loft_part 两矩形、straight（自动选种子） | 6fe7ba7589f04113a88549f6679781b5 / 5b701fbd24e3492089ee57670f1d3c40 | 1 | loft_seed 特征 ID 60（two_straight）；volume 48000.0 mm³ |
| 14 | export STL | d297bd8382f94233af042a3db97759d2 | 1（不变） | 只读任务 |

体积解析对照：

- 场景 3：π×25²×20 = 39269.90816987242，与返回逐位一致。
- 场景 4：π×30²×20 = 56548.66776461628，与返回逐位一致；且草绘尺寸段读回 30.0，证明命名尺寸写入原生草绘并驱动下游拉伸重生成。
- 场景 13：800 mm²×60 mm = 48000.0，与返回逐位一致；自动选中的种子截面数与插值（2 / straight）与请求匹配。
- 场景 8~10：翼型为连续参数编辑，中间截面 ID 与 loft 特征 ID 在两次编辑后保持不变，revision 逐次 +1。

## 负例与保护行为

| 场景 | 实际返回 | 判定 |
| --- | --- | --- |
| 开放轮廓：new_loft_part 第二截面用 `closed:false` 的 polyline | 入参阶段拒绝：`Section sec2: Profile is open or branched near [-15.0, -8.0]; connect endpoints within 0.0001 mm`；响应无 job_id / model_id | 拒绝成立且未入队；随后 list_models 前 5 条无 `wb_reject_open`，确认未创建模型或作业 |
| 过期 revision：set_sketch_dimensions `expected_revision=1`（实际 5） | `Stale revision: current model revision is 5`；无作业 | 并发保护成立；随后 inspect 仍为 revision 5、体积不变，模型未被改动 |
| 执行器占用：保存作业运行中提交放样 STL 导出 | `Creo Toolkit is busy with another task; query its job and try later` | 明确拒绝，未自动重试、未静默入队；等保存作业终态 succeeded 后对同一模型重试导出成功 |

第 3 项是一次真实的 busy 拒绝，但本轮没有实施任何并行提交，不构成并发验收，也不代替 [DEV-002-batch2.md](DEV-002-batch2.md) 保留的并发与锁释放边界。

## 产出物核对（MCP 导出的 STL，文件级）

对 MCP 导出的 STL 做三角面与边界框解析，用于确认导出内容与 Creo 中的实体一致。

| 文件 | 面片 | X | Y | Z | 判定 |
| --- | --- | --- | --- | --- | --- |
| `wb_accept_circle.stl` | 220 | [-29.9996, 29.9996] | [-30.0000, 30.0000] | [0.0000, 20.0000] | R30×20 圆柱，吻合；±30 处的微小差异为圆弧离散弦差 |
| `wb_accept_loft.stl` | 12 | [-20.0000, 20.0000] | [-10.0000, 10.0000] | [0.0000, 60.0000] | 矩形棱柱，与 800×60=48000 mm³ 自洽 |
| `wb_accept_airfoil.stl` | 4940 | [-16.0381, 24.0874] | [-4.2063, 6.0200] | [0.0000, 100.0000] | 三截面跨 0/50/100 mm |

翼型型线核对（pivot_fraction=0.4）：

| 截面 | 请求弦长 / 扭转 | 实测 X 范围 | 与理论 NACA 0012 最大最近距离 | 容差 |
| --- | --- | --- | --- | --- |
| z=0 | 40 mm / 0° | [-16.0000, 24.0000]（理论 -16.0000 / 24.0000） | 0.024441 mm | 0.15 mm，通过 |
| z=100 | 20 mm / 30° | [-6.9567, 10.4031]（理论 -6.9282 / 10.3923） | 0.029145 mm | 0.15 mm，通过 |

z=50 中间截面未被三角化平面精确采样（最近环位于 z=50.405），属平滑 Blend 按曲率离散的正常表现，不是截面丢失；截面数与插值已由 `creo_list_seeds` 的种子匹配与特征创建结果确认。

## 未验证与边界

- 构建身份：MCP 只提供启动时源码指纹与 `source_changed_since_startup=false`，不提供 Git 提交、dirty 状态或编译期 MSVC 版本，这些项目记“无法确认”。
- 原生构建：`ready_to_build=true` 仅是 SDK/模板/编译器脚本存在；本轮未编译、未调用原生构建。
- 许可：`feature_creation_license=requires_actual_modeling_test`，本轮实体创建成功可作为许可可用性的实际证据，但不覆盖全部特征族与参数分支。
- Creo 10：本轮环境为 Creo 12.4.0.0（release_numeric=44），不代替 Creo 10 的独立验收。
- 并发：未实施并行提交，busy 拒绝只作单次现象记录。
- 宿主连接：普通 Codex 宿主的 -38 与 stdio 启动 configuration_error 在本轮未复现也未修复，沿用既有 BUG-005 诊断路径；本轮使用已存在的桌面会话。
- 保存重载以服务返回的 `saved_file_reloaded_and_verified` 为准，未独立重新打开 `.prt` 文件核对。
- 本轮未运行仓库单元测试、开发检查或任何本地源码探针；结论只覆盖 MCP 可见行为。
- 未修改 C 盘正式部署、连接器配置或用户已有模型；新增测试模型与产物全部位于 E 盘的 `models\` 与 `jobs\`。未提交，未合并 main。

## 与本批迁移模块的对应

本轮黑盒场景覆盖的迁移实现：草绘显式尺寸建立与编辑（`schema` 校验 + 原生草绘尺寸写入路径）、翼型创建与连续参数编辑（`airfoil`）、轮廓合法性拒绝（`profile_checks` 的闭合/分支检查）。旧入口 106 个导出与包内对象身份一致的结论来自开发者离线证据，本轮不重复验证。

DEV-002 第二批维持验收中；Creo 10 与并发边界仍待独立处理。
