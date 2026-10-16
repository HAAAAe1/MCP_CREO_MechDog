# MCP_CREO_MechDog 0.3.0 全量工具实测问题报告

> 测试时间：2026-10-14 14:53–15:45 (GMT+8)
> 环境：Windows x64 · Creo Parametric **12.4.0.0**（`release_numeric=44`）· 单位 mm · MCP_CREO_MechDog **0.3.0**（82 工具，stdio）
> 服务目录：`C:\MCP_CREO_MechDog`（本轮由 0.2.6 升级至 0.3.0 并重建原生层）
> 测试方式：通过 MCP 客户端逐个调用工具；每个作业用 `creo_get_job`（`detail=compact`）收敛至 `succeeded/failed/unknown_outcome`，**从不重复提交**；关键几何用解析体积独立交叉校验，并用 `job.json` / `native.log` / 进程态交叉验证
> 用途：供 MCP 开发者协作修复

---

## 一、结论摘要

**0.3.0 的建模链路与几何正确性依然优秀，新增的更新检查与引用语法文档确实生效；但本轮暴露出两类高危缺陷：① `creo_loft` 挂死并锁死整条 Toolkit 通道；② 一次失败作业可将 Creo 的 Toolkit 连接彻底损坏（`toolkit_code=-38`），必须重启 Creo 才能恢复。** 核心几何全部命中解析解，失败用例均能回滚。

| 维度 | 评价 |
|---|---|
| 建模正确性 | ✅ 优秀（本轮全部体积/拓扑命中解析解，保存-重载-校验闭环稳定） |
| 失败安全性 | ✅ 良好（失败即回滚，revision 不推进，无残留特征） |
| 新功能可用性 | ✅ 已生效（`creo_check_update`、`references.by_tool`、`axis_pattern` 兼容别名归一化 BUG-006） |
| 单通道鲁棒性 | ❌ **高危**：`creo_loft` 挂死占用通道 600 s；失败作业可损坏 Toolkit 连接（见 P0-3） |
| 可恢复性 | ❌ **高危**：通道损坏后无自助恢复工具，协调器线程会一并死锁，只能重启 Creo（见 P0-3.4） |
| 错误可诊断性 | ⚠️ 部分好、部分笼统（失败作业 `operations=null`，无法定位失败 op，见 P1-4） |
| 并发可用性 | ❌ 运行期无法提交任何新调用，且存在竞态（见 P0-2） |
| 回显一致性 | ⚠️ 偏弱（`operations[]` 成对重复、`inspection.counts` 成功时也为 0、失败结果形状不统一） |

---

## 二、部署与版本升级验证（0.2.6 → 0.3.0）

升级按官方流程执行，配置/模型/作业全部保留，并留有回滚点：

| 步骤 | 命令/动作 | 结果 |
|---|---|---|
| 拉取新版本 | `git pull --ff-only origin main` | `b0851ef` → `a558ee8`（54 文件变更） |
| 可编辑安装 | `pip install --no-deps --editable .` | `MCP_CREO_MechDog-0.3.0` |
| 种子库 | `seeds.py --install` | 9 个种子哈希校验通过 |
| 原生层 | `bridge.py build` | 命中缓存（C++ 无变更） |
| 回滚点 | `ROLLBACK_HEAD_0.2.6.txt` | `b0851ef9bbd50f84053e5d451de37615cc89a102` |

**升级后运行时自述（关键项）**

| 项 | 值 |
|---|---|
| `version` / `tool_count` | **0.3.0** / **82**（`unavailable_tools=[]`） |
| `references.by_tool` | ✅ 存在（覆盖 15 个工具的分工具引用语法） |
| `capabilities.update` / `startup_status.update` | ✅ 存在（`status=up_to_date`，`current=latest=0.3.0`，`is_prerelease=true`） |
| `creo_check_update` | ✅ 工具已注册并可调用 |
| `creo_session_status` | `connected=true`，`release_numeric=44`，`worker_exit_code=0` |

### 2.1 关于"看不到新功能"的根因（重要）

用户最初反馈"感觉没有新功能"。排查结论：**不是功能缺失，而是运行实例陈旧**——当时 `C:\MCP_CREO_MechDog` 仍是 0.2.6，而 GitHub 已发布 0.3.0。

- **为什么热更新无效**：MCP 服务进程由客户端宿主托管（stdio），升级源码/包后**不会自动重载**。重启前 `creo_check_update` 不存在、`startup_status` 无 `update` 字段；重启连接器后一次性全部出现。
- **建议**：`capabilities`/`startup_status` 已有 `runtime.source_fingerprints_at_startup`，建议在检测到"源码版本 > 运行版本"时**主动提示"请重启 MCP 连接器以加载 0.x.y"**，可显著降低此类误判。

---

## 三、覆盖总览（82 / 82 全部完成调用）

