# MCP_CREO_MechDog v0.3.0 核心问题：尺寸编辑（set_dimensions / set_relations）系统性失败

> 测试日期：2026-10-14
> 被测版本：MCP_CREO_MechDog **0.3.0**（is_prerelease=true，check_update 显示已是最新）
> 测试环境：Windows / Creo Parametric 10.0.0.0（D:\Program Files\PTC\Creo 10.0.0.0）/ Toolkit 异步连接 release_numeric=42 / VS2022 BuildTools
> 测试方式：在本机 Creo 会话中逐个实际调用全部 creo_* 工具，记录成功/失败与原生日志

## ⓪ 核心问题（本次测试发现的最大问题）

**set_dimensions 与 set_relations 两条尺寸编辑链路全部确定性失败，且失败路径异常地进入 `activate_blend_context`（Blend 特性专属上下文）。**

这被判定为最大问题，理由有三：

1. **影响面最大**：尺寸编辑是参数化建模的根基。set_dimensions 挂了意味着所有"检查 → 改尺寸 → 再生"闭环全部失效，之前能建的特征也无法参数化修改，等于把 MCP 的"native 参数化"价值砍掉一半。
2. **根因指向共享基础设施而非单个工具**：两个不同工具（改尺寸、设关系式）报同样的 `Toolkit operation failed`，且失败 job 的 native_log_tail 都以
   `PHASE=activate_blend_context → ProMdlDisplay → ProDirectoryChange → ExportBlendFeatureInfo → RestoreFeatureInfoDirectory → DISCONNECT` 收尾——
   这是 Blend（loft）专用激活流程的日志。**改尺寸操作根本不该进入 Blend 上下文**，说明 job runner 中"非建模类 Toolkit 操作"的模型激活逻辑存在系统性 bug。
   旁证：历史上有一个与本测试无关的 job（`ad7856f88c70425f856f8467d7c24c31`）也超时在同一 `stage=activate_blend_context`，说明该路径已多次出问题。
3. **不可绕过**：hole 基准面定位失败还能用边参考绕过，rib 失败可以用薄拉伸替代；但尺寸编辑没有等价替代路径，失败即功能缺失。

**建议作者优先排查**：job runner 中 `activate_blend_context` 的触发条件——为何 set_dimensions / set_relations 会走 Blend 激活分支；修复后应验证 D13=40 这类最小用例（复现 job：`b2f560e244af4f1292f6f265ac01ab3d`、`3981d9b19c8243db8318dd7883c0ae5f`）。

## 其余问题速览

**30+ 个工具中绝大多数可用，但 hole 的基准面定位、rib 两条链路也存在确定性失败，另有若干接口设计问题**

---

## 一、测试覆盖矩阵

| 类别 | 工具 | 结果 |
|---|---|---|
| 信息类 | check_update / check_environment / lookup_constants / list_jobs / session_status / startup_status | ✅ 全部通过 |
| 信息类 | **capabilities** | ⚠️ 可用但输出 97KB 超客户端限制（问题 7） |
| 信息类 | **list_models** | ⚠️ 可用但 limit=5 仍返回 4.1MB（问题 7） |
| 零件 | new_part / create_sketch / extrude / revolve / sweep / loft / chamfer / shell / draft / mirror / dimension_pattern / set_parameters / set_sketch_dimensions* | ✅ 通过（*未单独触发因 set_dimensions 失败链） |
| 零件 | **hole** | ❌ 基准面参考失败，仅边参考可用（问题 1） |
| 零件 | **rib** | ❌ 两种 flip 均失败（问题 2） |
| 零件 | **set_dimensions** | ❌ Toolkit 失败，落入 blend 上下文（问题 3） |
| 零件 | **set_relations** | ❌ 同问题 3 |
| 计划 | execute_plan（sketch+extrude+断言） | ✅ 通过，volume_mm3 断言精确生效 |
| 计划 | execute_plan 内嵌 **hole op** | ❌ 无法引用计划内生成几何（问题 5） |
| 快速件 | create_plate | ⚠️ 建模成功，但不返回 model_id 且不注册 list_models（问题 6） |
| 装配 | new_assembly / assemble_component / remove_component | ✅ 通过 |
| 高级 | dump_feature_tree / reorder_features / save / export(STEP/PDF) / refresh_model | ✅ 通过 |
| 钣金 | new_sheetmetal / sheetmetal_wall | ✅ 通过 |
| 钣金 | **sheetmetal_flat_pattern** | ⚠️ 真实面 ID 可用；fixed_surface 传 id=0 直接 Toolkit -23，报错不友好（问题 9） |
| 工程图 | new_drawing / drawing_view / note / table / dimension / delete / export pdf | ✅ 全部通过 |
| UDF | inspect_udf | ⚠️ 本机无 .gph 库，仅验证了路径校验分支（正常拒绝非 .gph） |

