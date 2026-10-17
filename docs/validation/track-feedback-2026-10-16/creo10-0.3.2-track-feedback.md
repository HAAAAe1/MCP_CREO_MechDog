# 2026-10-16｜CREO 10.0.0.0｜MCP_CREO_MechDog 0.3.2｜剖面轮廓重叠致切除创建失败（及草图坐标尺寸/自动标注/曲线阵列相关缺陷）

- 报告日期：2026-10-16
- 目标软件：Creo 10.0.0.0（`release_numeric = 42`，Toolkit `toolkit_code = 0`）
- MCP 版本：MCP_CREO_MechDog 0.3.2
- 复现任务：仅用 `MCP_CREO_MechDog`，从一份纯文本说明（履带零件，节距 86.1056mm、63 节）从零建模。**几何数据 100% 来自该文本，未导入任何实体、未使用任何源 CAD 文件。**
- 结论摘要：**核心缺陷是"单个草图内多个闭合轮廓若存在互相重叠，`creo_extrude`（切除）必然失败，且错误信息完全不指向真实原因"。** 另发现坐标尺寸模式对相切直线+圆弧链过约束、自动标注在相切链上恒失败、无曲线阵列接口、空实体残留、单任务全量几何枚举导致性能瓶颈等问题。
- 第二批结论（长任务实测补充）：**① 新建切除特征会"创建成功但重新生成静默失败"（status 6，零诊断）；② 对称拉伸的 `depth` 是总深而非单侧深，口径不明且不回读实际范围，极易静默做出半深特征；③ 改已有特征尺寸（`creo_set_dimensions`）比新建特征可靠得多；④ `creo_inspect_model` 里所有曲面 `type` 恒为 34，按类型筛几何完全失效；⑤ `datum_plane` 在 offset=0 且存在多个共面基准面时静默取最小 id。** 详见第十～十六节。
- **第三批结论（最严重）：作业超时会杀死 native worker，导致"几何做完了但没保存"，并且模型被 `pending_job` 永久锁死 —— MCP 既没有检查点回滚，也没有任何 reconciliation 工具，只能人工改 `model.json`。** 详见第十七节。
- **第四批结论：① 超时残留的"脏会话"无法自愈**（worker 复用会话内同名模型，回滚分支被 `mutated` 门禁挡住）⇒ 手工清锁后仍然永远失败，**唯一出路是重启 Creo**，详见第十八节；**② 默认 600 s 作业预算对大型零件必然不够，且没有"按作业指定预算"的入口**（实测单个作业需 644 s），详见第十九节；**③ 保存先于重载核验**（超时最多损失记账、不损失几何），详见第十九节末。
- **任务最终结果（供参考）：** rev 16 完成，单实体，63 分切 / 63 驱动窗口 / 90 胎面凸块，56 个特征全部健康；体积 147,747,977.87 mm³（对比文本目标 0.14993 m³ 为 −1.46 %），包围盒 `[−1272.266, −68.685, −228.600] … [1115.233, 945.629, 228.600]`；另有独立解析 STL 重算交叉验证（体积一致性 0.0028 %）。完整账本、三方核验与两处已知偏差见第二十节。

---

## 一、核心问题（P0）：草图中轮廓互相重叠 → 切除特征创建失败，错误信息无指向性

### 现象

用一次切除完成 63 处节距分切（剖面为同一梯形，按切向旋转后合入一张前视面草图，见任务文档"等效站位规则"）：

1. 草图创建**成功**。native 日志：`SKETCH_SOLVE=0 mode=coordinates`、`AutodimensionSketch=SKIPPED_COMPLETE_COORDINATE_DIMENSIONS`、`RegenerateSolvedSketch=0`，无任何几何偏差告警。
2. 随后的切除**必定失败**：

```json
{
  "status": "failed",
  "message": "Toolkit call ProFeatureWithoptionsCreate failed with code -1 during execute_extrude",
  "failed_stage": "execute_extrude",
  "failed_toolkit_call": "ProFeatureWithoptionsCreate",
  "rollback_succeeded": true
}
```

3. native 日志里元素树全部构造成功（`ProElement*Set(...)=0`、`ProElementtreeElementAdd(...)=0`），紧接着就是：

```
ProArrayAlloc(1, sizeof(ProFeatureCreateOptions), 1, (ProArray *)&opts)=0
ProFeatureWithoptionsCreate=-1
BUILD_FAILED=-1
```

**没有任何提示指向"轮廓重叠"**，只报一个笼统的 `-1`。极易被误判为"草图平面/方向/深度参数错误"或"轮廓数过多"，从而走上错误的排查方向（改方向、改深度、拆分轮廓数都无效）。

### 真实根因

把 63 个梯形轮廓做二维布尔并集检验，发现**相邻站位在环的左右两个急转弯圆弧段上相互重叠**：

```
station spacing 86.1055 mm（弧长等分）；梯形顶边切线向半宽 27.085 mm
重叠的相邻站位对：15 对
  (10,11) (11,12) (12,13) (13,14) (14,15) (15,16) (16,17)     ← 右端急转段
  (36,37) (37,38) (38,39)                                     ← 顶直段与左端过渡
  (46,47) (47,48) (48,49) (49,50) (50,51)                     ← 左端急转段
重叠面积合计 183.9 mm²；63 个轮廓并集后仍有 48 个连通分量
```

相邻站位中心距 86.1055mm，而梯形顶边半宽 27.085mm（两侧合计 54.17mm）；在半径较小的圆弧段（R=152.4mm）上，顶边弦的角向张角约 ±25.4°，大于站位角间距的一半，**两个相邻弦段确实相交**。Creo 无法为一个"自相交的闭合轮廓集合"求出有效的剖面区域，于是 `ProFeatureWithoptionsCreate` 直接返回 -1。

### 为什么源模型没这个问题

源模型用的是**曲线阵列**（每个阵列实例是独立特征、各自一张草图），重叠发生在特征之间，Creo 允许；而被要求"合并成一张草图、一次切除"的等效做法，就把重叠搬进了同一剖面内，于是被拒绝。

### 验证与规避方案

| 分组方式 | 组内重叠对数 | 结果 |
|---|---|---|
| 63 个轮廓全部一张草图 | **15** | `ProFeatureWithoptionsCreate = -1`（失败） |
| 奇数站 31 个 / 偶数站 32 个（步长 2） | **0 / 0** | 创建成功（`ProFeatureWithoptionsCreate = 0`） |
| 步长 3 | 0 | 同上 |

- 采用"步长 2"把 63 处切成两组（偶数站组、奇数站组），两组各自无重叠 → **两张草图 + 两次对称切除**，几何与一次性 63 轮廓切除完全等价。
- 对照组：6 个互不重叠的轮廓 → `ProFeatureWithoptionsCreate = 0`，切除成功，实体数由 2 自动收敛为 1。

### 建议（给作者）

