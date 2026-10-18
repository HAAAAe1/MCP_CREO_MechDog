# MCP_CREO_MechDog v0.3.5 缺陷报告 —— 建模能力边界阻塞跨软件全量重建

| 项目 | 内容 |
|---|---|
| 报告日期 | 2026-10-18 |
| MCP 名称 | MCP_CREO_MechDog |
| MCP 版本 | **v0.3.5**（`creo_startup_status` 返回 `current_version: 0.3.5`、`up_to_date`） |
| 目标软件 | Creo Parametric 10.0.0.0（`D:\Program Files\PTC\Creo 10.0.0.0`，release_numeric 42） |
| 环境自检 | `creo_check_environment` → `ready_to_build: true`，metric 模板齐备 |
| 传输/会话 | stdio；`creo_startup_status` → `state: ready`，`connected: true` |
| 建模任务 | 依据一份纯文本自然语言说明（4 零件 + 8 实例装配的虹膜式机构），从空白模型用原生草图/实体特征重建 |
| 核心问题 | **MCP 在多轮廓闭合截面、偏心轴圆周阵列、自定义基准面草图、草图尺寸策略四处的能力边界，导致 4 个零件中 2 个无法按规格完成、装配无法进行** |

---

## 0. 结论摘要（按严重度排序）

| # | 问题 | 严重度 | 影响 |
|---|---|---|---|
| P1 | 单个特征只接受**单条闭合轮廓**：多环截面（10 个独立槽）的拉伸/切除全部失败 | **阻断** | 无法一次性切除 10 个齿槽；备用路线（新实体+布尔）同样失败 |
| P2 | `creo_axis_pattern` 在**非原点轴**上生成的实例几何错误（不报错，体积证据可量化） | **阻断** | 齿轮 10 槽无法阵列；被迫换路线并废弃 2 个模型 |
| P3 | `creo_create_sketch` 在**自定义基准面**上：`kind:'surface'` 引用必失败、`u_axis` 为纯轴向时必失败 | **阻断** | 摆杆狗骨截面（Right 平面，u=−Z）完全无法建立 |
| P4 | `dimensioning:'coordinates'` 与 `'autodim'` 在非主轴面上互补地失效，且坐标校验会产生**不可能满足的伪偏离** | 高 | 含构造中心线的回转剖面无法用 coordinates；倾斜面必须退回 autodim |
| P5 | `creo_datum_axis` 用「两平面」构造轴时，实际生成的是**某一平面的法向轴**而非交线 | 高 | 偏心阵列轴无法构造（P2 的根因之一） |
| P6 | 没有删除/替换特征的能力；label 冲突即拒绝 | 中 | 失败草图无法就地修正，模型树残留脏特征 |
| P7 | `preview.jpg` 渲染不可信 | 中 | 体积显示零件完好、预览却渲染成若干分离长条，无法用于目视验收 |
| P8 | 无批量/计划接口，每个特征 1 次 job（10–25 s） | 中（工程效率） | 4 零件+8 实例 ≈ 60+ 个特征 → 60+ 次串行调用，实测 ≥70 分钟仅完成 2.5 个零件 |

---

## 1. P1 — 多轮廓闭合截面被拒（最严重）

### 1.1 现象

用一条含 **10 个互不相交闭合环（40 段圆弧）** 的草图 `gear_slots_10`（位于 XY 平面 offset 2.5，`dimensioning: coordinates`，草图本身创建**成功**，`features` 计数正常增长），随后：

| 调用 | 参数 | 结果 |
|---|---|---|
| `creo_extrude` | `mode:"cut"`, `depth_type:"through_all"`, `direction:"negative"` | ❌ `ProFeatureWithoptionsCreate failed with code -1 during execute_extrude`，`rollback_succeeded: true` |
| `creo_extrude` | `mode:"add"`, `new_body:true`, `depth:5`, `direction:"symmetric"`（想造刀具实体再布尔） | ❌ 同上 |

