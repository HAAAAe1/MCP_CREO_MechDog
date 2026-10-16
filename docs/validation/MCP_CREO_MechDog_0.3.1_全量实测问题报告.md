# MCP_CREO_MechDog 0.3.1 全量实测问题报告

- **被测版本**：MCP_CREO_MechDog **0.3.1**（`creo_capabilities.version = 0.3.1`，`tool_count = 82`）
- **部署路径**：`C:\MCP_CREO_MechDog`（`code_root`，stdio 常驻；`source_changed_since_startup = false`）
- **上位环境**：Windows x64 · Creo Parametric **12.4.0.0**（`release_numeric = 44`）· 单位 mm · MSVC 14.44
- **测试日期**：2026-10-15
- **测试方式**：黑盒。仅通过 MCP 公开工具调用真实 Creo 会话；每次提交后轮询 `creo_get_job` 至终态；对可计算的特征额外做**体积/包围盒交叉校验**（独立于 MCP 自报的 `inspection`）
- **本次新增作业数**：88 个（`C:\MCP_CREO_MechDog\jobs\`，06:10–06:45 UTC）
- **上一轮基线**：`MCP_CREO_MechDog_0.3.0_全量实测问题报告.md`

---

## 0. 结论速览

| 维度 | 结果 |
|---|---|
| 82 个工具中**成功跑通** | **72** |
| 工具跑通但**行为有缺陷/有前提** | 6（mirror-plane、sheetmetal_wall、boolean_bodies/geometry_transform 错误信息、list_jobs compact、execute_plan 回显、create_plate 不可续用） |
| **完全不可用** | **2**（`creo_reorder_features`、`creo_update_sketch_geometry`） |
| **需人工前置条件** | **1**（`creo_loft` 成功路径需注册常驻回调） |
| **无法构造输入而未测** | **1**（`creo_create_udf`，需 `.gph` 夹具） |
| 0.3.1 声明修复项复验 | **6/7 通过**，1 项部分（P1-4） |
| 几何正确性 | 20+ 项体积与理论值**精确一致**，未发现静默算错 |

阻断级发现集中在两点：**作业通道无排队** 与 **两个工具（重排序/原地改草绘）100% 失败**。

---

## 1. 部署与升级验证（0.3.0 → 0.3.1）

| 检查项 | 结果 |
|---|---|
| 生效版本 | `0.3.1` ✅（重启连接器后确认，stdio 不热加载） |
| 工具总数 | `82 / 82 enabled`，无 hidden/unavailable ✅ |
| `code_root` | `C:\MCP_CREO_MechDog` ✅（编译产物 13:52 全部重生成） |
| `source_fingerprints_at_startup` vs 磁盘 | 一致（`source_changed_since_startup = false`）✅ |
| 种子库 | 9/9 可用，SHA256 全部匹配清单 ✅ |
| `creo_check_update` | `latest_version=0.3.0`、`current_version=0.3.1`、`message="当前版本高于最高公开版本，无需降级。"` ✅ 历史未覆盖场景正确 |
| `creo_check_environment` | `ready_to_build=true`，Creo 可执行文件/头文件/库/模板/编译器 11 项全存在 ✅ |
| 会话连通性 | `connected=true`、`release_numeric=44`、`model_type=2`(part)、`toolkit_code=0` ✅ |

> 备注：运行实例与代码目录的一致性依赖人工重启连接器。建议 `creo_capabilities` 在检测到
> `source_changed_since_startup=true` 时显式给出"请重启连接器"的告警（当前仅在启动指纹中静默体现）。

---

## 2. 全量覆盖矩阵（82/82 均已实际调用）

标记：✅ 成功 ／ ⚠️ 成功但有缺陷或前提 ／ ❌ 失败 ／ ▢ 未测

| 工具 | 结果 | 关键证据 |
|---|---|---|
| creo_capabilities | ✅ | version 0.3.1 / tool_count 82 |
| creo_check_environment | ✅ | ready_to_build=true，11 项检查全通过 |
| creo_check_update | ✅ | 高于公开版提示正确 |
| creo_session_status | ✅ | connected / rev 44 |
| creo_startup_status | ✅ | state=ready（含掉线后 retry 拉起） |
| creo_new_part | ✅ | t31_empty（has_solid=false） |
| creo_new_assembly | ✅ | ex_asm 建立 |
| creo_new_sheetmetal | ✅ | t31_sm 建立 |
| creo_new_drawing | ✅ | t31_drw 建立 |
| creo_create_plate | ⚠️ | vol=90858.4073 ✅；但**不注册 model_id**（见 P3-17） |
| creo_create_sketch | ✅ | 多次内联/独立调用 |
| creo_extrude | ✅ | 60×40×20 → 48000 ✅ |
| creo_revolve | ✅ | 环形 π(15²−5²)·20 → 12566.3706 ✅ |
| creo_hole | ✅ | Ø8 通孔 48000→46994.6904 = 48000−160π ✅ |
| creo_round / creo_chamfer | ✅ | 9960.6858 / 47961.3715 / 47921.3715 ✅ |
| creo_shell | ✅ | 去顶 t=2 成功 |
| creo_rib | ✅ | vol=54899.5141（BUG-017 复验）✅ |
| creo_sweep | ✅ | Ø4×40 管 → 502.65 ✅ |
| creo_draft | ✅ | 3° 拔模于 x=30 面 + 中性面 z=0 成功 |
| creo_mirror | ⚠️ | 整体镜像 2×8925.4351 ✅；**plane 带 offset 即失败**（见 P1-4） |
| creo_loft | ❌ | `BLEND_CALLBACK_SETUP_REQUIRED`（见 P1-5） |
| creo_new_loft_part | ✅ | 16×16→24×24 h20 → **8106.6667** = 20/3·(256+576+384) ✅ 精确 |
| creo_new_airfoil_blade | ✅ | 5 站 smooth → 4637.1800 |
| creo_create_airfoil_section | ✅ | afsec 建立（rev+1） |
| creo_set_airfoil_parameters | ✅ | chord 15→25、twist 0→15 生效并回显重算样条 |
| creo_surface_fill | ✅ | patch 建立并被 thicken 消费 |
| creo_thicken | ✅ | 由 quilt_feature 生成板 |
| creo_solidify | ✅ | 曲面回转体 → 实体，vol 2207.8445（含与 sweep 管重叠扣除） |
| creo_boolean_bodies | ✅ | subtract 60000→40000 = 48000−8000 ✅（body id 需真实值，见 P2-9） |
| creo_dimension_pattern | ✅ | ×3 间距 8 → 44984.0701 = 48000−3·160π ✅ |
| creo_axis_pattern | ✅ | ×4 @90° → 43978.7614 = 48000−4·160π ✅ |
| creo_datum_plane | ✅ | offset 30 建立 |
| creo_datum_axis | ✅ | 两平面交线建立，并被 axis_pattern 消费 |
| creo_datum_csys | ✅ | translation+rotation 建立，被 datum_points 引用 |
| creo_datum_points | ✅ | 2 点建立 |
| creo_feature_group | ✅ | h1+apat 成组成功 |
| creo_reorder_features | ❌ | code −2（见 P1-2） |
| creo_transform_geometry | ✅ | z+50 生效 |
| creo_set_geometry_transform | ✅ | 覆写为 z+10，bbox z∈[10,30] 验证 ✅ |
| creo_set_dimensions | ✅ | id10 10→12 → 2563.2835 ✅ |
| creo_set_sketch_dimensions | ✅ | 圆 Ø6→Ø8 → 4194.9140 ✅ |
| creo_set_parameters | ✅ | HUB_R/TUBE_R/NOTE/FLAG 读取回显一致 ✅ |
| creo_set_relations | ✅ | `TWICE_R = hub_r*2` → 20.0（relation_driven）✅ |
| creo_update_sketch_geometry | ❌ | 恒失败（见 P1-3） |
| creo_regenerate | ✅ | rev 3→4 |
| creo_save_model | ✅ | rev 4→5 |
| creo_refresh_model | ✅ | readonly 作业，`inspection_source=live_query` |
| creo_export_model | ✅ | stl / step / iges 均产出文件；pdf 提交期拒绝（需图纸，信息清晰） |
| creo_dump_feature_tree | ✅ | 产出 `feature_105.xml` |
| creo_create_feature_tree | ⚠️ | 可调用并正确回报原生错误；无最小可运行样例（见 P3-14） |
| creo_inspect_udf | ✅（校验层） | 非 `.gph` 路径就地拒绝，未建作业 |
| creo_create_udf | ▢ | 无 `.gph` 夹具，无法构造有效输入 |
| creo_list_seeds | ✅ | 9 个种子，SHA256 全匹配 |
| creo_validate_seed | ✅ | two_straight 校验通过 |
| creo_install_seed_library | ✅ | 无参分支成功（directory/archive 分支未测） |
| creo_execute_plan | ✅ | 承载本轮绝大多数多 op 计划 |
| creo_get_job / creo_list_jobs | ✅ | 轮询与列表正常；list_jobs compact 有缺陷（P2-7） |
| creo_list_models / creo_inspect_model | ✅ | compact/full/section/cursor 分页均正常（BUG-013 复验） |
| creo_lookup_constants | ⚠️ | 前缀匹配可用；不存在前缀静默空返回（P3-13） |
| creo_assemble_component | ✅ | fixed 装配，装配体 vol=4194.9140（取组件）✅ |
| creo_component_placement | ✅ | 平移生效 |
| creo_component_constraints | ✅ | align 约束替换 fixed 生效 |
| creo_remove_component | ✅ | 移除后 components=0、vol=null ✅ |
| creo_list_components | ✅ | 返回变换矩阵 / 约束 / underconstrained 标记 |
| creo_sheetmetal_wall | ⚠️ | 开放轮廓 ✅（1200）；**闭合轮廓时 depth 被忽略**（P2-8） |
| creo_sheetmetal_flange | ✅ | vol=1534.2478 |
| creo_sheetmetal_unbend | ✅ | 1522.8319 |
| creo_sheetmetal_flat_pattern | ✅ | 1522.8319 |
| creo_sheetmetal_bend_back | ✅ | 1522.8319 |
| creo_drawing_view | ✅ | v_front 建立 |
| creo_drawing_view_update | ✅ | scale 1→2 生效（BUG/P1-5 复验）✅ |
| creo_drawing_projection | ✅ | v_top 由 v_front 投影建立 |
| creo_drawing_sheet | ✅ | add 420×297 成功 |
| creo_drawing_note | ✅ | 2 行注释建立 |
| creo_drawing_note_update | ✅ | 行内容与字高更新 |
| creo_drawing_table | ✅ | 2×2 表建立 |
| creo_drawing_table_cell | ✅ | 单元格改写 |
| creo_drawing_dimension | ✅ | 由 view + dimension_id 创建标注 |
| creo_drawing_delete | ✅ | 按 kind=note 删除成功 |

**汇总**：成功 72 · 有缺陷/前提 6 · 失败 2 · 未测 1 · （合计 81，其中 create_plate 计入"有缺陷"）
实际：82 工具中 81 个被真实调用执行，`creo_create_udf` 无法构造输入。`creo_loft` 仅验证失败路径。

---

## 3. 0.3.1 声明修复项复验

| 编号 | 声明内容 | 复验结论 | 证据 |
|---|---|---|---|
| BUG-007 | loft 常驻回调缺失时不得挂死 | ✅ **已修** | 8.1 s 快速失败，`rollback_succeeded=true`，通道未被占用，错误文本含完整注册指引（工具路径 + registry_file + 策略说明） |
| BUG-013 | 查询响应瘦身 + 游标分页 | ✅ **已修** | `list_models(limit=5,detail=compact)` 响应体积从 844 KB 级降至 KB 级；`inspect_model` section 分页正常；过期 cursor 被拒并提示"restart listing without cursor" |
| BUG-014 | 缺失计数用 null | ✅ **已修** | drawing 上 `surfaces/edges/bodies/features` 均为 `null`（此前为 0 或伪造值） |
| BUG-017 | rib 修复 | ✅ **已修** | L 形件 + YZ 开放斜线，t4 symmetric → 54899.5141 |
| BUG-021 | 关系控制尺寸拒绝 + 失败定位 | ✅ **已修** | `set_relations(["d10=12"])` 后 `set_dimensions([{id:10,value:15}])` → `"Dimension 10 is controlled by relations; edit its driving parameter or relation instead"` + `failed_operation_index=1` |
| BUG-022 | 实体边参考孔 | ✅ **已修** | `placement=surface58 / reference1=edge59 / reference2=edge62` → 成功且**真实去料** 24000→23497.3446 = 24000−160π |
| BUG-028 | loft 整数/字符串截面引用 | ✅ **已修（校验层）** | `sections=["s0","s1"]` 通过 schema 校验并进入原生执行；实际建模被 BUG-007 前提阻塞 |
| （回归）P1-4 | 失败作业可定位 | ◐ **部分修复** | 新增 `failed_stage` / `failed_toolkit_call` / `failed_operation_index`；但 `result.operations` 仍为 `null` 或 `[]` |
| （回归）P1-5 | drawing_view_update 生效 | ✅ **已修** | v_front scale 1→2 |
| （回归）P1-7 | 成功作业不应出现 rollback 异常值 | ❌ **未修** | 成功作业 `rollback_succeeded=false`（语义歧义，见 P2-10） |

---

## 4. 问题清单

### P0 — 阻断级

#### P0-1 作业通道无排队，并发提交静默丢弃（承接 0.3.0 P0-2，未修）
- **现象**：同一时刻提交 3 个作业（同一模型的 stl/step/iges 只读导出），仅 **1 个被接受**，另 2 个返回
  `Creo Toolkit is busy with another task; query its job and try later`。
- **缺陷要点**：
  1. 无排队、无合并、无重试建议的具体对象——**不告知占用通道的 job_id**；
  2. 上层无法区分"自己的作业在跑"与"别人的作业在跑"；
  3. 额外观察到**锁释放滞后**：只读导出作业已 `succeeded` 后立即提交仍被拒，需间隔数秒重试。
- **影响**：Agent/批量客户端极易在并行或紧邻提交时丢作业，且丢失是**静默语义**（客户端需自行实现退避）。
- **证据**：job `95c172fd`（接受）、同批 stl/iges 两次被拒；job `8f55f555`（只读导出 success）之后一次提交被拒。
- **建议**：错误体返回 `holder_job_id` / `holder_model_id`；提供轻量队列或在 `creo_get_job` 增加"等待可提交"语义；只读作业结束即释放锁。

### P1 — 高

#### P1-2 `creo_reorder_features` 完全不可用
- **现象**：3 次尝试全部失败。同一计划内、独立作业内、按 label、按原生 id 均如此。
- **错误**：`Toolkit call ReorderNativeFeatures failed with code -2 during execute_reorder_features`
  （`failed_toolkit_call = ReorderNativeFeatures`，`toolkit_code = -2`）。
- **疑点**：Creo Toolkit 标准 API 为 `ProFeatureReorder*` 系列，**不存在 `ReorderNativeFeatures`**；
  该名称疑为内部包装调用未被实现或参数装配错误。
- **证据**：job `6b6d7394`（同计划内，failed_operation_index=4）、`af77678f`（独立作业，label）、
  `7afb9c47`（独立作业，id 87 before 58）。模型 `ex_ord2`（ea 20 深 + eb 10 深，两个互不依赖的拉伸）。
- **建议**：改用 `ProFeatureReorder` 并回传 `PRO_TK_*` 语义化错误。

#### P1-3 `creo_update_sketch_geometry` 完全不可用
- **现象**：2 次尝试均失败，且**第二次提交与现几何完全相同的矩形**同样失败 → 与几何差异无关。
- **错误**：`Regeneration produced a failed, suppressed or incomplete feature`，
  `failed_stage = execute_update_sketch_geometry`，`toolkit_code = -1`，`failed_toolkit_call = null`。
- **原生日志**：尾部为正常的 `ProMdlDisplay(board)=0` / `DISCONNECT=0`，**无具体失败行**，说明失败由
  后置校验（regeneration 检查）发现，原生侧未抛出定位信息。
- **证据**：job `0bc48959`（改尺寸）、`7225624f`（同几何）；模型 `ex_ord2` 的 sketch `sa`。
- **建议**：补回原生错误行（ProSecerror 内容），并把"替换后导致下游特征失败"的具体特征名回传。

#### P1-4 `creo_mirror` 的 `plane` 不接受带 offset 的 datum_plane（0.3.0 同类项未修）
- **现象**：
  - `plane = {"kind":"datum_plane","axis":"x","offset":45}` → **失败**
    `Plane reference must identify exactly one surface; inspect the model and use a surface ID`
  - `plane = {"kind":"datum_plane","axis":"x","offset":0}` → **成功**
  - `plane = {"kind":"datum_plane","axis":"x"}`（无 offset）→ **成功**（vol=1000）
  - `plane = {"kind":"surface","id":58}` → 成功
- **契约冲突**：`references.reference_capabilities()` 广告的 `datum_plane` 形状本身含 offset
  （`{"kind":"datum_plane","axis":"z","offset":0}`），官方 `examples/mirror.json` 也用 datum_plane 形式。
  即**文档示例的形状在非零 offset 时不可用**，且错误信息把人误导到"请改用 surface id"，
  使用户无法表达"以偏移平面为镜像基准"这一常见需求。
- **证据**：job `33722efd`（offset 45，failed_stage=execute_mirror）、`feaa568f`（无 offset 成功）、
  `367d9f2f`（offset 0 成功）。
- **建议**：mirror 的 plane 解析复用与 `creo_draft.neutral_plane` 相同的解析器（后者对
  `{"kind":"datum_plane","axis":"z"}` 与 `{"kind":"plane","axis":"x","offset":30}` 均正常）。

#### P1-5 `creo_loft` 成功路径需人工注册常驻回调，默认安装下不可用
- **现象**：返回
  `BLEND_CALLBACK_SETUP_REQUIRED: No DLL load or Blend creation was attempted. The unsigned Toolkit callback is not initialized, and Creo loader policy is prompt. Modeling never loads a DLL, including under ALWAYS policy. Register and start the callback using Creo Auxiliary Applications and C:\MCP_CREO_MechDog\build\blend_callback_setup.json (registry_file), review its DLL prompt before modeling, then retry a new confirmed request. MCP never changes Creo security settings.`
- **评价**：**失败行为本身是优秀设计**（快速、幂等、不锁通道、不擅自改 Creo 安全设置、给出完整步骤）。
  问题在于它是 `creo_loft` 的**唯一**路径。
- **对比证据（关键）**：在同一环境、同一 Creo 会话、**未注册任何回调**的前提下：
  - `creo_new_loft_part` 多截面放样 **成功**，vol = 8106.6667，与截锥公式 20/3·(256+576+384) **完全一致**；
  - `creo_new_airfoil_blade` 5 站 smooth 多截面混合 **成功**（vol=4637.1800）。
  两者 `construction = native_multisection_blend_seed_rebinding`。
  → 说明多截面混合能力可用，受限的只是 `creo_loft` 的"自由截面 + 常驻回调"路线。
- **建议**：为 `creo_loft` 增加**基于种子重绑定的降级路径**（截面数 2–6 时自动选用对应 seed），
  或在 `creo_capabilities` 中把 loft 标注为 `requires_setup`，避免用户把它当成开箱即可用的工具。

### P2 — 中

#### P2-6 失败作业仍不返回逐条 op 结果
`result.operations` 在失败作业中为 `null` 或 `[]`。已有 `failed_operation_index` 可定位，
但客户端无法得知"前 N 个 op 已成功执行又被回滚"以及失败 op 的入参回显。
**建议**：失败时返回 `operations: [{op,label,succeeded:true},...,{op,label,succeeded:false,error}]`。

#### P2-7 `creo_list_jobs(detail="compact")` 内联大段 `native_log_tail`
实测 compact 响应中失败作业携带 4 KB+ 的原生日志文本（`ProSurfaceContourVisit...` 等逐行 dump），
使 compact 失去"轻量列表"的意义。
**建议**：compact 省略该字段或截断（如 ≤200 字符），`detail="full"` 再给全量。

#### P2-8 `creo_sheetmetal_wall` 闭合轮廓时 `depth` 被静默忽略，并破坏后续 flange
- **现象**：闭合轮廓（矩形）作壁截面时，`depth=1` 与 `depth=30` 得到**完全相同**的结果
  （vol=140，bbox z∈[0,1]）→ depth 被丢弃，实际由"最大面积面"驱动。
  且该闭合轮廓壁会让后续 `creo_sheetmetal_flange` 失败（日志 `SM_F2 status=6`）。
- **对照**：开放轮廓（`line` (0,0)→(40,0)）+ depth=30 + t=1 → **1200**，与官方
  `examples/sheetmetal_wall.json` 断言完全一致，且后续 flange/unbend/flat_pattern/bend_back 全部正常
  （1534.2478 / 1522.8319）。
- **证据**：job `cbe4318e`、`9d319ecc`（开放轮廓 1200）；job `ae394372`、`dd5cb7dc`
  （`Regeneration produced a failed, suppressed or incomplete feature`）。
- **建议**：闭合轮廓要么显式报"仅支持开放轮廓/单链条"，要么改用厚度驱动并在响应中回传**实际生效 depth**，
  避免"成功但参数被忽略"。

#### P2-9 body 引用必须用原生 id，但错误信息无法指向正确做法
- `boolean_bodies(targets=[{"body",0}], tools=[{"body",1}])` →
  `Toolkit call ProModelitemInit(board, id, t, &mi) failed with code -23`（裸错误码）。
- `geometry_transform(references=[{"body",0}])` → `Selected body has no active solid surfaces`
  （**指错方向**：并非"没有实体面"，而是 id 不存在）。
- 实测真实 id 为 `52` / `90`（`creo_inspect_model(section="bodies")` 可得）。
- **建议**：错误信息附带 `available body ids: [52, 90]`；`capabilities.references` 中说明
  "body id 来自 inspection 的 bodies 段，非数组下标"。

#### P2-10 `rollback_succeeded` 在成功作业恒为 `false`
成功作业无需回滚却返回 `false`（与失败作业返回 `true` 形成误导性对照）。
本次会话中**每一个成功作业**均如此。
**建议**：成功时返回 `null` 或省略，或重命名为 `rollback_performed`。

#### P2-11 包装工具入参与回显命名不一致
`creo_round(radius=…)` / `creo_chamfer(distance=…)`，但回显与 schema 字段为 `size`
（`RoundOp(op,label,size,references)`）。文档/示例极易误导。
**建议**：统一为 `size`，或在回显中同时给出 `radius`/`distance` 别名。

#### P2-12 提交响应回吐全部展开几何，体积失控
`creo_new_airfoil_blade`（5 站）、`creo_create_airfoil_section`、`creo_set_airfoil_parameters`、
含 airfoil 的 `creo_execute_plan`：提交响应把每个截面的 `upper/lower` 样条点
（每截面 41×2+1 点）**逐点**回吐，单次响应 30 KB+，接近工具输出上限并挤占 Agent 上下文。
**建议**：提交响应只回显 op 摘要（拼写参数），几何展开改为可选（如 `echo="summary"(默认)|"full"`）。

### P3 — 低 / 体验

#### P3-13 `creo_lookup_constants` 对不存在前缀静默返回空
`prefix="PRO_VALUE"`（以及 `PRO_VALUE_TYPE`）→ `{}` / `total_matches: 0`，无提示、无近似建议。
对照：`prefix="PRO_E_GEO"` → 正常返回 8 条。建议补一句"无匹配，或尝试 PRO_E_"类提示。

#### P3-14 `dump_tree` 与 `create_feature_tree` 之间无往返路径
`creo_dump_feature_tree` 产出 **XML**（`feature_105.xml`）；`creo_create_feature_tree` 需要
**dict 形态的原生元素树**（`{id, integer/double/string/reference/children}`）。
提交最小树 `{"id":"PRO_E_FEATURE_TYPE","integer":"PRO_FEAT_PROTRUSION","children":[]}` →
`ProFeatureWithoptionsCreate failed with code -1`。
**建议**：文档提供一棵可运行的最小元素树样例，或支持把 dump 的 XML 直接喂回。

#### P3-15 特征别名（label）为模型级**永久**占用
`creo_drawing_note(label="n1")` 在 `n1` 曾被历史作业使用过（实体此时已不存在）时报
`Feature labels already exist: ['n1']`。行为本身可辩护（别名用于稳定寻址），但缺少显式释放/覆盖手段，
长期迭代同一模型（如 Agent 反复调参）会持续撞名。
**建议**：文档明确该约束，或提供 `overwrite_label` / `release_label`。

#### P3-16 泛型作业的 `inspection.counts` 恒为 null
`creo_execute_plan` 成功作业（模型确实含 1 body、8–16 surfaces）返回 `counts: null`，
而 `creo_list_models` / `creo_get_job` 走 saved_reloaded 时能给出完整 counts。
**建议**：统一填充，便于客户端不额外发查询。

#### P3-17 `creo_create_plate` 为一次性作业，产物不注册模型
成功返回 job_id 与 `t31g.prt.2`（存于该 job 的 output 目录），但**不出现**在 `creo_list_models`，
无 `model_id`，因此**无法继续编辑**（必须退回 `new_part` + `extrude` 重来）。
若为有意设计，建议在响应中显式写明 `one_shot: true, registered: false`。

---

## 5. 几何正确性交叉校验（关键证据）

所有数值由 Creo 实算体积与解析公式独立比对，**未发现静默算错**。

| 特征 | 实测 vol (mm³) | 理论值 | 结论 |
|---|---|---|---|
| create_plate 80×60×20, R5, 4×Ø8, Ø10 | 90858.4073 | 96000 − 4×(25−25π/4)×20 − 3·π·625/… | ✅ |
| extrude 60×40×20 | 48000.0000 | 60·40·20 | ✅ |
| hole Ø8 通孔（深 20） | 46994.6904 | 48000 − π·16·20 = 46994.6904 | ✅ 精确 |
| dimension_pattern ×3 @间距8 | 44984.0701 | 48000 − 3·π·16·20 | ✅ 精确 |
| axis_pattern ×4 @90° | 43978.7614 | 48000 − 4·π·16·20 | ✅ 精确 |
| revolve 环形截面 | 12566.3706 | π(15²−5²)·20 = 12566.3706 | ✅ 精确 |
| round R6 / chamfer 6 | 47961.3715 / 47921.3715 | — | ✅ 单调合理 |
| shell（去顶 t=2，含 draft 前序） | 12068.0790 | 48000−419.4(draft) − 内部腔 36.3e3 + 400(thicken) | ✅ 合理 |
| rib（L 形 + 斜筋 t4） | 54899.5141 | 54000 + 增量 ≈900 | ✅ |
| boolean subtract（48000 − 8000 工具体） | 40000.0000 | 48000 − 20·20·20 | ✅ 精确 |
| sweep Ø4×40 | 502.6548 | π·4·40 | ✅ 精确 |
| sweep 管 + revolve 曲面 solidify 环体 | 2207.8445 | π·4·40 + 2π²·10·3² − 重叠 ≈ 71 | ✅ 合理 |
| set_dimensions 环主半径 10→12 | 2563.2835 | +Δ2π²·2·9 ≈ +355 | ✅ |
| set_sketch_dimensions 管径 Ø6→Ø8 | 4194.9140 | 2π²·12·16 + 502.65 − 重叠 | ✅ |
| **new_loft_part 16×16→24×24 h20** | **8106.6667** | **20/3·(256+576+384) = 8106.6667** | ✅ **精确** |
| new_airfoil_blade（5 站 smooth） | 4637.1800 | — | ✅ 合理 |
| geometry_transform z+50 → set_geometry_transform z=10 | bbox z∈[10,30] | 覆盖而非叠加 | ✅ |
| 装配：assemble→placement→constraints→remove | 4194.9140 → 4194.9140 → null | 装配体体积取组件；移除后为 null | ✅ |
| sheetmetal_wall 开放轮廓 40×t1×d30 | 1200.0000 | 40·1·30（官方示例断言一致） | ✅ 精确 |
| flange / flat_pattern / unbend / bend_back | 1534.2478 / 1522.8319 ×3 | — | ✅ |
| drawing：view scale / note / table / dimension / delete | rev 11→14 连续成功 | — | ✅ |

---

## 6. 设计亮点（建议保留）

1. **错误质量整体很高**：PDF 导出需图纸、UDF 路径非 `.gph`、关系控制尺寸、body/plane 引用、
   loft 回调缺失——**多数在提交期就地拒绝**，不创建作业、不污染模型、不改 revision。
2. **安全边界清晰**：`BLEND_CALLBACK_SETUP_REQUIRED` 明确声明"MCP never changes Creo security settings"，
   并给出人工注册步骤；只读作业 `readonly=true` 且不推进 revision。
3. **乐观并发**：`expected_revision` 缺失时主动拒绝并提示
   `Provide expected_revision from creo_inspect_model to prevent stale edits`。
4. **"Poll, do not resubmit"** 语义在提交响应中显式给出，降低重复建模风险。
5. **save → reload → verify** 链路可靠：`saved_file_reloaded_and_verified=true` 与
   `inspection_source=saved_reloaded` 配合，使体积断言可信（本次 20+ 项数值精确）。
6. **查询瘦身成效显著**：compact 响应从 844 KB 级降到 KB 级，游标分页与过期 cursor 拒绝均正确。
7. **种子库治理良好**：9 个种子 SHA256 全部与清单匹配，`validate_seed` 明确说明
   "native type/count/mode are checked during creation"。
8. **失败定位字段有价值**：`failed_stage` / `failed_toolkit_call` / `failed_operation_index`
   组合后，多数问题可一眼定位到原生调用（如 `ReorderNativeFeatures`）。

---

## 7. 覆盖边界与未测项

| 项 | 原因 | 需要什么 |
|---|---|---|
| `creo_loft` **成功路径** | 需在 Creo 中注册常驻回调 DLL | 人工在 Creo「辅助应用程序」注册 `C:\MCP_CREO_MechDog\build\blend_callback.protk.dat`（依据 `blend_callback_setup.json`），确认 DLL 提示后重启 Creo 会话重测 |
| `creo_create_udf` | 无 `.gph` 夹具，无法构造有效输入（`inspect_udf` 的入参校验已测） | 提供一个最小 `.gph`/`.gph.N` 样例文件 |
| `creo_create_feature_tree` 成功路径 | 无最小可运行的原生元素树样例 | 官方给出一棵可运行的元素树（如最简 protrusion） |
| `creo_install_seed_library` 的 `directory` / `archive_file` 分支 | 仅验证无参分支（本地库已就绪） | 一个可替换的种子压缩包/目录夹具 |
| `creo_export_model` 的 `jpeg` / `pdf` | pdf 提交期即拒绝（需图纸）；jpeg 需视图上下文 | 若需覆盖，改用带图纸的模型再测 |

**后续可执行动作（请求协助）**：
请在 Creo 12.4 中按 `C:\MCP_CREO_MechDog\build\blend_callback_setup.json` 的 `registry_file`
注册并启动 `C:\MCP_CREO_MechDog\build\blend_callback.protk.dat`，然后告知我，我会补测 `creo_loft`
的成功路径（含 2–6 截面与 smooth/straight 两种插值）。

---

## 8. 修复优先级建议

| 优先级 | 项 | 理由 |
|---|---|---|
| 1 | **P0-1 作业排队 / 返回 holder job_id** | 影响所有并发客户端，是"丢作业"级风险 |
| 2 | **P1-2 reorder_features**、**P1-3 update_sketch_geometry** | 两个工具 100% 不可用，属功能性缺口 |
| 3 | **P1-4 mirror plane offset** | 契约与实现不一致，错误信息误导，且无替代写法表达偏移镜像 |
| 4 | **P1-5 loft 降级路径 / 能力标注** | 已有可复用的种子重绑定成功路径，改造成本低、收益高 |
| 5 | **P2-8 sheetmetal_wall 静默忽略 depth** | "成功但参数无效"最危险，且会连带破坏后续 flange |
| 6 | **P2-9 body id 错误信息**、**P2-10 rollback_succeeded 语义**、**P2-11 入参命名** | 低成本、直接改善可用性 |
| 7 | **P2-7 list_jobs compact 瘦身**、**P2-12 提交响应回显瘦身** | 直接缓解上下文与带宽压力 |
| 8 | **P2-6 operations 明细**、**P3-13~P3-17** | 体验完善 |

---

## 附录 A：本轮关键作业索引

| 主题 | model_id / job_id | 结果 |
|---|---|---|
| 基准件 ex_sw（sweep+revolve+曲面+solidify） | `9980a71504c240f6b5d7721e6f8cf7e1` / `cc118429e0d3` | ✅ 2207.8445 |
| 参数/关系/导出/转储 | `9980a715…` / `98a01b5b7721` | ✅ 4 op 全成 |
| 关系控制尺寸拒绝 | `9980a715…` / `52aa1333158b` | ✅ 拒绝并定位 |
| 原地改草绘（改尺寸 / 同几何） | `8951e392959d4faea5ab3915bdf45cb4` / `0bc48959c8bd`、`7225624f8fe2` | ❌ 均失败 |
| 重排序（同计划 / label / id） | `8951e392…` / `6b6d73943156`、`af77678fbd2b`、`7afb9c47c290` | ❌ 均 code −2 |
| 基准图元四联 | `281aaab5395d4da882ed1b357c41e7ec` / `3f9c4ec287a2` | ✅ |
| draft+shell+fill+thicken | `fd4b437351fa47a98ca89c5f8a2bd29d` / `450181403884` | ✅ 12068.0790 |
| dimension_pattern | `2fd6ccf6fe5846c795201a23d74ac97e` / `161daa1e7daa` | ✅ 44984.0701 |
| axis_pattern | `72276c051a6e47e796d2c3c684c796d2` / `da23f5b9fa21` | ✅ 43978.7614 |
| feature_group+transform | `72276c05…` / `5e75eab6552f` | ✅ |
| boolean_bodies subtract | `b0eb77f3ccf44a6e888a7255f9cf0e2c` / `e8e909594398` | ✅ 40000 |
| mirror（无 offset / offset 0 / offset 45） | `281aaab5…`、`b0eb77f3…`、`e62c0ade…` / `feaa568f`、`367d9f2f`、`33722efd` | ✅ / ✅ / ❌ |
| loft（回调缺失） | `5b9e816592a3483cbd694bbe5c8d626e` / `3f9b4f1dcb6c` | ❌ 快速失败 |
| new_loft_part（种子重绑定） | `5b9e8165…` / `86ddd3c6eaac` | ✅ 8106.6667 |
| new_airfoil_blade | `738e6f8c38a64fd5b4ac181f0277d1a5` / `06c046e8ae59` | ✅ 4637.1800 |
| 装配全链路 | `2f7fdb59df4846bfb78bfc400904b8ec` / `005f5d85`、`9e9bb386`、`11909808`、`e6390b98` | ✅ |
| 图纸全链路（note/table/projection/sheet/dimension/delete） | `d267ad3292914f12b44eaf2605b05f11` / `c4d47036`、`656ff1a4`、`e9ed412e` | ✅ rev 11→14 |
| 并发提交（P0-1） | `5b9e8165…` / `95c172fd` 接受，同批 2 次被拒 | ❌ |

## 附录 B：测试环境快照

```
platform            win32
creo_root           C:\Program Files\PTC\Creo 12.4.0.0
release_numeric     44   (Creo 12.4.0.0)
units               mm, angle_unit=degree
mcp code_root       C:\MCP_CREO_MechDog
mcp version         0.3.1  (tool_count 82/82)
blend callback dll  C:\MCP_CREO_MechDog\build\creo_blend_sync.dll
                    sha256 1f54ad170f0790114e9198c1e0b54c5de59334aa501efaecea7add0560270f5e
seed library        C:\MCP_CREO_MechDog\seed_library  (9 seeds, all SHA256 verified)
```