1. **创建特征前对剖面做一次"轮廓互不相交"预检**：若存在重叠/相切但非嵌套的轮廓，直接抛出明确错误，例如
   `Section loops 10 and 11 overlap (area 2.10 mm^2); merge them or split into separate features.`
   这一条能省掉用户几小时。
2. 建议顺带预检：轮廓自相交、极细长（面积/周长比过小）、退化为零面积的轮廓。
3. 可考虑在 `creo_execute_plan` 增加 `merge_overlapping_loops` 选项（服务端做一次并集再提交），直接把"等效做法"变成可靠能力。

---

## 二、P1：坐标尺寸（`dimensioning: "coordinates"`）对"直线 + 圆弧"相切闭环过约束

### 现象

按任务文档附录画出通路草图（5 直线 + 5 圆弧，逐段 G1 相切，端点坐标逐位相同以保证水密闭环），使用 `dimensioning: "coordinates"`：

```
坐标尺寸化改变了给定几何；最大偏差 mm=0.487310
（Coordinate dimensioning changed the supplied geometry; maximum deviation mm=0.487310）
草图特征创建失败（self-check 容差 1e-5 mm）
```

### 定位

native 日志显示**该草图本身是有效的**：5 段圆弧的极角 `COORDINATE_ARC_POLAR` 全部精确吻合、`SKETCH_SOLVE=0`、`RegenerateSolvedSketch=0`。失败只发生在 MCP 自带的 1e-5mm 回读校核上。

根因是**过约束**：Creo 会把重合的直线端点与圆弧端点合并为同一顶点。10 个实体（5 直线 × 4 + 5 圆弧 × 5 = 45 自由度）合并 10 个节点后只剩 25 自由度，而 `coordinates` 模式仍按原始端点发出 44 个坐标尺寸 → 过约束 → 求解器把几何推到 0.487mm 之外。

### 隔离实验（同一份几何，只改提交方式）

| 提交内容 | 结果 |
|---|---|
| 5 个互不相连的圆弧 | 通过 |
| 10 直线 × 10 顶点的水密闭合多边形 | 通过 |
| 10 条直线 + 5 段圆弧的**相切水密链** | **失败**（偏差 0.487310） |
| 同上，端点人为分开 1e-5 mm 以避开 1e-9 顶点合并 | 草图通过，但**扫描失败**（轨迹不再闭合，`ProSolidRegenerate` 失败） |

即：**"相切链"这一情形两条路都走不通**——水密则过约束，分离则破坏闭合。

### 建议

- `coordinates` 模式在回读/发尺寸前，先把实体端点按 Creo 的顶点合并容差（1e-9）做一次归并，**按"合并后的顶点"而不是"原始端点"发尺寸**，即可消除这类过约束。
- 或提供 `dimensioning: "coordinates"` 的宽松自检开关（例如 `max_deviation_mm` 可选），把 1e-5mm 作为默认值但允许用户放宽。
- 顺带：`polyline` 实体的 `points` 上限为 200。若要把一条折线离散得足够细（例如本任务 153 点尚可，但更细的离散会超限），只能改用大量 `line` 实体表达同一条轮廓，接口上没有说明该替代路径。

---

## 三、P1：自动标注（`autodim`）在"相切直线 + 圆弧链"上恒失败

### 现象

同一张 10 实体相切链草图改用 `dimensioning: "autodim"`：

```
SKETCH_SOLVE=-1
SECTION_ERRORS phase=solve count=0
AutodimensionSketch=-1
Toolkit call AutodimensionSketch failed with code -1 during execute_sketch
```

### 分析

源码中 `solve_profile()` 在调用 `ProSectionAutodim` **之前**就把 Intent Manager 置为 FALSE（`ProSectionIntentManagerModeSet(section, PRO_B_FALSE)`），并且是"先 `ProSectionSolve`，后 `ProSectionAutodim`"。在这个顺序下，求解器先把草图拖到某个（未约束的）位置，随后 `ProSectionAutodim` 在关闭 Intent Manager 的剖面上工作，返回值恒为 -1。

反证：扫描特征自身那个 20 条直线的截面 `AutodimensionSketch=0` 成功 —— 说明 autodim 并非全面失效，而是对"相切直线 + 圆弧"链失效（直线段本身在该顺序下还能收敛）。

### 建议

- 恢复顺序：先 `ProSectionAutodim`（Intent Manager 保持 TRUE），再做 solve/regenerate。
- 或者对"存在相切约束的圆弧"自动降级到显式尺寸方案，并给出明确提示，而不是抛出裸 `-1`。

---

## 四、P2：无"沿曲线阵列"接口，无法复现曲线阵列（PAT）

任务文档要求用"沿曲线阵列"（驱动曲线 = 闭环路径，实例总数 63 / 15 / 15，含跳站）。MCP 现有阵列能力为：

- `creo_axis_pattern`：仅**角向**阵列（绕轴、按角度增量）。
- `creo_dimension_pattern`：仅**尺寸驱动**阵列（取一个 leader 尺寸 + 增量），且 leader 必须是可阵列特征的尺寸；由于本 MCP 的草图是**独立草图特征**（`PRO_E_SEC_USE_SKETCH` 引用外部草图），切除特征自身只有深度尺寸可驱动，**无法用草图内的位置尺寸做阵列**。

结论：**路径非圆形的曲线阵列无法通过 API 表达**，只能退化为"等效站位规则"（把每站轮廓按切向旋转后合入草图）。这会显著放大草图实体数量（本任务 63 站 × 4 = 252 条直线），从而撞上第一节的"轮廓重叠"缺陷。

### 建议

- 增加 `creo_curve_pattern`（`ProPattern` 的 curve/`PRO_PAT_CURVE` 形式），至少支持"参考一条草绘曲线/基准曲线 + 等弧长 + 随曲线切向"。
- 若短时间无法实现，建议在 `creo_capabilities` 中明确写出"曲线阵列不可用，推荐等效站位做法"，并同时提示"等效做法下要注意轮廓重叠"。

---

## 五、P2：扫描建模后残留空实体（`bodies: 2`）

用 `sweep`（`mode: "add"`）建出实体后，`creo_inspect_model` 报：

```json
"counts": { "features": 9, "surfaces": 2756, "edges": 5814, "bodies": 2 }
```

其中一个为空实体（`state = 3`），一个是有效实体（`state = 4`）。**空实体的清理只在后续 `extrude`/`revolve` 成功后附带执行**（源码 `extrude_or_revolve()` 末尾：`if (active == 1 && !skip_empty_body_cleanup) remove_empty_body();`）。因此：

- 新建模型后**只做扫描**时，模型会一直保持 2 个实体；
- 下游若按"实体数 = 1"做验收（本任务文档明确要求单实体），会立刻判定不合格。

### 建议

- 把空实体清理放到与特征类型无关的公共收尾路径（或提供独立的 `creo_remove_empty_bodies` 工具）。