对照组：**同一草图只保留 1 个环**（同一个 4 段弧的槽截面）时，`cut + through_all` 一次成功，`material_removed_mm3 = 88.43`。因此失败原因确定是「多环」而非曲线本身。

### 1.2 复现最小用例

```
sketch: 2 个互不相交的 R1 圆，位于 XY offset 0
extrude: mode=cut, depth_type=through_all, direction=negative
期望: 两个通孔
实测: ProFeatureWithoptionsCreate = -1，回滚
```

### 1.3 影响与绕行代价

- 规格要求「种子槽 + 圆周阵列」，本可退化为「多环一次切除」；两条路都被堵死。
- 最终绕行为：**新建 R1 圆柱凸台 → 取其柱面作为阵列轴 → 阵列 → 再用中心孔切除顺带清除凸台**（见 3.2，可行但极其迂回，且对「轴在零件外」的情形完全不可用）。

### 1.4 建议

`creo_extrude` / `creo_revolve` 的 section 应支持多 contour 并逐个传递（Creo 原生 `ProSectionEntityVisit` + 每 loop 一个 `PRO_E_STD_SECTION` 子节点），或在文档中明确「单轮廓」限制并提供一个 `creo_extrude_multi`。

---

## 2. P2 — 偏心轴圆周阵列几何错误（静默出错）

### 2.1 现象与量化证据

模型：小齿轮（Ø24×5，盘心 (0,−0.092)），需绕 **(0,−0.504)**、方向 +Z 阵列 10 × 36°。

| 步骤 | 体积 (mm³) | 说明 |
|---|---|---|
| 盘体 | 2261.9467 | 与 π·12²·5 = 2261.9467 完全一致 |
| 种子槽切除 | 2173.5147 | 切除 88.4320 |
| `creo_axis_pattern` count=10, inc=36° | **1993.9312** | 仅又切除 **179.58** ≈ 2 个槽，期望 795.89（9×88.43） |
| 第二次尝试（另一模型）`creo_axis_pattern` count=2, inc=36° | 2173.5147 → **2155.1611** | 仅切除 **18.35**，期望 88.43 |

`status: succeeded`、`features` 里确实出现 10 个 instance（seed + 9 个 `cut` 特征 id 152–160），但几何不对：多数实例被转到**厚度方向之外**，因而几乎不切材料 —— 符合「旋转轴不是 Z 向」的推断。

对照组：同一 API 在**过原点的 Z 轴**上完全正常 —— 齿形摩擦片 40×9° 阵列（切除 3061.56 = 78.50×39，精确）与 5×72° U 槽阵列（1792.57 = 448.14×4，精确）均一次通过。

**结论：`creo_axis_pattern` 仅在「轴过零件原点」时可靠；非原点轴静默产生错误几何，不返回任何告警。**

### 2.2 轴构造对结果无影响（三种写法都错）

| 轴构造方式 | `creo_datum_axis` 结果 | 阵列结果 |
|---|---|---|
| `[{kind:'datum_plane',axis:'x'},{kind:'datum_plane',axis:'y'}]`（仅用于过原点，可作基线） | succeeded | ✅ 正确（Part3 已验证） |
| `[{kind:'datum_plane',id:70},{kind:'datum_plane',axis:'x'}]`，id70 = 法向 +Y、过 (0,−0.504,0) | succeeded | ❌ 错误 |
| `[{kind:'datum_plane',axis:'x'},{kind:'datum_plane',label:'PLANE_PAT_Y'}]` | succeeded | ❌ 错误 |

### 2.3 唯一可行的轴构造：柱面

```
creo_datum_axis(references=[{kind:'surface', id:173}])
  id 173 = 临时 R1 圆柱凸台的柱面（axis (0,0,1), origin (0,-0.504,2.5), radius 1.0）
→ 轴正确，随后的 10×36° 阵列一次成功
```
最终小齿轮体积 **1490.7023**（目标 1490.8，Δ −0.0066%），证明「柱面取轴」这条路径是对的。