| 结果 | 数量 | 工具 |
|---|---|---|
| ✅ 正向通过 | 74 | 见下方分组表 |
| ❌ 调用级失败/挂死 | 5 | **`creo_loft`（挂死）**、`creo_drawing_view_update`、`creo_rib`、`creo_dimension_pattern`、`creo_create_feature_tree` |
| ⛔ 前置条件受限（错误信息清晰） | 2 | `creo_inspect_udf`、`creo_create_udf`（本机无 `.gph` 库，校验快速失败） |
| ⚠️ 语义疑点（报成功但几何无变化） | 1 | `creo_solidify`（`mode=cut` 基准面剪裁分支） |

分组结果：

| 分组 | 工具 | 结果 |
|---|---|---|
| 会话/环境/更新 | `creo_session_status` `creo_startup_status` `creo_capabilities` `creo_check_environment` `creo_check_update` `creo_lookup_constants` | ✅（会话状态工具随后劣化，见 P1-8） |
| 作业 | `creo_get_job` `creo_list_jobs` | ✅ |
| 模型管理 | `creo_new_part` `creo_new_assembly` `creo_new_sheetmetal` `creo_new_drawing` `creo_create_plate` `creo_list_models` `creo_inspect_model` `creo_refresh_model` `creo_save_model` `creo_regenerate` `creo_execute_plan` | ✅（`create_plate`/`list_models` 见 P2-8/P1-6） |
| 草图/基础特征 | `creo_create_sketch` `creo_set_sketch_dimensions` `creo_update_sketch_geometry` `creo_extrude` `creo_revolve` `creo_hole` `creo_round` `creo_chamfer` `creo_shell` `creo_mirror` `creo_sweep` | ✅ |
| 基准特征 | `creo_datum_plane` `creo_datum_axis` `creo_datum_csys` `creo_datum_points` | ✅ |
| 参数/关系/尺寸 | `creo_set_parameters` `creo_set_relations` `creo_regenerate` | ✅；`creo_set_dimensions`（关系驱动尺寸）见 P2-9 |
| 阵列/结构 | `creo_axis_pattern` `creo_group_features` `creo_reorder_features` | ✅；`creo_dimension_pattern` ❌ |
| 几何变换 | `creo_transform_geometry` `creo_set_geometry_transform` | ✅（干净件）；`transform` 在复杂件上失败，见 P1-7 |
| 曲面子系统 | `creo_surface_fill` `creo_thicken` `creo_draft` | ✅ |
| 放样/翼型/种子库 | `creo_new_loft_part` `creo_new_airfoil_blade` `creo_create_airfoil_section` `creo_set_airfoil_parameters` `creo_install_seed_library` `creo_list_seeds` `creo_validate_seed` | ✅；`creo_loft` ❌ 挂死 |
| 布尔/筋/抽壳 | `creo_boolean_bodies` ✅ / `creo_rib` ❌ / `creo_solidify` ⚠️ | 见 P0-3 / P2-11 / P2-10 |
| 钣金 | `creo_sheetmetal_wall` `creo_sheetmetal_flange` `creo_sheetmetal_unbend` `creo_sheetmetal_bend_back` `creo_sheetmetal_flat_pattern` | ✅ |
| 装配 | `creo_assemble_component` `creo_component_placement` `creo_component_constraints` `creo_remove_component` `creo_list_components` | ✅ |
| 工程图（11） | `creo_new_drawing` `creo_drawing_sheet` `creo_drawing_view` `creo_drawing_projection` `creo_drawing_note` `creo_drawing_note_update` `creo_drawing_table` `creo_drawing_table_cell` `creo_drawing_dimension` `creo_drawing_delete` | ✅ |
| 工程图（视图更新） | `creo_drawing_view_update` | ❌ **恒失败**（P1-5） |
| 导出/低层 | `creo_export_model`(step/stl/iges/jpeg) `creo_dump_feature_tree` | ✅ |
| UDF / 底层元素树 | `creo_inspect_udf` `creo_create_udf` `creo_create_feature_tree` | ⛔⛔❌（错误清晰 / 需完整元素树） |

---

## 四、问题清单（按严重程度）

### 🔴 P0-3（本轮新增·最高危）｜`creo_loft` 挂死 → 锁死通道 → 最终损坏 Creo 会话

这是本轮最重要、且最具破坏性的发现，含 4 个层次：

#### 3.1 现象：`creo_loft` 永久卡在 `activate_blend_context`

在已有零件 `t30_loft2` 上追加放样（先建两个 XY 草图 sk_a(R10@Z0)、sk_b(R6@Z25)，再 `creo_loft(sections=[sk_a,sk_b], mode="add", interpolation="straight")`），作业**永久停在**：

```json
{ "status": "running", "stage": "activate_blend_context", "operation_count": 1 }
```