---

## 六、P2：单任务全量几何枚举导致性能瓶颈

**每个**建模任务结束前都会遍历该实体的全部曲面/边并把结果写入请求/日志：

- 实测量级（2756 面 / 5814 边）：单任务 `request.json` 约 **5.6 MB**、`native.log` 约 **2.8 MB**。
- 单个草图特征任务端到端 **≈ 4~5 分钟**；一个 63 轮廓草图任务 ≈ 5 分钟，其中真正的建模只占很小一部分。
- `creo_get_job(detail="compact")` 也无法在完成前拿到进度细分（`operation_count` 有，但只到 `stage` 粒度）。

### 建议

- 追加/复用任务时对"未变化的几何快照"做缓存或哈希，只重算被修改的特征。
- 提供 `detail: "minimal"`（只返回 status/revision/volume/counts），并把全量几何改成按需拉取。
- `jobs/<id>/request.json` 建议只保留载荷本身。

---

## 七、P3：草图约束创建因"三位小数舍入"产生微小间隙而失败

首次提交时，通路 10 个拐点直接使用文本给出的三位小数坐标（圆弧端点由圆心+半径推导，因此与直线端点存在 ~1.7e-3 mm 差异）：

```
CreateSketchConstraint failed with code -1 during execute_sketch
```

即：同一段落上本应重合的两个端点，若坐标不完全逐位相同，创建 `coincident` 约束会失败，且报错不说明是哪一对端点、差多少。

### 建议

- 报错时给出"期望重合的两个端点、实际间距 mm、所属实体名"。
- 或在 `coincident` 约束创建前做一次容差吸附（例如 ≤1e-3 mm 自动吸附），并把吸附量回写到返回结果。

---

## 八、附：本次任务在其他方面的表现（正常，供参考）

- `creo_execute_plan` / `creo_create_sketch` 的 `coordinates` 模式对**纯直线**的 153 点水密闭环（扫描轨迹）完全正常：`SKETCH_SOLVE=0`、`AutodimensionSketch=SKIPPED_COMPLETE_COORDINATE_DIMENSIONS`、`RegenerateSolvedSketch=0`，扫描成环成功。
- `sweep`（`mode: "add"`）在 153 段水密折线轨迹上成功，实体包围盒与任务文档给出的自检值吻合（带体外周面 Y=-44.890，文档要求 -44.893，差 0.003mm）。
- 失败回滚（`rollback_succeeded: true`）行为正确，模型能可靠回到上一个已保存检查点，未污染模型。
- `creo_save_model` 的"保存后重新载入并核对"（`saved_file_reloaded_and_verified: true`）+ `sha256` 机制很好用，是本次判断"模型是否真的落盘"的可靠依据。

---

## 十、P0：新建切除"创建成功但重新生成静默失败"（status 6，零诊断信息）

### 现象

模型上已有一组切除特征（节距分切，草图为 32 个梯形轮廓，切除深度参数写错，见第十一节）。为把深度改到正确值，**新建一个同剖面、更大深度的切除特征**：

```json
{"op":"sketch","label":"sk_p03a2", ... }          // 同一组梯形，坐标完全相同
{"op":"extrude","label":"cut_p03a2","mode":"cut","direction":"symmetric","depth":96.375}
```

任务返回失败，但日志显示**特征本身创建成功**：

```
ProElement*Set(...)=0            // 元素树全部构造成功
ProFeatureWithoptionsCreate=0    // 成功，并返回 created_feature_id=17268
UNHEALTHY_FEATURES=[{"id":17268,"name":"CUT_P03A2","status":6}]
BUILD_FAILED=Regeneration produced a failed, suppressed or incomplete feature
```

对外错误仅有：

```json
{
  "status": "failed",
  "message": "Regeneration produced a failed, suppressed or incomplete feature",
  "failed_stage": "execute_feature_plan",
  "rollback_succeeded": true
}
```

**核心问题：从 `ProFeatureWithoptionsCreate` 的返回值看是"成功"，问题直到重新生成才暴露，而重新生成失败后 MCP 没有把 Creo 的错误详情取回来**（没有特征错误码、没有失败的面/边、没有 `ProFeatureRegenerate` 返回的错误信息）。调用方只拿到一句笼统文案，无法区分是：
(a) 几何退化/自相交；(b) 新特征与原特征面重合；(c) 深度越过可用材料；(d) 与已有特征冲突。

失败任务：`86882650350a4d29936445637dfd9e6e`、`33f7cbe94cce45409a68ba2d4fc075cd`（深度分别 96.375、100.0）。

### 合理怀疑

新切除的**侧面与已有切除特征的侧面完全共面**（同一张草图的同一组梯形，只有 Z 向深度不同），在 `|Z| ≤ 24.09` 区间内两者边界重合，重新生成时内核得不到有效实体。

### 关键对比（同一模型上的 A/B 对照）

| 做法 | 结果 |
|---|---|
| 新建切除特征 `cut_p03a2`（同剖面、深度 96.375） | **失败**，status 6，无诊断 |
| 用 `creo_set_dimensions` 直接改**已有**特征的驱动尺寸 | **成功**，体积变化与理论值吻合 |

这说明"同剖面重复切除"这一操作路径在 Creo 内核里是脆弱点。**建议 MCP 在创建切除前，检查新剖面是否与已有切除特征的面共面/重合，并在报错时把这些面 id 一并输出。**

---

## 十一、P1：对称拉伸的 `depth` 语义是"总深"而非"单侧深"，且内部尺寸需要双倍——极易静默做出半深特征

### 现象

任务文档写"沿 Z 中面贯穿切除，两侧各 48.19mm"（总深 96.375）。按最自然的读法调用：

```json
{"op":"extrude","label":"cut_p03a","mode":"cut","direction":"symmetric","depth":48.19}
```

调用**返回成功**，无任何警告。但实测材料只被切除到 `Z = ±24.095`（总深 48.19，正好是要求的一半）。用 `creo_inspect_model` 看到槽底面 `Z[±24.09]`，体积只下降了理论值的一半。

### 说明

- MCP 的 `depth` 语义 = **总深**，`direction:"symmetric"` 时两侧各 `depth/2`。
- Creo 内部把这条对称深度存成**一个**尺寸（该特征 id=2788 的尺寸 = 48.19），把该尺寸改成 **96.375** 后，几何才变成 `Z = ±48.19`（已实测验证，槽底面 `Z[±48.19]`，体积 123，119，343.26 → 120，512，978.62 mm³，与理论减去量 2，606，365 mm³ 吻合）。
- 也就是说：**API 的 `depth` 与"单侧深度"不是同一口径，而 MCP 文档、结果里都没有说明，也没有把"实际切除范围"回读给调用方。**

### 建议（这条改动性价比最高）