### 2.4 建议

1. 修 `creo_datum_axis` 的「两平面求交」分支（当前疑似退化为「取第一个平面法向」）。
2. `creo_axis_pattern` 增加**阵列后自校验**：比较阵列前后 `material_removed_mm3` 与 `(count−1) × seed_removed` 的量级，偏差 >20% 时报 warning 而不是静默 `succeeded`。
3. `creo_axis_pattern` 的 `axis` 参数应接受显式 `{origin:[x,y,z], direction:[x,y,z]}`，彻底绕开基准轴构造的坑。

---

## 3. P3 — 自定义基准面上的草图：两处硬失败

### 3.1 `kind:'surface'` 引用必失败（与文档不符）

文档原文：`plane` 可为 `{reference:{kind:'surface',id:N},origin:[x,y,z],u_axis:[x,y,z]}`。

实测（同一块倾斜基准面 id 163，法向 (0.587785, 0.809017, 0)，过原点）：

| reference.kind | 草图结果 |
|---|---|
| `'surface'` + 30 段弧闭环 + `autodim` | ❌ `AutodimensionSketch failed with code -1` |
| `'surface'` + 4 条直线矩形 + `autodim` | ❌ 同样失败（**排除轮廓复杂度**） |
| `'datum_plane'` + 30 段弧闭环 + `autodim` | ✅ 成功 |
| `'datum_plane'` + 30 段弧闭环 + `coordinates` | ❌ `Coordinate dimensioning requires a principal plane ...`（见 P4） |

→ **文档写的 `surface` 不行，未文档化的 `datum_plane` 才行。**

### 3.2 `u_axis` 为纯轴向时 "Zero direction vector"

需求：摆杆狗骨截面在 Right 平面（法向 +X）内，`u_axis` 必须为 **−Z**（规格给的映射是 `(u,v) → 全局 (0, v, −u)`，即 u 沿 −Z、v 沿 +Y）。

| 参数 | 结果 |
|---|---|
| `plane={reference:{kind:'datum_plane',id:2}, origin:[0,0,0], u_axis:[0,0,-1]}` | ❌ `Zero direction vector`（`failed_stage: execute_sketch`） |
| `u_axis:[0,0,1]` | ❌ `Zero direction vector` |
| 对照：`u_axis:[0.809017,-0.587785,0]`（Part1 倾斜面，含 X/Y 分量） | ✅ 成功 |

两次失败与 u_axis 的正负无关，只与「纯 Z 向」有关 → 疑似内部用某个只取 X/Y 分量的公式计算 v 方向，纯 Z 时得到零向量。**结果：Part2 的狗骨杆身（零件主体之一）完全无法建立**，因为没有其他平面能给出 (u=−Z, v=+Y) 这个手性正确的帧。

### 3.3 建议

- 文档改为 `{reference:{kind:'datum_plane',id:N}, ...}`，或两种都支持。
- `u_axis` 一律先做 `u = u/|u|`、`v = n×u`，并对 `|n×u| < eps` 给出**明确报错**（说明 u_axis 与平面法向平行），而不是 "Zero direction vector"。
- 增加一个 `plane={origin, normal, u_axis}` 的**不依赖任何几何引用**的写法，让「规格里直接给了平面方程」的场景可以一步落地。

---

## 4. P4 — 草图尺寸策略在非主轴面上互补失效 + 伪偏离

### 4.1 coordinates 模式不支持非主轴面

```
dimensioning:"coordinates" + 倾斜面(id 163)
→ 400: "Coordinate dimensioning requires a principal plane and line/polyline/rectangle/circle/arc entities"
```
规格里绝大多数截面是**给定精确坐标**的（20/24/30 段闭环），`coordinates` 是唯一能保证「照抄坐标不走样」的模式；在倾斜面上被禁用后只能退回 `autodim`，失去了坐标保真度。

### 4.2 混合「闭环 + 构造中心线」时产生不可能的偏离