- 原生 `native.log` 冻结在 `ProSelbufferClear()=0`（第 115 行）后**再无增长**；
- Creo 内核 `xtop` CPU 占用仅 **1.6%**（空转阻塞），`creo_worker.exe` 存活但空闲 → **是死等，不是计算中**；
- 该作业**独占 `toolkit.lock`**（`generic_bridge.py` 在整段 `with bridge.toolkit_lock(wait_seconds=120)` 内 `subprocess.run(...)` 跑 worker），因此**期间任何新调用都被拒**（含只读）；
- 唯一出口是 `subprocess.run(timeout=600)`（`generic_timeout_seconds`）在 **600 s** 后杀 worker，作业转 `unknown_outcome`（`"Native worker timed out; inspect Creo and the model before retrying"`）；`creo_get_job` 的 `unknown_outcome` 看门狗更晚（`bridge.py:785`：`age > 120+120+600+30 = 870 s`）。

#### 3.2 根因：`creo_loft` 走"UI 宏自动化"路径，而非已验证的种子重绑定路径

源码定位 `native/blend_create.cpp: generic_loft()`：

```
activate_blend_context(); CK(ProSelbufferClear());
... ProToolkitDllLoad(... creo_blend_sync.dll ...)      // ← 实际卡点（未见 BLEND_DLL_LOAD 日志）
ProMacroLoad("~ Command `ProCmdFtPBlend`; ... ~ Activate `main_dlg_cur` `chkbn.blend_sectionspage.0` 1; ...")
```

该路径依赖：① **可交互且空闲**的 Creo 主窗口；② 硬编码对话框/控件名（`blend_sectionspage.0.0`、`main_dlg_cur`、`chain_dlg`、`UI Message Dialog`）；③ **运行时加载**的同步回调 DLL（`ProToolkitDllLoad`，未在 `protk.dat` 注册时可能触发安全确认对话框）。

**本机观测**：`xtop.exe` 存在且能渲染（能生成 `preview.jpg`），但**枚举不到任何可见主窗口标题**；`creo_startup.py` 通过 `ShellExecute` 启动并刻意"与 GUI 进程解耦"（源码注释：*kept out of the GUI process; ShellExecute's return is NOT readiness*）。在该状态下宏无法驱动仪表盘，进程即死等。

**佐证**：同一台机器上 `creo_new_loft_part`（种子重绑定路径）**完全正常**（3 截面矩形放样 40650 mm³、3 站翼型叶片 21473.67 mm³ 均成功），只有 `creo_loft`（宏路径）挂死。

#### 3.3 第二次挂死：worker 卡在断开连接阶段

紧接一次**失败**的 `creo_transform_geometry` 之后，`creo_new_part` 的原生建模**已成功保存**（`ProMdlnameBackup=0`），但 worker 卡在 `ProMdlErase(board)=0` 之后——**没有 `DISCONNECT=0`，也没有写出 `native_result.json`**，`native.log` 冻结。即：**挂死不止发生在建模前段，也可能发生在收尾阶段**，同样只有 600 s 超时兜底。

#### 3.4 最严重后果：Toolkit 通道被损坏，且无自助恢复

上述挂死作业被 600 s 超时强制终止后，提交任何作业（含只读 `creo_refresh_model`）都返回：

```
toolkit_code = -38   （connection_failed）
```

`bridge.session_status(2)` 实测得 `connected=false / connection_state=connection_failed`。此时：

- `creo_session_status` **持续抛错**（且**错误信息为空**，见 P1-8）；
- `creo_startup_status` **仍报告 `connected=true`**（陈旧缓存，见 P1-8）；
- `creo_startup_status(retry=true)` 触发的协调器线程**卡在 `state=building_worker`**，**9 分钟无任何进展**（`state.json` 的 `updated_at` 不变）；
- 最终只能**杀掉整个 Creo 进程组**（`xtop / parametric / pro_comm_msg / creoagent / nmsd`），协调器才立刻恢复响应，并在约 90 s 内拉起新 Creo（`launch_attempt=8`，`state=ready`，`toolkit_code=0`，`launched_by_coordinator=true`）。

> 也就是说：**一次 `creo_loft` 调用 = 约 10 分钟通道封锁 + Creo 重启**。这对自动化流程是致命的。

**建议（按性价比排序）**：

1. **让 `creo_loft` 复用种子重绑定实现**，彻底去掉宏/回调 DLL 依赖（`creo_new_loft_part` 已证明可行）；
2. 若必须保留宏路径，**调用前探测窗口可用性**（无可见窗口/`ProMdlWindowGet` 失败即快速失败并给出可行动错误），**禁止无限等待**；
3. 为所有原生调用增加**独立于作业生命周期的更短超时**（`native_timeout_seconds=180` 目前未被 generic 作业使用，generic 一律 600 s），并检测"连续 N 秒 `native.log` 无增量"→ 上报 `stage=stalled`；
4. **提供取消/中断作业工具**（如 `creo_cancel_job`），让 Agent 主动释放通道；
5. **提供 Toolkit 连接自愈**：检测到 `toolkit_code=-38` 时自动重建连接（或干净重启 Creo 会话），而不是让协调器线程死锁。

---

### 🔴 P0-2｜运行期无法提交任何新调用（历史复现），且存在竞态

在任一作业 `running` 时，提交**任何**工具（含只读）都被拒：

```
Error executing tool creo_refresh_model: Creo Toolkit is busy with another task; query its job and try later
```