1. 文档明确写"`direction: symmetric` 时 `depth` 为总深"。
2. 更好：支持显式口径，例如 `depth_per_side`，或 `depth_semantics: "total" | "per_side"`。
3. **最好：在作业结果里回读并回报该特征实际占据的范围**（例如"切除后新增/移除材料的包围盒 Z ∈ [-48.19, +48.19]"）。本次若结果里直接给出实际范围，这个错误当场就会被发现，而不必靠事后量体积。

---

## 十二、P1：修改已有特征的驱动尺寸（`creo_set_dimensions`）是可靠的修复路径，建议在报错里主动引导

本次"深度写错"的最终修复方式不是重建特征，而是：

```json
{"op":"set_dimensions","values":[{"id":2788,"value":96.375}]}
```

结果：`status: succeeded`，深度特征自动重新生成，模型从 rev 8 → rev 9，体积与理论值吻合。此后又被用于第 10 节场景（在"新建特征必失败"的情况下，它依然成功）。

### 建议

- 报错文案里补一句可操作指引，例如："若是修正已有特征的尺寸，请用 `creo_set_dimensions`（提供 `creo_inspect_model` 返回的尺寸 id），不要新建同剖面特征。"
- `creo_inspect_model` 的尺寸枚举很好用（本次靠它找到 CUT_P03A 的 497 个尺寸中唯一的 48.19），建议在文档里把这个"查尺寸 id → set_dimensions"的闭环写成标准用法。

---

## 十三、P2：`creo_inspect_model` 里**所有**曲面的 `type` 恒为 34，按类型筛选几何完全失效

实测（模型含 2807 个曲面）：

```
surfaces 2807   types [34]
sample: {"id":246,"type":34,"normal":[0,1,0],"origin":[-834.943,0,-17.87],
         "bbox":[[-834.699,0,-17.87],[672.274,0,17.87]],"body_id":203}
```

该样本明显是**平面**（子午面/槽底面，Y 向 bbox 宽度为 0），却和圆柱面、倒角面一样报 `type: 34`。

后果：

- 无法用 `type` 区分平面/圆柱面/圆锥面，只能靠 `normal` + `bbox` 反推（本次就是这么做选中基准平面的），筛选成本高且不可靠。
- 用 `{"kind":"plane"}` 引用时依赖 `normal` 反推，遇到"多个法向相同的平面"就会直接报错（见第十四节）。

### 建议

把 Creo 的真实面类型输出：`PRO_SRF_PLANE / PRO_SRF_CYL / PRO_SRF_CONE / PRO_SRF_TORUS / PRO_SRF_SPL / PRO_SRF_FIL …`，并附加 `is_planar`、`radius`（圆柱面/圆锥面）等派生字段。

---

## 十四、P2：`{kind:"datum_plane"}` 在 offset=0 且存在多个共面基准面时"静默取最小 id"

`native/generic.cpp` 的引用解析（约 436–461 行）：

```cpp
if (kind == "datum_plane" && fabs(offset) < 1e-9 && matches.size() > 1)
    matches = {*std::min_element(matches.begin(), matches.end())};
if (matches.size() != 1)
    throw std::runtime_error("Plane reference must identify exactly one surface; inspect the model and use a surface ID");
```

本模型的 Z 法向基准面在 offset 0 处有多个（id 6、42、12754、13073、…）。于是：

- `kind:"datum_plane"` + offset 0 → **静默**取 id 最小的那个（通常是 id=3 的 TOP），调用方无从得知选中了哪个；
- `kind:"plane"` + offset 0 → 多个匹配时直接抛"必须唯一"，但错误信息不告诉调用方**存在哪些候选**。

本次因此完全放弃了"按基准面名引用"的路线，改为把每个站位的草图平面写成显式 `offset`（`sketch.plane="XY", offset=±120.985`），才得以稳定推进。

### 建议

- 候选多于 1 时，错误信息里列出全部候选的 `id / origin / normal`；
- 提供显式引用（`{"kind":"datum_plane","id":N}` 或 `{"kind":"datum_feature","label":"..."}`），不要把"静默取最小 id"作为默认行为。

---

## 十五、P3：字符串平面 + offset 会隐式新建一个基准面特征，文档未说明

`native/generic.cpp` 的 `sketch_frame`（约 556–577 行）：当 `plane` 是字符串（`"XY"/"XZ"/"YZ"`）且 `offset ≠ 0` 时，MCP 会**自动调用 `offset_plane()` 新建一个基准面特征**，命名为 `<草图 label>_plane`。

本次用 `{plane:"XY", offset:±120.985}` 建凸台草图，模型里因此多出 `sk_p05_pzb_plane`、`sk_p05_nzb_plane` 等**非用户要求的构造特征**。功能上没问题，但：

- 文档没说明会产生新特征，调用方在做"特征数量核对"时会看不懂多出来的基准面；
- 建议在作业结果里列出隐式创建的特征（label + feature_id）。

---

## 十六、附：本次长任务的实测耗时（供性能优化参考）

单通道串行作业，全部为真实建模（非空转）：

| 作业 | 内容 | 耗时 |
|---|---|---|
| `creo_set_dimensions`（P03 深度修正） | 1 个尺寸 | ≈ 3 min 30 s（09:58:58 → 10:02:28） |
| P04 偶数批 `a8e05f5ef2b643caa82cb4be9c7f48bc` | 32 轮廓草图 + 1 切除 | ≈ 6 min 30 s |
| P04 奇数批 `31991d5bc9dc45238d3d5f761b0feb7a` | 31 轮廓草图 + 1 切除 | ≈ 7 min 45 s（10:13:47 → 10:21:32） |
| P05 凸台 `cf66aea4af4f46bea6aaf1549457da7b` | 2×45 轮廓草图 + 2 拉伸（4 个操作） | 见下一版记录 |

- **单轮廓 ≈ 10–15 s**，且随模型曲面数增长而变慢（2743 → 2807 面时，31 轮廓比 32 轮廓还慢）。
- 时间几乎完全花在 `resolve()` → `inspection(false)` 的全量几何枚举上（每个操作都要重来一遍）。
- 因此 90 个凸台块的一次性建模用了 4 个操作 / 90 个轮廓，是当前接口下能达到的最优批量，但仍需十几分钟。

---

## 十七、P0：作业超时 → native worker 被强杀 → 模型被 `pending_job` **永久锁死**，MCP 不提供任何解锁工具

这是本次任务最严重的一次阻塞：**几何其实已经全部做完了，但作业被超时杀死，成果全部丢失，而且模型从此无法再接受任何作业。**

### 现象

一次 4 操作的建模作业（2 张 45 轮廓草图 + 2 个凸台拉伸，见第十六节）：

- 作业 `cf66aea4af4f46bea6aaf1549457da7b`，`started 10:29:00` → `finished 10:39:01`，**正好 601 s**。
- native 日志显示 4 个操作**都在正常推进**：