摆杆回转剖面：8 段闭环 + 1 条构造中心线（x=15，用于 `creo_revolve`），XY 主轴面，`coordinates`：

```
→ "Coordinate dimensioning changed the supplied geometry; maximum deviation mm=22.264000"
```
22.264 mm 的偏离说明求解器整体挪动了图元（中心线不受坐标尺寸约束，被求解器自由拖动，触发偏离阈值）。**只要草图里有一根不进环的构造线，coordinates 就不可用** —— 而 `creo_revolve` 恰恰需要它。

绕行：改 `autodim` → 通过（扇壳体积 2416.0358，与 Pappus 定理估算 2427 一致）。

### 4.3 建议

- `coordinates` 解除「principal plane」限制（坐标尺寸本身与平面无关）。
- 偏离校验只统计**参与成形轮廓**的图元，忽略 construction 图元。
- 偏离阈值可配置，或在报错里给出**是哪个 entity 偏离**，便于定位。

---

## 5. P5 — `creo_datum_axis` 两平面求交退化为法向

见 2.2：`[{kind:'datum_plane',id:70},{kind:'datum_plane',axis:'x'}]`（y=−0.504 平面 ∩ x=0 平面，交线应为 Z 向直线）→ 生成的轴与「平面 70 的法向 +Y」一致（由阵列结果反推：实例被转到厚度外，只有横向轴会造成这种「几乎不切料」的量化特征）。

同时 `creo_datum_axis` **无任何返回信息**（不含 direction/origin），`creo_inspect_model` 的 `sections_available` 里也没有 `axes` 段 —— 无法在阵列前校验轴是否正确。这是本次排障最耗时的一点。

### 建议
1. 修求交分支。
2. 返回 `{origin, direction}`。
3. `creo_inspect_model` 增加 `axes` 段（或 `datum_axes`）。

---

## 6. P6 — 无特征删除/替换能力

- `creo_create_sketch` 对同名 label 直接拒绝：`Feature labels already exist: ['tooth_slot']`。
- 支持的 feature 列表里没有 delete/remove feature（只有 `remove_component` 针对装配组件）。
- 后果：一次失败的草图（例如坐标偏离被回滚后残留的草图、或轮廓画错）只能**换新 label 重画**，旧特征永久留在树里。本次 3 个零件里累计留下 5 个无用草图/平面，会污染后续 `creo_inspect_model` 的 features 输出，也无法向用户交付干净的模型树。

### 建议
增加 `creo_delete_features(labels=[...])`（或 `suppress`），并允许 label 复用（先删后建）。

---

## 7. P7 — `preview.jpg` 不可信

Part1 在「斜槽种子切除」后：

- `creo_get_job.inspection.volume_mm3` = 16028.4006，相对切除前 16106.2664 只少 77.87；
- 同一 job 的 `preview.jpg` 却把零件渲染为 **7~8 根互不相连的长条**，圆盘完全消失。

两者不可能同时为真。后续体积逐步累加（+347.474 凸台、+83.621 凸销）与解析值精确吻合，证明**体积可信、预览不可信**。建议检查预览的 tessellation / 视图状态（疑似渲染了未缝合的曲面或错误的 display set）。

影响：目视验收失效，只能靠体积/面数间接判断，显著增加排障成本。

---

## 8. P8 — 无批处理，特征成本 = 1 job

`creo_create_feature_tree` 需要手写 Toolkit element tree，不具备可用性；`creo_group_features` 只能对**已存在**的特征分组，不能一次执行多个 op。

实测单次 job 端到端 8–33 s（含 connect → build → save → reload → verify），本任务：

| 零件 | 特征/草图数 | 调用（含轮询） | 耗时 |
|---|---|---|---|
| Part3 齿形摩擦片 | 16 | ~40 | ~18 min |
| Part4 小齿轮（含 3 次重建） | 34 | ~60 | ~28 min |
| Part1 星形架（部分） | 12 | ~30 | ~14 min |
| Part2 摆杆（部分） | 3 | ~12 | ~7 min |