---

## 二、其余问题清单（按严重度）

### P1-1 creo_hole 使用基准面（datum_plane）作线性参考时稳定失败
- **现象**：placement=顶面 surface(id=58)，reference1/2 分别尝试 `RIGHT+FRONT`、`RIGHT+TOP` 组合，均报
  `Regeneration produced a failed, suppressed or incomplete feature`（toolkit_code=-1），随后自动回滚。
- **可用路径**：改用两条实体边 `{kind:'edge',id:N}` 作参考后一次成功，体积精确吻合
  （24000 − π·4²·10 = 23497.35 mm³，实测 23497.345）。
- **影响**：基准面参考是孔定位最常用方式，现在等于强制要求先有合适的实体边。
- **建议**：修复 datum plane 参考在 hole element tree 中的装配方式；若短期难修，请在工具描述与 capabilities 中明确“仅支持边参考”，避免用户反复试错。

### P1-2 creo_rib 完全不可用
- **现象**：在 XZ 面创建开放轮廓（一条竖线 + 一条斜线，端点落在实体边界上）后调用 rib(thickness=3)，
  `flip=false` 与 `flip=true` 两种方向都报同样的 `Regeneration produced a failed, suppressed or incomplete feature`。
- **影响**：rib 功能当前无法使用。
- **建议**：检查 profile rib 的 element tree（材料侧 / 草图平面法向 / 深度侧）；错误信息目前无法区分“草图无效”“材料侧错误”“几何不相交”，建议增加前置校验。

### P1-3 set_dimensions 失败（即核心问题，此处保留细节）
- **现象**：对 inspect 返回的孔位置尺寸 d13(id=13, 30→40) 调用 set_dimensions，报
  `Toolkit operation failed; inspect native.log and its element error list`。
- **关键线索**：失败 job 的 native_log_tail 末尾出现
  `PHASE=activate_blend_context → ExportBlendFeatureInfo → RestoreFeatureInfoDirectory`，
  与历史遗留的 `unknown_outcome` 超时 job（stage=activate_blend_context）完全同路径。
  **说明"修改尺寸"操作被误导入 Blend 特性上下文**，疑似所有"非建模类 Toolkit 操作"共用的激活逻辑有 bug（详见文档开头"核心问题"节）。

### P1-4 set_relations 同样失败（同核心问题路径）
- **现象**：`lines=["D13 = 40"]`（尺寸符号来自 inspect），同样 Toolkit 失败 + activate_blend_context 日志。
- **建议**：同 P1-3，属同一根因的可能性大。

### P2-5 execute_plan 中的 hole op 无法引用计划内生成的几何
- **现象**：plan = [sketch, extrude, hole]，hole 的 `placement:{kind:'surface',id:0}`、`reference edge id:0/1`
  在执行时报 `ProModelitemInit(...)=-23 → BUILD_FAILED`。
- **根因**：sketch/extrude 可以用 label 相互引用，但 hole 的 placement/reference 只接受执行前就不可知的数字 ID，
  plan 内没有“引用本计划第 N 步生成的面/边”的语法。
- **影响**：一次成型（草图→拉伸→打孔）的核心场景跑不通，必须拆成多次调用。
- **建议**：为 hole 增加 label 式几何引用（如 `{kind:'plan_surface', of:'plan_ext', ordinal:0}`），
  或允许 hole 像独立调用一样在 plan 完成后由服务端自动选择放置面。

### P2-6 create_plate 成功但不返回 model_id、不进入模型注册表
- **现象**：job succeeded、PRT 保存且校验通过，但响应 JSON 无 `model_id` 字段；
  之后 `list_models` 中找不到该板材（仅 3 个旧模型）。
- **影响**：create_plate 的产物无法被 assemble_component / execute_plan(assemble_component) 引用
  （后者需要 32 位十六进制 source_model_id），“快速生成板材再装配”链路断裂。
- **建议**：job 完成后把 model_id 写回 job 结果；或 create_plate 走统一模型注册流程。

### P2-7 大响应体积超出 MCP 客户端限制
- **capabilities**：返回 97,062 字符，直接超过客户端 token 上限，工具完全不可读。
  建议拆分：`capabilities` 返回摘要，详细证据走单独参数（如 `detail:"full"`）。