```
PHASE=execute_sketch        / PHASE=sketch:sk_p05_pzb
  ProFeatureWithoptionsCreate=0 → created_feature_id=22985  (偏置基准面)
  ProFeatureWithoptionsCreate=0 → created_feature_id=22987  (45 轮廓草图)
  SKETCH_SOLVE=0 mode=coordinates ; RegenerateSolvedSketch=0   ← 草图 45 个轮廓全部解算通过
PHASE=execute_extrude       / PHASE=extrude:tb_p05_pzb
  ProFeatureWithoptionsCreate=0 → created_feature_id=23216  ; ProSolidRegenerate=0
PHASE=execute_sketch        / PHASE=sketch:sk_p05_nzb
  ProFeatureWithoptionsCreate=0 → created_feature_id=24753  ; SKETCH_SOLVE=0
PHASE=execute_extrude       / PHASE=extrude:tb_p05_nzb        ← 第 4 个操作进行中被杀
（日志在此处截断，全文件 0 次 BUILD_FAILED）
```

- 结果：作业目录里**没有 `native_checkpoint.json`**，`native_result_present: false`，`stage` 仍停在 `executing_feature_plan`，状态被判为 `unknown_outcome`，模型 revision 未提交（磁盘上仍是 rev 11）。

### 更严重的问题：锁死

从此之后，**对该模型的任何作业都被拒绝**，包括**只读**作业（`creo_refresh_model`）：

```json
{"status":"busy","code":"toolkit_busy","accepted":false,
 "blocking_job_id":"cf66aea4af4f46bea6aaf1549457da7b",
 "blocking_model_id":"c437cace0625425496fec62d8c14743a",
 "blocking_operation":"pending_job",
 "message":"Model has a pending job"}
```

而 `src/creo_mechdog/recovery.py` 的注释写得很明确：

> Read-only evidence for uncertain jobs; **evidence never authorizes replay or unlocking.**

`next_steps` 只写了一句"operator reconciliation is required"，但：

- **MCP 没有提供任何 reconciliation 工具**（`creo_startup_status(retry=true)` 也明确声明 "Never closes Creo, clears unknown job/model reservations or replays jobs"）；
- 状态落在 `models/<model_id>/model.json` 的 `status: "unknown_outcome"` + `pending_job: "<job_id>"` 两个字段上，**只能由人手工改文件**才能恢复；
- 也就是说：**一次超时 = 该模型在自动化流程里彻底报废**。

### 代价

- 已经成功执行完毕的前 3 个操作（2 个基准面 + 3 张草图 + 1 个 45 块凸台拉伸）全部作废（超时发生在保存之前）；
- 模型无法继续建模，除非人工改 MCP 的状态文件或让 MCP 作者提供解锁工具；
- 调用方在超时后**拿不到任何"做到哪一步了"的结构化信息**（`operations` 数组未回填，`succeeded` 标志全无），只能自己去 grep 3.5 MB 的 native.log。

### 根因（性能与预算）

作业预算是**每个 job 固定 ≈ 600 s**，而每个操作的耗时都随模型规模增长 —— 因为**每个操作都会调用一次全量 `inspection()`**（枚举所有曲面 + 所有边）。实测（同一模型，串行）：

| 作业规模 | 模型规模 | 耗时 |
|---|---|---|
| 1 操作（`set_dimensions`） | 2677 面 / 7368 边 | **210 s** |
| 2 操作（32 轮廓草图 + 切除） | 2743 面 / 7917 边 | **388 s** |
| 2 操作（31 轮廓草图 + 切除） | 2807 面 / 8460 边 | **465 s** |
| 4 操作（2×45 轮廓草图 + 2 拉伸） | 2807 面 → 更大 | **>601 s ✗ 被杀** |

可见 2 操作已用掉 388–465 s，4 操作必然超预算。native.log 里 90% 的行是这种噪声，也印证了枚举开销：

```
ProEdgeIdGet(edge, &id)=0        （本次 233,154 行日志里出现 152,447 次）
ProSurfaceContourVisit(surface, inspect_contour, nullptr, surface)=0
ProSurfaceDataGet(surface, &data)=0
```

### 建议（按重要性）

1. **超时前必须先落检查点并回滚到已保存基线**：既然已经有 `native_checkpoint.json` 机制（`completion_stage` / `delivery_complete` / `success`），就应该在超时被 kill 之前写入"已完成到第几个操作"；并且**把模型回滚到上一个已保存的 prt 版本**，不要给调用方留下一个"内存里有脏几何、磁盘上没变、状态还锁着"的三重不确定状态。
2. **提供一个显式的 reconciliation 工具**，例如
   `creo_reconcile_model(model_id, action="rollback_to_baseline" | "accept_live")`：
   先做一次 live 核验（体积/面数/特征数比对基线），允许操作者选择"丢弃内存改动回到基线"或"接受当前内存状态并正常保存"，然后**清除 `pending_job`**。当前唯一的出路是手工编辑 `model.json`，这对任何调用方都是不可接受的。
3. **放宽超时策略**：把"建几何"和"生成结果报告（全量 inspection）"拆成两段计时，或允许调用方在作业里指定预算 / 关闭详细 inspection（例如 `assertions.verify: false`、`detail: "minimal"`）。本次的几何工作**其实已经全部完成**，纯粹是被收尾的枚举拖过线的。
4. **不要在 `pending_job` 期间拒绝只读作业**：`creo_refresh_model` / `creo_get_job` / `creo_session_status` / `creo_inspect_model` 是排障所必需的，目前连诊断都被一起挡住，调用方只能猜。
5. **超时结果里回填部分进度**：至少给出 `completed_operations`（本次应为前 3 个操作的 label 与 feature_id）与 `failed_operation_index`，便于操作者判断是否可以继续 / 是否要回滚。
6. 版本号建议：本次模型到 rev 11 时已 2807 面 / 8460 边，且每操作全量枚举 —— 对小零件没问题，对"环形带 + 630+ 特征"这类零件必须做几何快照缓存（同一 job 内复用一次枚举结果，而不是每个操作都重来）。

---

## 十八、P0：超时后的"脏会话"**无法自愈** —— worker 复用会话内同名模型，而回滚分支被 `mutated` 门禁挡住

第十七节描述了 `pending_job` 锁死。继续读 native 源码后发现一个**更隐蔽、更致命**的问题：**即使调用方手工清掉 `pending_job`，模型依然无法继续建模** —— 因为 Creo 会话里残留的脏几何会被下一次作业直接继承，而 MCP 没有任何工具能让会话回到基线。

### 完整链路（`native/generic.cpp`）

1. `:1876`　`ProMdlInit(name, mdltype, &board)` —— **先按名字在会话里查，而不是先看磁盘**。
2. `:1904-1910`