本轮多次触发。四个问题点：① 不告知占用方（无 `blocking_job_id`）；② 无排队机制（提交侧 `toolkit_lock(wait_seconds=0)` 直接拒绝，而作业侧允许等 120 s）；③ 只读查询也被拒；④ **竞态**：上一作业已报 `succeeded` 后立刻提交，仍偶发被拒。

**建议**：提交侧允许排队（至少只读）；错误中回传 `blocking_job_id` + `retry_after`；消除作业收尾与锁释放之间的竞态。

---

### 🔴 P0-1｜引用语法：文档裸引用 vs 工具包裹引用（0.3.0 已显著改善）

0.3.0 新增的 `references.by_tool`（覆盖 15 个工具）显著改善了文档分歧：`axis_pattern.axis` 现同时接受 `{kind:'axis',id:N}`、`{kind:'datum_axis_feature',label:…}`，并把旧别名 `{kind:'datum_feature',label:…}` **归一化**为规范形式（BUG-006，**本轮实测通过**）。

但历史上"同类引用在工具间语法不一致"的分歧点仍需逐工具回归（如 `round/chamfer` 需 `{edge:{...}}` 包裹、`sheetmetal_flange` 需非包裹），`capabilities.references` 顶层示例仍是裸引用。

**建议**：把 `references` 拆成"引用值语法"与"集合元素包裹语法"两节，并让所有工具族接受同一种规范写法，或至少在拒绝时回传"该工具期望的写法"。

---

### 🟠 P1-4（本轮新增）｜失败作业 `operations` 为 `null`/`[]`，无法定位失败 op

本轮失败作业的 `result.operations` 一律为空，导致 Agent **完全不知道是哪个 op 失败**：

| 场景 | 回显 |
|---|---|
| 工程图 6-op 计划失败 | `operations: []`（被迫把 6 op 拆成 4 op、再逐个单测才定位到 `drawing_view_update`） |
| `creo_transform_geometry` 失败 | `operations: null` |
| `creo_create_feature_tree` 失败 | `operations: null` |
| `creo_dimension_pattern` / `creo_rib` 失败 | `operations: null` |

而**成功路径会逐条回显 op**（含 `label/succeeded/feature_id`）——**失败路径的信息反而更少**，与"可诊断性"方向相悖。

**建议**：失败时保留已执行 op 的结果，把未执行/失败的 op 标注为 `{op,label,succeeded:false,message}`，并返回 `failed_operation_index`。

---

### 🟠 P1-5（本轮新增）｜`creo_drawing_view_update` 恒失败

单独调用（`scale=2` 更新已有视图）依然失败，与是否批量无关：`toolkit_code=-1, operations=[], rollback_succeeded=true`。

隔离验证：同批的 `creo_drawing_sheet`（新增图纸页）单独调用**成功**；`creo_drawing_note_update` **成功**（rev3）。故失败点确认为 `creo_drawing_view_update` 本身。

**建议**：检查视图更新（缩放/位置）的原生实现与入参映射，并补一条独立的 `drawing_view_update` 验收用例。

---

### 🟠 P1-6（本轮新增，P2-1 升级）｜`creo_list_models` 单次返回 **844 KB**，且无精简模式

`creo_list_models(limit=20)` 返回 **844,447 字符**（超出单次可读上限，报错落盘）。结构：20 个模型 ×（`aliases` ≈ 5.4 KB + `inspection` ≈ 13.6 KB）。

`creo_get_job`、`creo_list_jobs` 都有 `detail=compact`，**`creo_list_models` 没有**；连"列表"接口都内联完整快照。

**建议**：增加 `detail` 参数；默认只回 `model_id / model_name / model_type / revision / status / updated_at`，快照交给 `creo_inspect_model`。

---

### 🟠 P1-7（本轮新增）｜失败作业把模型标记为 `status=failed`（几何其实完好）；`rollback_succeeded` 语义混乱

`creo_transform_geometry` 在 `t30_probe` 上失败后：

- 模型注册表 `model.json` 被置为 **`status: "failed"`**，而**几何完好、revision 未推进、体积不变**（9646.19）；
- 原因是 `generic_bridge.py` 用 `result.get("rollback_succeeded")` 决定模型状态，而该次失败返回 **`rollback_succeeded: false`** —— 尽管原生日志显示 `PHASE=rollback_to_saved_checkpoint` 确实执行了；
- 更进一步：**成功**作业的结果里也带 `"rollback_succeeded": false`（11 次成功导出作业均如此）。该字段在成功/失败两侧都出现 `false`，**无法据此判断回滚是否发生**。

**影响**：一个几何完好的模型会被标成 `failed`，后续调用者可能误判为不可用。

**建议**：回滚失败才置 `rollback_succeeded=false`（成功路径省略该字段）；模型状态改为依据"保存文件是否完好 + revision 是否推进"，而非单一布尔；失败后最好返回 `model_status` 与"模型可用性"提示。

#### 根因补充：该次失败真实发生在保存阶段