- **list_models(limit=5)**：返回 4.1MB——limit 只限制模型数量，但每个模型附带完整几何快照
  （全部 features/dimensions/surfaces/edges/aliases）。模型一多必然爆。
  建议默认 compact（仅 id/name/revision/status/体积），几何快照按需 `include_snapshot:true`。
- **inspect_model**：中等复杂度模型（37 特征）返回 137KB 同样超限。建议提供 `sections` 参数按需拉取。

### P2-8 装配宿主的报错指引缺失
- **现象**：误用 `creo_new_part` 的产物当装配宿主时，assemble_component 报
  `Assembly operations require an MCP assembly model`，但没有提示“应使用 creo_new_assembly”。
- **建议**：错误信息中直接指路正确工具；另建议 new_part 与 new_assembly 在工具描述中互相注明区别。

### P3-9 失败诊断噪音过大
- 每次失败返回的 `native_log_tail` 几乎全是例行 `ProSurfaceDataGet=0 / ProEdgeIdGet=0 / ProSurfaceContourVisit=0`，
  真正的错误只在末尾 2~3 行。建议服务端过滤例行日志，只保留错误上下文 ±10 行。
- 失败时 `result.inspection` 的 counts 全为 0，而模型实际已回滚成功——应返回回滚后的真实 inspection，
  便于确认模型状态。

### P3-10 sheetmetal_flat_pattern 参数校验不足
- `fixed_surface:{kind:'surface',id:0}`（明显非法）不在校验层报错，直落到 Toolkit -23。
  建议前置校验 surface id 存在性，或报错信息列出当前有效 surface id。
- 附带观察：sheetmetal_wall 成功后 inspect 出现 `body id=-5778 (state=3)` 的异常 body 条目，
  疑似钣金转换后的内部表示泄漏，建议过滤。

### P3-11 校验错误风格不统一
- 同一批工具，有的参数错误由 MCP 层 pydantic 返回（信息完整），有的由宿主 JSON-schema 校验返回
  （`root: must have required property 'angle'`），信息量与格式不一致，建议统一到一层。
- `creo_reorder_features` 要求 before/after 二选一，缺省时到 op 层才报
  `Supply exactly one of before or after`，可前置到参数校验。

---

## 三、正面反馈（本次实测验证的亮点）

1. **体积校验精度优秀**：base extrude 24000.000 / hole 后 23497.345 / revolve 增量 15707.96（=π(30²−20²)×10）/ loft 棱台 793.25，全部与理论值一致。
2. **execute_plan 的 volume_mm3 + require_solid 断言**按预期拦截并回滚。
3. **save 后 sha256、reload-and-verified 链路**在所有成功 job 上一致工作，审计友好。
4. **失败自动回滚**（rollback_succeeded=true）在 hole/rib/set_dimensions 失败场景均正确恢复。
5. dimension_pattern（按 d13 步进 8×4）一次成功；chamfer/shell/draft/mirror/sweep/loft 全链路稳定。
6. 工程图链路（视图/注释/表格/尺寸/删除/PDF 导出）完整可用。

---

## 四、复现环境与产物

- 测试模型：`mdtest_full_chain`（60×40×10 底板 + 孔/倒角/抽壳/拔模/旋转/扫描/放样/镜像/阵列）、
  `mdtest_asm_real`（装配验证）、`mdtest_sheet`（钣金）、`mdtest_drw`（工程图）
- 模型/作业根目录：`E:\WorkBuddy Space\MCP MCP_CREO_MechDog\`
- 典型失败 job_id（供作者核对日志）：
  - hole 基准面参考：`c5ab4301a88c4a778c47f1406dfe0453`、`f450c491acd34f1ca03bf8b0484a394b`
  - rib：`7d6096c64fba473a974b74c88b44babc`、`2f16c33e6be74e978a5039384863138f`
  - set_dimensions：`b2f560e244af4f1292f6f265ac01ab3d`
  - set_relations：`3981d9b19c8243db8318dd7883c0ae5f`
  - execute_plan+hole：`1e975c5d0f3c47979bc02ea223f07248`
  - flat_pattern id=0：`8d9827ce3bd94c2f9f38190c58cd9e48`

> 以上 job 目录内均含 native.log 全文，可直接定位。核心问题复现 job：`b2f560e244af4f1292f6f265ac01ab3d`（set_dimensions）、`3981d9b19c8243db8318dd7883c0ae5f`（set_relations）。