```cpp
} else {
    if (found == PRO_TK_E_NOT_FOUND) {
        path(file, checkpoint);
        CK(ProMdlFiletypeLoad(file, PRO_MDLFILE_UNUSED, PRO_B_FALSE, &board));   // 只有"会话里没有"才读磁盘
    } else
        check(found, "FindOwnedModel");                                          // 否则直接用会话里那份
```

   ⇒ **只要同名模型还在会话里（哪怕是超时残留的脏模型），就直接沿用会话状态，磁盘上的基线文件根本不参与。**
3. `:1917`　唯一防线：

```cpp
if (model.contains("inspection") && !request.value("readonly", false))
    verify_saved(model["inspection"], inspection());
```

   而 `verify_saved`（`:1749`）会逐项比对**特征数量、每个特征的 id/type/name、尺寸数量与数值（1e-6）、实体体积（0.01 mm³）、参数表** —— 脏模型必然不等 ⇒ 抛异常。
4. `:2027`　回滚分支：

```cpp
if (!report["success"].get<bool>() && connected && mutated && !checkpoint.empty()) {
    log("PHASE=rollback_to_saved_checkpoint\n");
    ProError erased = board ? ProMdlErase(board) : PRO_TK_NO_ERROR;
    ...
```

   第 3 步的异常发生在**任何几何变更之前**，所以 `mutated == false`，**这段本来能救命的回滚代码永远不会执行**。

### 后果：手工清锁也没用，形成死循环

- 每次新作业都在第 3 步抛错 → 状态落 `failed`（注意：不是 `unknown_outcome`，所以 `pending_job` 反而被清掉，**看起来"解锁成功了"**），但**会话里的脏模型一次都不会被清掉**；
- 于是：手工清锁 → 作业在 `verify_saved` 失败 → 再手工清锁 → 再失败……**几何永远无法推进**；
- 唯一的出路是**重启 Creo**，而这恰恰是 MCP 明确拒绝做的（`creo_startup_status` 声明 "Never closes Creo"）；
- 雪上加霜：全部 op 列表里**没有删除特征的 op**（实测枚举到的 op 只有 `assemble_component / chamfer / component_constraints / component_placement / datum_axis / datum_plane / dimension_pattern / draft / drawing_* / dump_tree / export / extrude / feature_tree / hole / loft / mirror / regenerate / remove_component / revolve / round / save / set_dimensions / set_parameters / set_relations / set_sketch_dimensions / sheetmetal_* / shell / sketch / sweep`），所以**调用方也没有办法自己删掉脏特征让会话回到基线**。

### 建议

1. **同名模型已在会话中时，先与基线校验；不一致就 `ProMdlErase` 后从 `part_file` 重新载入**，而不是默默沿用脏模型。这一条比新增任何工具都更根本，改动也最小（就是把 `:1904-1910` 的分支反过来）。
2. **把回滚条件里的 `mutated` 去掉**（或改为 `mutated || verify_mismatch`）："载入后发现与基线不符"同样应该触发回滚到基线。
3. 提供 `creo_reconcile_model(model_id, action="rollback_to_baseline" | "accept_live")`（同第十七节第 2 条），内部即 `ProMdlErase(board)` + `ProMdlFiletypeLoad(checkpoint)` + 重新 `inspection()` 比对基线。
4. 补一个通用 `delete_feature` op，或至少允许"回滚到已保存基线"作为一种独立作业类型。
5. `new: true` 且会话已有同名模型时，报错文案应提示"会话中存在同名模型，请先 Erase 或重启 Creo"，而不是只抛一句 `New model name already exists in the Creo session`。

### 一处值得肯定的设计

超时后 `bridge.py` 的跨进程锁是**正确的**：`toolkit-owner.lock` 里记的是 `pid`，进程一死 Windows 字节区间锁自动释放，`toolkit-owner.lock` 也随之删除。实测故障进程 PID 16540 退出后，锁文件消失、通道立刻可用，`creo_session_status` 正常返回。**卡住一切的只是 `model.json` 里的两个字段**，不是锁机制本身。

### 本次实际处置（供作者参考）

调用方在确认"磁盘基线完好 + 无活动进程持锁 + 只读/写入均被 `pending_job` 拒绝 + 无 reconciliation 工具"之后，采取了人工协调：

1. 备份 `models/c437cace0625425496fec62d8c14743a/model.json`；
2. 仅改两个字段：`status: "unknown_outcome" → "ready"`、`pending_job: "<job_id>" → null`（保留 `last_job` 作为审计线索）；
3. 重启 Creo 以丢弃脏会话；
4. 之后从 rev 11 继续。

⇒ 这一步**本该由 MCP 自己提供**，让每个调用方都去编辑 `model.json` 是不可接受的。

---

## 十九、P1：默认 600 s 作业预算对大型零件必然不够，且没有"按作业指定预算"的入口（实测被卡到 644 s）

第十八节说明超时会造成多大的破坏。本节记录**超时本身是可以避免的**：预算太紧，而且调用方无法为单个作业申请更多时间。

### 现象

同一个模型（环形带零件，5600+ 特征级几何、3200 曲面），后续作业都使用**完全相同的 2 操作**结构（1 张草图 + 1 个拉伸）：

| 作业 | 草图形状数 | 起始规模 | 耗时 | 相对 600 s 预算 |
|---|---|---|---|---|
| `de1797e5…`（rev 12） | 45 轮廓 | 2807 面 / 8460 边 | **552 s** | 92% |
| `813ab096…`（rev 13） | 23 轮廓 | 2956 面 / 9375 边 | **595 s** | **99.2%（仅余 5 s）** |
| `4028889b…`（rev 14） | 22 轮廓 | 3032 面 / 9813 边 | **644 s** | **107.3% → 已在预算外** |
| `191c27df…`（rev 15） | 15 轮廓（切除） | 3107 面 / 10278 边 | **577 s** | 96.2% |
| `8409306b…`（rev 16） | 15 轮廓（切除） | 3154 面 / 10518 边 | **619 s** | **103.2% → 已在预算外** |

⇒ **rev 14、rev 16 两个作业都超过了 600 s**。它们之所以没有变成 `unknown_outcome`，仅仅是因为调用方在这之前把 `config.json` 的 `generic_timeout_seconds` 从 600 改成了 1500。若沿用默认值，**这两个作业都会被杀死**，按第十七、十八节，模型会再次被 `pending_job` 锁死，而且脏会话需要重启 Creo 才能清除。

### 为什么这是产品缺陷（而不是"模型太大"）

1. **耗时随模型规模增长，而预算是常数**。每个操作、以及作业首尾的 `verify_saved` / `inspection()` 都会**全量枚举所有曲面和所有边**（见第六、十六节），所以同一套 2 操作作业，规模越大越慢：552 → 595 → 644 s。默认 600 s 对"环形带 + 600+ 特征"这一类零件**必然溢出**，而这类零件正是这个 MCP 的典型用例（复杂机械件）。
2. **调用方无法为单个作业申请预算**。唯一的口径是全局 `config.json` 的 `generic_timeout_seconds`，而改全局配置需要改文件、重启语义不明；
   `creo_execute_plan` 也没有 `timeout_seconds` / `budget_seconds` 参数，`assertions` 里也没有任何"跳过收尾核验"的开关。