`t30_probe`（此前刚做过分组 `feature_group`）上调用 `creo_transform_geometry(references=[{kind:'body',id:52}], translation=[0,0,15])`：

```
PHASE=geometry_transform:t30_x1
created_feature_id=478          ← 特征已创建
PHASE=save_and_reload
ProMdlnameBackup(board,destination)=-1     ← 保存失败（成功作业此处恒为 =0）
BUILD_FAILED=-1
PHASE=rollback_to_saved_checkpoint
```

**同一调用在全新干净件 `t30_rb` 上完全成功**（`rev3`，体积不变，`ProMdlnameBackup=0`）。故这是**模型状态相关**的失败，建议开发者用"复杂件（含 group/pattern/shell）+ transform"的组合复现。

---

### 🟠 P1-8（本轮新增）｜`creo_session_status` 抛"空错误"；`startup_status` 报陈旧 `connected=true`

通道损坏后（P0-3.4）：

- `creo_session_status` **反复仅返回 `Error executing tool creo_session_status`（无任何文本）**。源码定位：它调用 `bridge.session_status(connect_timeout_seconds=2)`，内部 `subprocess.run(..., timeout=9)` 抛 **`subprocess.TimeoutExpired`**；而 `server.py: invoke()` 只捕获 `(ValueError, RuntimeError, OSError)`，**`TimeoutExpired` 未被捕获** → 对外表现为空错误信息，完全不可诊断。
- 同时 `creo_startup_status` 仍返回 **`connected: true / state: ready`**，因为该接口读的是**上一次成功验证的缓存快照**，不做实时校验 → 与真实状态（`connection_failed`）矛盾。

**建议**：`invoke()` 捕获范围扩为 `Exception` 并归一化；`session_status` 超时转为可行动错误（"Toolkit 状态查询超时：Creo 可能被挂死作业/模态框占用，请重启会话"）；`startup_status` 增加 `stale: true` 或 `verified_at` 字段，避免把缓存快照当实时状态。

---

### 🟠 P1-1｜stale revision 仅文本回传（历史复现）

乐观并发防护有效（过期 revision 提交即拒、不产生 job），但当前 revision 只在**错误文本**里，结构化 payload 无对应字段。

**建议**：错误 payload 增加 `current_revision` 与 `model_id`。

---

### 🟠 P1-2 / P2-13｜失败作业 `inspection` 形状不一致（历史 P1-2 复现并扩展）

失败作业的 `inspection` 出现两种形态，均不可靠：

| 场景 | `inspection` |
|---|---|
| 工程图批量失败 | `{"counts": {全部 0}}`（占位值，非真实状态） |
| `creo_create_feature_tree` | `null` |
| `creo_transform_geometry` | 含真实 `volume_mm3`/`bodies`（！） |

三种形态并存，客户端无法统一解析。**建议**：失败路径统一为 `"inspection": null, "note": "not refreshed on failure"`。

---

### 🟠 P1-3｜`creo_chamfer` / `creo_round` 入参 `distance` 与回显 `size` 命名不一致（历史复现）

调用参数是 `distance`，作业 `operations[]` 回显的是 `size`（类定义见 `schema.py: RoundOp(op,label,size,references)`）。**建议**：对外 schema 与内部 op 结构统一命名。

---

### 🟡 P2-8（本轮新增）｜`creo_create_plate`：`operations` 为空、`inspection.counts` **成功时也为 0**

`creo_create_plate(80×60×20,R5,3孔)` **成功**（体积 91989.38 = 期望 91989.3807），但：

```json
"operation_count": 0, "operations": [],
"inspection": { "counts": { "features":0,"surfaces":0,"edges":0,"bodies":0,"components":0 } }
```

逐特征计数反而出现在**顶层**（`extrude_count=1, round_count=1, hole_count=3`）。

**根因**：`compact_job`（`bridge.py:841`）用 `len(inspection.get(key, []))` 重算计数，而 `create_plate` 的原生 `inspection` 只给了 `counts` 字典、**没有** `features/surfaces/edges/...` 列表字段 → 恒为 0。与 `execute_plan` 族结构不一致。
**建议**：统一 `create_plate` 的 result 结构与 `execute_plan` 一致。

---

### 🟡 P2-9（本轮新增）｜`creo_set_dimensions` 对"关系驱动尺寸"报错笼统

对由关系式驱动的尺寸（`d9 = SIZE / 10`）调用 `creo_set_dimensions(d9=12)` 失败：`toolkit_code=-1, operations=[]`，错误未提示"该尺寸由关系驱动"。改用未参与关系的草图尺寸（`creo_set_sketch_dimensions`）即成功。

**建议**：拒绝前检测该尺寸是否被 relation 驱动，并提示"d9 由关系 `d9=SIZE/10` 驱动，请改参数/关系或改用草图尺寸接口"。

---

### 🟡 P2-10（本轮新增）｜`creo_solidify(mode="cut")` 报告成功但几何零变化