**建议**：提供 `creo_apply_plan(ops=[...])`，一次 job 内顺序执行 N 个 op，仅末尾 save+reload+verify（当前每个 op 都 save+reload，是主要的墙钟开销）。这对「按规格文本批量重建」这种最典型的用法是决定性的。

---

## 9. 已成功验证的部分（供作者定位「边界在哪」）

以下能力在本次任务中**完全可用且精度很高**，可作为回归基线：

| 能力 | 证据 |
|---|---|
| `creo_new_part`（metric 模板） | 4 个零件均正常建立 |
| `creo_create_sketch` + `coordinates`（主轴面，闭环） | 20/4/6 段闭环全部通过 |
| `creo_extrude` add/cut、blind/through_all、positive/negative/symmetric | 全部正确 |
| `creo_revolve`（草图内构造中心线，symmetric 67°） | 体积 2416.0358，与 Pappus 估算 2427 差 0.45% |
| `creo_axis_pattern`（**过原点**轴） | 40×9° 与 5×72° 两次均精确 |
| `creo_datum_plane` offset / angled-about-axis | 法向实测 (0.587785, 0.809017, 0)，与规格完全一致 |
| `creo_datum_axis` 由**柱面**取轴 | 成功，且阵列结果正确 |
| `creo_inspect_model` section=surfaces | 能给出圆柱面的 axis/origin/radius，非常有用 |
| `creo_get_job` 的 `material_removed_mm3` | 每个切除都给出精确值，是本次最重要的自校验依据 |

**精度依据**：本次用「规格文本给的截面坐标」重建的两个零件，与规格记录值的偏差为

- 齿形摩擦片：实测 18569.9426 mm³ / 记录 18570.1 → **−0.00085%**
- 小齿轮：实测 1490.7023 mm³ / 记录 1490.8 → **−0.0066%**

说明「文本坐标 → 原生草图 → 实体」这条链路本身精度足够，问题只在上述能力边界。

---

## 10. 优先级建议

1. **P1 多轮廓截面**（阻断面最广，且绕行代价最高）
2. **P2 偏心轴阵列静默错误** + P5 轴求交（静默错误最危险，且是 P1 的唯一天然替代方案）
3. **P3 自定义基准面草图**（`u_axis` 纯轴向、`kind` 文档不符）
4. **P4 尺寸策略**（coordinates 的平面限制与偏离校验）
5. **P8 批量 plan 接口**（工程效率，直接决定这类任务能否在合理时间内完成）
6. P6 删除特征 / P7 预览 / 轴可观测性

---

## 附：本次任务最终状态（诚实记录）

| 零件 | 目标 V (mm³) | 实测 V (mm³) | 偏差 | 状态 |
|---|---|---|---|---|
| Part3 齿形摩擦片 | 18570.1 | 18569.9426 | −0.0009% | ✅ 完整（40 齿、Ø8、双环槽、5 U 槽） |
| Part4 小齿轮 | 1490.8 | 1490.7023 | −0.0066% | ✅ 完整（10 弧槽、Ø4、双面双凸环） |
| Part1 星形架 | 12852.8 | 16459.4958 | +28.06% | ⚠️ 部分（花盘+5 斜槽种子+中心凸台+侧凸销；**5 槽阵列未成、R3 圆角与 2 处倒角未做**） |
| Part2 摆杆 | 3791.6 | 2416.0358 | −36.29% | ⚠️ 部分（仅 67° 扇壳；**狗骨杆身/腹板/三角筋/销/凸台未做**，因 P3） |
| 装配 Assem1（8 实例） | — | — | — | ❌ 未进行（Part1/Part2 不完整，位姿校核无意义） |

**未使用任何外部模型输入**：全部几何数据来自那份 TXT 的附录 B 草图坐标与正文参数；未导入 STEP/Parasolid/STL，未引用 CREO/SolidWorks/NX 原文件。