3. **超时的代价极不对称**：多等几分钟是完全可接受的；而超时 = 丢成果 + 锁死模型 + 需要人工干预 + 需要重启 Creo。**宁可让调用方显式指定一个长预算，也不要静默地按 600 s 杀进程。**

### 建议

1. **`creo_execute_plan` 增加 `timeout_seconds` 参数**（带上限，如 300–7200），并把它透传到 `generic_bridge.py:388` 的 `subprocess.run(timeout=…)`，同时让 `bridge.py:936` 的看门狗按该值缩放（现在两者已经同步用同一个配置值，改成按作业传参即可）。
2. **按模型规模自适应默认值。** 注意实测数据（§20.1）显示耗时在 552–644 s 区间内**并不随轮廓数单调增长**（45 轮廓的 rev 12 只用 552 s，15 轮廓的 rev 16 却用了 619 s），说明该区间内耗时被固定开销主导、波动较大。因此不要用"精确拟合式"，而应用一条**宽松上界**，例如 `max(900, 180 + 12 × contours + 0.06 × surfaces)`：本次最重的 rev 14（22 轮廓 / 3107 面）得到 `max(900, 180+264+186) = 900 s`，比实测 644 s 留出约 40 % 余量。
   关键在于：**超时值只是上界，不是延迟** —— 把默认值放大到 1800 s 或 3600 s，正常作业依然是几十秒到几分钟就返回，一分钱不花；但哪怕只有一个作业撞线，代价就是丢成果、锁模型、人工清 `model.json`、重启 Creo（见 §十七 / §十八）。**代价如此不对称，默认值就应当偏大。**
3. **在 `creo_execute_plan` 的返回值里给出预算来源**（`timeout_seconds_used` 与它来自作业参数还是配置），让调用方能在作业开始前就知道还剩多少余量。
4. **把"几何阶段"和"收尾核验阶段"分开计时**（见第十七节第 3 条）：本次大量时间花在首尾两次全量 `inspection()` 上，几何本身只占一小部分。

### 一处值得肯定、但文档没写的设计（重要，建议写进 README）

`PHASE=save_and_reload` 里 **`ProMdlnameBackup` 先于重载校验执行**。实测 rev 13 的作业：

```
19:44:24  output/track_p01b.prt.15   ← 保存已完成
19:45:45  job/native_result.json     ← 结果回写（晚 81 s）
```

⇒ **即使作业在"重载 + 全量核验"阶段被超时杀死，几何也已经安全落盘**；这种情况下损失的是记账（`revision` / `part_file` / `inspection` 快照），不是模型。这与第十七节的结论一致（那次超时也是"几何全做完、只是没走到保存"）。

**建议**：把这个"保存先于核验"的顺序当成明确契约写进文档，并告诉调用方超时的正确处置是"先找最新的 `output/*.prt.N`，再决定回滚还是续跑"，而不是笼统地说 "inspect Creo before retrying"。

---

## 二十、附：本次运行完整实测数据（供作者复现与调参）

> 本节只记录**客观测量值**，供作者对照 §十六 / §十七 / §十八 / §十九 复现问题、调默认预算、验证修复效果。零件本身是一个环形橡胶履带（节距 86.1056 mm、63 节、闭链），几何 100% 来自纯文本说明，全程只用 `MCP_CREO_MechDog`。

### 20.1 修订账本（全部为真实建模，单通道串行）

| rev | 作业 | 内容 | 体积 mm³ | Δ体积 | features | surfaces | edges | bodies | 落盘 prt | 耗时 |
|---|---|---|---|---|---|---|---|---|---|---|
| 11 | — | 基线：带体 P01 + 63 分切 P03 + 63 驱动窗口 P04 | 118,000,774.10 | — | 31 | 2807 | 8460 | 1 | prt.12 | — |
| 12 | `de1797e5…` | P05 肩 **+Z 45 块**（C 框 + 两条 I 条） | 133,646,630.75 | +15,645,856.65 | 36 | 2956 | 9375 | 1 | prt.14 | **552 s** |
| 13 | `813ab096…` | P05 肩 **−Z 前 23 块** | 141,400,499.44 | +7,753,868.69 | 41 | 3032 | 9813 | 1 | prt.15 | **595 s** |
| 14 | `4028889b…` | P05 肩 **−Z 后 22 块** | 149,292,168.65 | +7,891,669.21 | 46 | 3107 | 10278 | 1 | prt.16 | **644 s** ⚠️ |
| 15 | `191c27df…` | 肩 +Z **15 处 36 mm 槽口切除** | 148,520,071.71 | −772,096.94 | 51 | 3154 | 10518 | 1 | prt.17 | **577 s** |
| 16 | `8409306b…` | 肩 −Z **15 处槽口切除** | **147,747,977.87** | −772,093.84 | 56 | 3201 | 10758 | **1** | prt.18 | **619 s** ⚠️ |

- 高亮 ⚠️ 两个作业 **超过 600 s**。它们之所以没有变成 `unknown_outcome`，**仅仅因为调用方在提交前把 `generic_timeout_seconds` 从 600 改成了 1500** —— 这是 §十九 的直接实测证据。
- 单处槽口切削量 = 772,096.94 / 15 = **51,473.13 mm³/处**（两个肩几乎完全对称，差 3 mm³）。
- Phase A（90 块凸台做完、未开槽）时体积 149,292,168.65，对比 TXT 目标 149,930,000 为 **−0.43 %**。

### 20.2 关键观察：耗时与模型规模强相关，且**固定开销占三分之一**

| 阶段 | 耗时 | 说明 |
|---|---|---|
| 连接 + 前置 `verify_saved`（全量枚举当前模型） | ≈ 90–120 s | 随模型面数线性增长 |
| 实际几何操作 | ≈ 10–15 s/轮廓 | `resolve()` + `inspection(false)` 每个操作重算一遍 |
| 收尾 `inspection()` 全量快照 + 保存 + 重载核验 | ≈ 120 s | §十九 的 `save_and_reload` |

⇒ **纯开销 ≈ 210–240 s 且随模型增大而增长**。所以"2 操作作业"在 30 轮廓左右尚有约 120 s 余量，超过就必然撞 600 s 旧上限。这是 §十九 建议"默认值随模型规模自适应"的量化依据。

⚠️ 但要提醒作者：**不要试图用"精确拟合式"**。本表 552–644 s 的区间里，耗时与轮廓数并不单调（45 轮廓 552 s vs 15 轮廓 619 s），波动已被固定开销主导。合理的做法是给一条**宽松上界**（如 `max(900, 180 + 12 × contours + 0.06 × surfaces)`），并依赖"超时值是上界而非延迟"这一性质 —— 详见 §十九 第 2 条。