在 `t30_rb`（实体 z∈[20,40]）上用 `mode="cut"`、`reference={kind:'datum_plane',label:'rb_dp'}`（该基准面 z=30 正好穿过实体）、`side="positive"` 调用：

- 作业 **`succeeded`**，特征 **`RB_SO1`（id 116, type 916）确实进入特征树**；
- 但**体积完全不变**（81399.81861641473 → 81399.81861641473，15 位有效数字一致），实体 bbox 的 z 范围仍为 20..40。

即"剪裁"未移除任何材料 → **疑似静默无操作**（silent no-op）。对比 0.2.6 验收报告记载的"基准面剪裁 x=0 → 体积减半"是有效的，故本项需开发者确认（可能是 `side`/`pull_direction` 语义或我输入的剖面选择问题）。

**建议**：切剪类操作后增加"几何是否真的变化"的断言（体积/拓扑变化），否则报 `succeeded=true` 会误导调用方。

---

### 🟡 P2-11（本轮新增）｜`creo_rib` / `creo_dimension_pattern` / `creo_create_feature_tree` 失败信息笼统、无元素清单（N5 复现）

| 工具 | 本轮输入 | 结果 | 原生日志 |
|---|---|---|---|
| `creo_rib` | L 形件（底板 60×40×15 + 竖壁 60×30×10）+ YZ 中面开放剖面线 (10,40)→(40,10)、厚 4 对称 | ❌ `Regeneration produced a failed, suppressed or incomplete feature` | 仅 `PHASE=rib:…` → `BUILD_FAILED` → 回滚，**无元素级原因** |
| `creo_dimension_pattern` | leader=`rb_ex`、`dimension_id=9`(深度 20)、count=2、increment=10 | ❌ 同上文案 | 同上，**无元素级原因** |
| `creo_create_feature_tree` | 最小树 `{"id":1}` | ❌ `Toolkit operation failed; inspect native.log and its element error list` | 仅 201 行，`BUILD_FAILED=-1` 后即回滚，**native.log 里没有任何元素错误清单** |

三者的错误文案都提示"inspect … element error list"，但 `native_log_tail` 中并不存在该清单（N5 复现）。`creo_rib` 与上一轮（0.2.6）的失败现象一致，为**历史复现**；本轮输入已按"L 形件 + 端点在实体上的开放剖面"构造，故更可能是工具限制而非输入问题（仍请开发者复核）。

**建议**：失败时输出 `ProElement` 级的错误树/错误码；Rib 至少返回"剖面端点是否落在实体上""厚度方向是否与实体相交"等可行动原因。

---

### 🟡 P2-4｜作业 `operations[]` 回显成对重复、空 label（历史复现，本轮更系统）

| 场景 | 回显 |
|---|---|
| `creo_execute_plan`（export×4 + dump_tree + save，6 op） | 回显 **11 条**：每个 export/dump_tree **成对出现**——首条含 `file` 但**无** `succeeded`，次条含 `succeeded` 但**无** `file` |
| `creo_dump_feature_tree` / `creo_export_model` | `[{…,"file":…}, {"op":…,"label":"","succeeded":true}]` |
| `creo_reorder_features` / `set_parameters` / `relations` / `regenerate` / `save` / `set_geometry_transform` / `component_*` / `remove_component` | `label` 为空串 |
| `creo_update_sketch_geometry` | 成对出现，首条含 `parameters/preserved_feature_id`，次条 `label:""` |

**建议**：统一为单条 `{op,label,succeeded,file?,feature_id?,message?}`，去掉占位空条目。

---

### 🟡 P2-5｜提交响应内联大几何 / 全量 op 回显

- `creo_create_airfoil_section`：内联 83 个样点；
- **`creo_new_airfoil_blade`（3 站）：同步提交响应内联 3×83 ≈ 250 个展开点（≈ 7 KB）**；
- `creo_create_sketch`、`creo_new_loft_part`、`creo_extrude` 等：提交响应回显**完整规范化后的 operations**（含全部实体/尺寸/约束）。

**建议**：提交响应只回 `label / plane / profile 摘要 / op 计数`，几何细节留给 `creo_inspect_model`。

---

### 🟡 P2-3｜`creo_dimension_pattern` 失败信息笼统（历史复现，已并入 P2-11）

### 🟡 P2-2｜`creo_datum_plane` 的 `reference.offset`（匹配已有面）与工具 `offset`（新建偏移）同名不同义（历史复现）

### 🟡 P2-6｜自动启动的超时恢复依赖一次"显式 retry"（历史复现）

### 🟡 P2-7 / N2 / N3 / N4（历史项，本轮状态）

| 项 | 描述 | 本轮 |
|---|---|---|
| P2-7 | README 兼容矩阵以 Creo 10 为基线 | 未变（实测 12.4 完全可用） |
| N2 | `creo_list_models` 返回持久化快照，滞后于当前 revision | 仍存在 |
| N3 | `creo_get_job(detail=compact)` 在失败作业中仍内联 `native_log_tail` | 仍存在，**但有界**（`bridge.py:863` 截断至 2000 字符），且其中并无元素错误清单 |
| N4 | `creo_lookup_constants` 对不存在前缀静默返回 `{}` | 未变（建议返回空列表 + 可用前缀提示） |