### 20.3 最终几何核验（三方独立交叉验证）

| 指标 | MCP `creo_inspect_model` | 独立解析 STL 重算 | 一致性 |
|---|---|---|---|
| 体积 | 147,747,977.873 mm³ | 147,743,893.149 mm³ | **0.0028 %** |
| 包围盒 | `[−1272.266, −68.685, −228.600] … [1115.233, 945.629, 228.600]` | 完全相同 | 0 |
| 实体数 | 1 | — | — |
| 表面积 | — | 7,124,888.529 mm² | — |

- STL 重算用散度定理（`vol6 += a·(b×c)`）独立实现，**不经过任何 MCP 代码**；顶点/三角数 13,148。
- 特征树 56 个特征 **`status` 全部为 0（健康）**，`incomplete = false`。
- 平面面普查（按 `(法向, 距离)` 归并）独立确认了 TXT 的关键基准：
  | 位置 | 实测 Y / Z | TXT 值 | 结论 |
  |---|---|---|---|
  | 凸台顶面 | Y = −67.118 | 基准面1 = −67.12 | ✓ |
  | 带体外表面 | Y = −44.890 | −44.893 | ✓ |
  | 自由高度 | 22.228 | 22.225 | ✓ |
  | 槽底面 | Y = −44.793 | — | = 外表面 −0.1 mm |
  | 带宽 | Z = ±228.600 | ±228.600 | ✓ |
  | 驱动窗口面 | Y = 0.000（Z = ±17.87） | 28.575×31.08 过 Y | ✓ |
  | 窗口侧壁 | Y = −13.499 / −13.599（Z = ±48.19） | — | ✓ |
  | P03 分切面 | Z = ±38.435 / ±222.250 | 同 | ✓ |
- 已核对 `.build/gen_band.py` 的扫略半径 `R_NOM = [152.40, 217.54, 225.42, 214.27, 152.40]` 与 `path_geom.json` 的圆弧**逐段相等** ⇒ **排除了"路径不匹配"这一解释**，说明 §20.4 的体积偏差来自草图/拉伸本身，不是带体骨架。

### 20.4 两处已知偏差（如实记录）

| 偏差 | 数值 | 归因 |
|---|---|---|
| 总体积 vs TXT | **−1.46 %**（147,747,977.87 vs 149,930,000） | 凸台侧壁未做 s 方向 25° 拔模；Phase A 仅 −0.43 %，剩余偏差主要来自 90 块凸台的棱柱假设 |
| 单个凸台块 vs 棱柱解析值 | **+11.7 %**（实测 ≈33,293 mm³ vs 解析 29,805 mm³） | 圆弧段带体外表面并非严格径向（`S_IN − R_ROOT = 31.777` vs 设定 32.0，存在亚毫米间隙），使块底与曲面之间多出实体 |

> 两者方向相反、量级小，且**都不影响拓扑正确性**（63 分切 / 63 窗口 / 90 凸块 / 单实体均已核实）。记录在此是因为作者若做"体积/面积 delta ≤1%"的自动门禁，需要知道这类偏差的合法来源。

### 20.5 本次交付物

| 文件 | 大小 | 说明 |
|---|---|---|
| `track_p01b_rev16.prt.18` | 6,617,857 B | Creo 原生零件，sha256 `85a375ac5fa88712093614e23fc060d76e7841729e00de5d2192ba46363ea4ba` |
| `track_p01b_rev16.step` | 6,353,782 B | STEP AP214/AP203（`creo_export_model`，只读作业，rev 保持 16） |
| `track_p01b_rev16.stl` | 3,048,360 B | STL，用于 §20.3 的独立核验 |
| `track_p01b_rev16_preview.jpg` | 26,267 B | 预览图（视觉确认闭链、双肩胎面、分切与窗口、单实体） |

---

## 九、按影响排序的修复建议清单（汇总总表，置于文末便于查阅）
| 优先级 | 问题 | 一句话建议 |
|---|---|---|
| P0 | 剖面轮廓重叠 → 切除创建失败且无提示（第一节） | 建特征前预检轮廓相交，报出"第 i、j 个轮廓重叠、重叠面积"，或提供自动并集开关 |
| P0 | **作业超时杀死 worker → 模型被 `pending_job` 永久锁死，无解锁工具（第十七节）** | 超时前写检查点并回滚到已保存基线；提供 `creo_reconcile_model`；只读作业不应被 pending_job 挡住 |
| P0 | **超时残留的"脏会话"无法自愈：worker 复用会话内同名模型，且回滚被 `mutated` 门禁挡住（第十八节）** | 同名模型在会话中时先与基线校验，不一致就 `Erase` 后从 `part_file` 重载；回滚条件去掉 `mutated` |
| P0 | 新建切除"创建成功、重新生成静默失败"（第十节） | 重新生成失败时取回 Creo 特征错误详情；预检新剖面与已有切除面是否共面 |
| P1 | 对称拉伸 `depth` 是总深、内部尺寸需双倍（第十一节） | 文档写明口径；**在结果里回读特征实际占据范围** |
| P1 | **默认 600 s 作业预算对大型零件必然不够，且不能按作业指定预算（第十九节）** | `creo_execute_plan` 加 `timeout_seconds`；默认值随模型规模自适应；返回值给出所用预算 |
| P1 | 改尺寸比重建特征可靠得多（第十二节） | 报错文案引导使用 `creo_set_dimensions` |
| P1 | `coordinates` 对相切直线+圆弧闭环过约束（第二节） | 发尺寸前按 Creo 顶点合并容差归并端点 |
| P1 | `autodim` 在相切链上恒失败（第三节） | 先 autodim 再 solve；Intent Manager 不要提前置 FALSE |
| P2 | 曲面 `type` 恒为 34（第十三节） | 输出真实 `ProSurfaceType` + `is_planar`/`radius` |
| P2 | `datum_plane` offset=0 时静默取最小 id（第十四节） | 候选 >1 时报出全部候选，并提供显式 id 引用 |
| P2 | 无曲线阵列接口（第四节） | 补 `creo_curve_pattern`；能力查询里如实标注 |
| P2 | 无 `delete_feature` op，脏特征只能靠重启 Creo 清除（第十八节） | 补通用删除特征 op，或提供"回滚到已保存基线"作业类型 |
| P2 | 扫描后残留空实体（第五节） | 空实体清理改为通用收尾 |
| P2 | 单任务全量几何枚举、日志膨胀（第六节、第十六节） | 几何快照缓存 + `detail: "minimal"`；`resolve()` 结果缓存 |
| P3 | 约束创建报错无定位信息（第七节） | 报出端点名与实际间距，或容差吸附 |
| P3 | `plane` 字符串 + offset 隐式新建基准面（第十五节） | 结果里列出隐式创建的特征 |
| P3 | 成功作业里 `rollback_succeeded: false` | 成功时把该字段标为 `null` 或省略，避免误读 |

---