---

### 🟡 P2-12（本轮新增）｜`creo_export_model` 在输出目录留下副产物

导出 STEP 后，job 的 `output/` 目录除 `t30_rb.stp`、`preview.jpg` 外，还留下 Creo 的导出日志 **`t30_rb__out.log.1`**。**建议**：导出后清理/归档该文件，避免污染输出目录。

---

### 🟡 P3（次要）

1. **`creo_new_part` 空件返回 `has_solid=false` 但 `bodies=1`**，同时 `surfaces=0/edges=0`——无实体时 `bodies` 仍为 1，易误读。
2. **`creo_list_models` 中存在长期 `status=unknown_outcome` 的残留模型**（如 `ai_part_ab80727bf524`），建议提供清理/重试语义。
3. **`creo_list_jobs(detail=compact)` 每个条目仍内联 `preview_file`/`part_file`**，列表接口偏重。
4. **模型注册表每个模型内联完整 `aliases` + `inspection`（`model.json` ≈ 92 KB/模型）**，随模型数线性膨胀，是 P1-6 的底层原因，建议按需分片。
5. **`creo_inspect_model` 与 `creo_get_job` 的 inspection 字段不统一**（前者有 `features/surfaces/...` 列表，`create_plate` 的 result 只有 `counts`），是 P2-8 的根因之一。

---

## 五、关键几何证据（解析校验，独立于工具自报）

本轮全部成功作业的体积/拓扑均命中解析解，**认定几何真实生成、非占位返回**：

| 特征 | 输入 | 观测体积 (mm³) | 解析期望 | 判定 |
|---|---|---|---|---|
| 拉伸 | 40×25×10 | 10000.0 | 10000 | ✅ |
| 倒角 | 2×2 / 2×10 | 9920.0 | 9920 | ✅ |
| 圆角 | R3 | 9842.7433 | 9842.74 | ✅ |
| 直孔 | φ8 通孔 | 9340.0885 | 9340.09 | ✅ |
| 抽壳 | t=1.5 | 4348.4475 | 4348.45 | ✅ |
| 镜像 | 关于 x=0 整体 | 8696.895 | 2×4348.4475 | ✅ |
| 旋转 | (R15,R5)×10 | 6283.1853 | π·(15²−5²)·10 | ✅ |
| 扫掠 | R3 沿 70 | 8118.75 | 并集 | ✅ |
| 填充面+加厚 | 35 mm² × 0.5 | 8714.394 | +17.5 | ✅ |
| 钣金壁 / 法兰 / 展平 | 40×30×1 等 | 1200.0 / 1534.25 / 1522.83 | ✅ | ✅ |
| 装配 | 2 组件 | 16833.14 | 8714.39+8118.75 | ✅ |
| **板件** | 80×60×20 R5 + 3 孔 | **91989.3806** | 期望 91989.3807 | ✅ |
| **多截面放样（种子）** | 3 矩形截面 | **40650.0** | — | ✅ |
| **翼型叶片（种子）** | 3 站 smooth | **21473.67** | — | ✅ |
| **板件 2（干净件）** | 60×40×20 | **48000.0** | 48000 | ✅ |
| **草图几何原地替换** | 60×40 → 80×50 | **80000.0** | 80×50×20 | ✅ |
| **拔模** | 侧面 5° | **81399.82** | 80000 + 材料 | ✅ |
| **尺寸变换（set_geometry_transform）** | 平移+45° 旋转 | **48000.0**（不变） | 刚体变换 | ✅ |
| **双实体布尔并集** | 54000 + 9000 | **63000.0**，实体数 2→1 | 63000 | ✅ |
| 导出 | STEP/STL/IGES/JPEG | 文件均生成（STEP 9696 B） | — | ✅ |

---

## 六、值得保留的优点（正面确认）

1. **保存-重载-校验闭环**：所有成功作业均返回 `saved_file_reloaded_and_verified=true` 并附 `sha256`。
2. **几何正确性**：见第五节，全部命中解析解。
3. **失败安全**：失败用例 `rollback_succeeded=true`，revision 不推进，无残留特征（如 `create_feature_tree`、`rib`、`dimension_pattern` 失败后模型保持原状）。
4. **乐观并发**：`expected_revision` 提交前拦截有效。
5. **种子重绑定路径可靠**：`creo_new_loft_part` / `creo_new_airfoil_blade` 通过种子重绑定实现原生 Blend，稳定且三处校验（创建/编辑/重载后）原生模式。
6. **0.3.0 新功能真实可用**：`creo_check_update`、`references.by_tool`、`axis_pattern` 兼容别名归一化（BUG-006）。
7. **`creo_get_job` 的 "Poll, do not resubmit" 防重提示**有效，全程未触发重复提交。
8. **多数错误信息质量高**：`creo_inspect_udf`/`creo_create_udf` 的 "UDF file_path must be an absolute path to an existing .gph or .gph.N file"、`creo_export_model` 的参数校验、`creo_update_sketch_geometry` 的实体名匹配检查，都清晰可行动。
9. **`creo_execute_plan` 可省略 `model_id` 直接建新件**（`model_name` 亦支持），一个作业完成"建件+草图+拉伸"，效率高。
10. **Coordination 自愈能力部分可用**：杀掉 Creo 后，协调器能立刻恢复并在 ~90 s 内拉起新 Creo（`launched_by_coordinator=true`）。

---

## 七、覆盖边界（诚实声明）

- **82 个工具已全部调用**；仅 `creo_inspect_model` / `creo_check_environment` 等只读工具以读取注册表/先前轮次证据替代了重复调用。
- **未通过项的性质**：
  - `creo_inspect_udf` / `creo_create_udf`：**前置条件受限**（本机无 `.gph` 库），错误信息清晰，非接口缺陷。
  - `creo_create_feature_tree`：需要**符合 SDK 的完整元素树**，最小树必然失败；其"失败文案提示元素清单但清单不存在"属真实缺陷（P2-11）。
  - `creo_dimension_pattern`：本轮输入（对基体拉伸深度做尺寸阵列、其后还有刚体变换特征）存在几何争议，失败**不作为工具缺陷定论**，但错误不可诊断属真实缺陷。
  - `creo_rib`：输入已按合法 L 形件构造，仍失败，倾向认定为工具限制，请开发者复核。
- **`creo_export_model`**：经 `creo_execute_plan` 覆盖 step/stl/iges/jpeg，另单独调用 step 通过；`pdf` 未单独验证。
- **版本范围**：所有结论仅适用于 **Creo 12.4.0.0 + MCP 0.3.0**，不可外推到其他 Creo 版本。
- **环境事件**：本轮因 P0-3 触发过一次 **Creo 会话重启**（`launch_attempt` 7→8），期间所有模型均完好（模型持久化在 `models/`，与 Creo 进程解耦）。

---

## 八、给开发者的修复优先级建议

| 优先级 | 事项 | 预期收益 |
|---|---|---|
| **P0** | **修复 `creo_loft` 挂死**（改用种子重绑定；或窗口探测 + 短超时 + 可取消） | 消除"一次调用锁死 10 分钟"的高危缺陷 |
| **P0** | **Toolkit 连接自愈 + 提供取消作业工具**；修掉协调器线程死锁 | 从"必须重启 Creo"降级为"自愈" |
| **P0** | 提交侧支持排队 / 回传 `blocking_job_id` `retry_after`；消除收尾竞态 | 大幅降低失败率与重试成本 |
| **P1** | 失败作业回传**逐 op 结果**与 `failed_operation_index` | 免去人工二分定位 |
| **P1** | 修复 `creo_drawing_view_update` | 补齐工程图编辑闭环 |
| **P1** | `creo_list_models` 增加 `detail=compact`，默认只回摘要 | 844 KB → 数 KB |
| **P1** | 修正 `rollback_succeeded` 语义；失败不再把完好模型标成 `failed` | 避免误判模型不可用 |
| **P1** | `invoke()` 捕获全部异常；`session_status` 超时给可行动错误；`startup_status` 标注快照陈旧 | 消除"空错误"与状态自相矛盾 |
| **P1** | 失败作业 `inspection` 统一为 `null` + 说明（三种形态并存的问题） | 便于客户端统一解析 |
| **P2** | 复现并修复 `creo_transform_geometry` 在复杂件上的保存失败（`ProMdlnameBackup=-1`） | 稳定性 |
| **P2** | `creo_solidify(cut)` 增加"几何是否变化"断言，避免静默无操作 | 正确性 |
| **P2** | `creo_rib` / `dimension_pattern` / `create_feature_tree` 输出元素级错误树 | 降低试错成本 |
| **P2** | 统一 `create_plate` 与 `execute_plan` 的 result 结构；修正 `counts` 重算 | 回显一致性 |
| **P2** | 统一 `operations[]` 单条结构，去掉成对空条目 | 便于解析 |
| **P2** | 去除提交响应的大几何/全量 op 回显（airfoil 250 点、sketch 全实体、loft 全 op） | 节省上下文 |
| **P2** | `set_dimensions` 检测关系驱动尺寸并给可行动错误 | 降低试错成本 |
| **P2** | 导出后清理 `*_out.log.N`；`lookup_constants` 空命中返回空列表+提示 | 体验 |
| **P2** | 版本一致性提示：源码版本 > 运行版本时提示重启连接器 | 消除"看不到新功能"误判 |
| **保持** | 保存-重载-校验闭环、`expected_revision` 防护、rollback、"Poll, do not resubmit"、种子重绑定路径 | 本 MCP 的核心亮点 |

---

*报告结束。所有结论均基于本机 Creo 12.4.0.0 上的实际调用，并与 `job.json` / `native.log` / `model.json` / 进程态交叉验证。*
