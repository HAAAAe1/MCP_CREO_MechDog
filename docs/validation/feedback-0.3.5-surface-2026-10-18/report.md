# 纯曲面链路缺 Trim / Merge / 边界混合，且含中心线草图无法就地改几何

> 反馈对象：MCP_CREO_MechDog v0.3.5（pre-release, tag v0.3.5）
> 运行环境：Windows win32 / Creo Parametric 10.0.0.0（release_numeric=42）/ Python 3.13 / stdio
> 触发任务：按一份「可乐瓶五爪花瓣瓶底」建模任务书执行**全程曲面法**（曲面放样→修剪→桥接→缝合→实体化→0.3 壁厚）
> 结论：**任务书 8 个步骤中有 5 步在本版本没有对应工具，链路在几何上不可执行**；另发现 1 项让模型无法迭代的流程阻塞。

---

## 0. 摘要（按阻塞程度排序）

| 级别 | 问题 | 影响 |
|---|---|---|
| **P0** | 缺 `trim`（曲面修剪，选保留侧） | 曲面法第 1、4 步无法做；整个"用曲面切曲面"的核心动作不存在 |
| **P0** | 缺 `merge`（曲面合并/缝合） | 多片 quilt 无法拼成封闭组 → 第 7 步实体化没有输入 |
| **P0** | 缺 `boundary_blend`（边界混合 / G1 桥接），`surface_fill` 仅支持平面 | 第 5 步爪谷过渡、第 6 步曲面填充均无法做 |
| **P0** | `loft` 不支持曲面模式（仅实体、仅 XY 平行截面、仅默认 body 加料） | 第 2 步"放样曲面"无法做；实体法第 2–4 步也要绕道 |
| **P0** | 无 quilt offset（面组偏置）；`thicken` 是"加厚成实体"不是偏置面组 | 第 8 步方案 B 无法做 |
| **P1** | `update_sketch_geometry` 拒绝 centerline，含中心线草图无法就地改几何 | 改一个尺寸必须整模重建（本次被迫重建 2 次） |
| **P1** | 无删除特征（delete）能力 | 建错一个特征只能重建整模 |
| **P1** | 恒定半径 `round` 在近切收尾处失败，无降级/变半径 | R2 爪谷圆角做不出，只能留锐边 |
| **P2** | `creo_capabilities` 返回 104,552 字符，超客户端上限被截断 | 首轮就要落盘再分批读，信息获取成本高 |
| **P2** | `creo_get_job` 无 wait/timeout，只能高频轮询 | 每个 job 4–6 次轮询，长链路耗时翻倍 |
| **P2** | 失败 job 无根因，`native_log_tail` 只有 `ProXxx()=0` 调用回显 | `shell` 两次失败，无法判断是厚度冲突还是面片自交 |
| **P2** | 无壁厚 / 最小料厚 / 面积查询 | "任意截面壁厚 0.3"只能靠导出 STL 自行计算 |
| **P2** | `creo_new_part` 无输出目录参数 | 模型固定落 `models/<id>/output/`，交付要手工复制 |
| **P2** | 预览固定 3/4 视角，不可指定 | 验收需要仰视/正视，只能自己导出 STL 渲染 |

---

## 1. P0：纯曲面法缺的 5 个算子

先给结论表——把任务书第二部分逐步映射到 v0.3.5 的 60 个 `operations`：

| 任务书步骤 | 需要的命令 | v0.3.5 现状 |
|---|---|---|
| 第 1 步 筒面 + R33 半球面 | 回转曲面 | ✅ `revolve{mode:"surface"}` |
| 第 1 步 用半球修剪筒面下缘 | **Trim** | ❌ 无 |
| 第 2 步 两个 50° 截面放样成曲面 | **Loft(surface)** | ❌ `loft` 仅 solid/add/XY 平行截面 |
| 第 3 步 五爪阵列（曲面） | 轴阵列 | ⚠️ `axis_pattern` 可用，但 quilt 阵列未验证 |
| 第 4 步 用爪曲面修剪半球（保留爪外侧） | **Trim + 保留侧** | ❌ 无 |
| 第 5 步 爪谷桥接过渡（G1） | **Boundary Blend** | ❌ 无；`surface_fill` scope 明确 "planar fill" |
| 第 6 步 中心圆形开口填充 | 填充曲面 | ⚠️ 仅平面填充，曲面边界不行 |
| 第 7 步 全部曲面缝合为封闭组 | **Merge / Stitch** | ❌ 无 |
| 第 7 步 封闭组转实体 | Solidify | ⚠️ 仅验证过"封闭 quilt"，曲面 quilt 未验证 |
| 第 8 步 面组向内偏置 0.3 | **Quilt Offset** | ❌ 无（`thicken` 语义不同） |
| 第 8 步 斑马纹 / 曲率检查 | Curvature analysis | ❌ 无查询接口 |

### 1.1 `trim`（曲面修剪）——最硬的一刀

- **现象**：`operations` 60 项里没有 trim/split/cut-with-quilt。唯一沾边的是 `solidify{mode:"cut"}`，但其 docstring 是 *"trim a solid with a datum plane using mode='cut'"*，能力表 `surface_solid.limits` 也自述 *"curved-quilt offset/cut and all side options need further validation"*——即"用曲面切实体"都未验证，更谈不上"用曲面切曲面"。
- **我可以做到什么**：只能靠 `revolve{mode:"cut"}` / `extrude{mode:"cut"}` 这类**轴对称或拉伸**的切除，无法用任意曲面修剪。
- **期望接口**（参考 Creo「曲面修剪」）：
  ```json
  {
    "op": "surface_trim",
    "label": "trim1",
    "target":   {"kind": "quilt_feature", "label": "body_quilt"},
    "tool":     {"kind": "quilt_feature", "label": "claw_0"},
    "keep_side": "one" | "two",          // 关键：保留侧
    "material_side": "one" | "two",      // 与实体求交时的取侧
    "thin": false
  }
  ```
  返回值至少要给出 `result_quilt_area_before/after`，否则无法判断剪对了边。
- **SDK 依据（可直接照做）**：安装 SDK 里有专门头文件 `ProTrim.h`。曲面修剪是 `PRO_E_FEATURE_TYPE = PRO_FEAT_CUT` + `PRO_E_SRF_TRIM_TYPE`（`ProSurfTrimType`）区分：
  ```c
  typedef enum _ProSurfTrimType {
    PRO_SURF_TRIM_TYPE_UNDEF = 0, PRO_SURF_TRIM_USE_CRV = 1,
    PRO_SURF_TRIM_USE_QLT = 2,   PRO_SURF_TRIM_THIN = 3,
    PRO_SURF_TRIM_SILH = 4 } ProSurfTrimType;
  ```
  元素树（ProTrim.h 第 25 行起）：`PRO_E_FEATURE_TYPE / PRO_E_FEATURE_FORM / PRO_E_SRF_TRIM_TYPE / PRO_E_SURF_TRIM_TYPE / PRO_E_TRIM_QUILT / PRO_E_STD_USEQLT_QLT / PRO_E_MATERIAL_SIDE / PRO_E_PRIMARY_QLTSIDE / PRO_E_KEEP_TRIM_SURF_OPT`。
- **当前连低层通道也走不通**：`native/constants.inc` 已导出 `PRO_E_SURF_TRIM_TYPE`、`PRO_E_SRF_TRIM_TYPE`、`PRO_E_TRIM_QUILT`，但**没有导出 `ProSurfTrimType` 的枚举值**（`PRO_SURF_TRIM_USE_QLT` 等命中 0 条），也没有 `PRO_TRIM_MATL_SIDE_ONE/TWO`、`PRO_E_PRIMARY_QLTSIDE` 的取值。所以 `creo_create_feature_tree` 能写出元素名、写不出枚举值。
- **最小修复**：把 `ProTrim.h` 里的枚举补进 `constants.inc`——核心 5 个枚举共 15 个常量：
  `ProSurfTrimType`(5)、`ProTrimMatlSideOpts`(3)、`ProTrimPrimaryQltSide`(2)、`ProTrimStdQuiltSideOpts`(3)、`ProKeepTrimSurfOpts`(2)；
  薄修剪另加 `ProTrimSurfOffMethodOpts`(3) 与 `ProThinTrimAxesOption`(8)。
  低层通道立刻可用，高层封装随后跟进。

### 1.2 `merge`（曲面合并/缝合）

- **现象**：无 merge。`boolean_bodies` 只作用于 **body**（`{kind:"body", id}`），不接受 quilt；`thicken`/`solidify` 都要单张 quilt。于是"筒面 + 5 片瓶底面 + 5 片过渡面"永远拼不成一个封闭组。
- **期望接口**：
  ```json
  {"op":"quilt_merge","label":"m1","targets":[{"kind":"quilt_feature","label":"q1"}],
   "tools":[{"kind":"quilt_feature","label":"q2"}],"intersect":true}
  ```
  并返回 `closed: true/false`（是否成为封闭面组）——这比面积更重要，是能否 `solidify` 的唯一判据。
- **SDK 依据**：`ProMerge.h` 存在；`PRO_FEAT_MERGE`（constants.inc 第 5653 行）与 `PRO_E_MERGE` 均已导出。也就是说这块**常量齐备、只差一层封装和验证**，是投入产出比最高的一项。

### 1.3 `boundary_blend`（边界混合 / G1 桥接）

- **现象**：`surface_fill` 的家族说明是 *"planar fill, thicken and solidify"*，只能平面填充；无边界混合、无 G1/G2 连续性控制、无"两曲线间桥接"。
- **后果**：任务书的"胜负手"——爪谷 G1 过渡——根本无法实现，只能让两张曲面硬交出一条锐棱。
- **期望接口**：
  ```json
  {"op":"boundary_blend","label":"bridge",
   "curves":[[{"kind":"edge","id":A}],[{"kind":"edge","id":B}]],
   "continuity":[["G1", 0.6],["G1", 0.6]],   // 每侧连续性与权重
   "close":false}
  ```
- **SDK 依据**：`PRO_E_BNDRY*` 系列常量在 constants.inc 里已导出 21 条，具备构造条件。

### 1.4 `loft` 的曲面模式

- **现象**：`loft` 的 limits 自述 *"solid add into the default body only; no cut/surface/new_body, nonparallel sections or endpoint tangency/curvature controls"*。
- **实际影响**：任务书第 2 步"两个 50° 截面放样曲面"做不了；**连实体法也没法直接用**——因为放样只能往默认 body 加料，无法生成独立"爪实体"再求差。本次只能绕道：用 `revolve{mode:"add", new_body:true, angle:50}` 生成独立爪实体（两个同角度同轴截面做直纹放样 ≡ 锥面 ≡ 回转体，几何等价），才把第 3、4 步走通。
- **期望**：`creo_loft` 增加 `mode: "add"|"cut"|"surface"` 与 `new_body: bool`；允许非 XY 平行截面（至少允许指定每段的支撑面/坐标系）。

### 1.5 面组偏置（quilt offset）

- **现象**：`thicken{reference: quilt, thickness}` 是"把面组加厚成实体"；任务书第 8 步方案 B 要求"对封闭曲面组向内偏置 0.3，再缝合内外两面组"。二者语义不同，且没有 `offset`。
- **期望**：`{"op":"quilt_offset","reference":{...},"distance":-0.3,"flip_side":false}`，返回偏置后 quilt 的 label 以便后续 merge。

---

## 2. P1：让模型无法迭代的流程阻塞

### 2.1 `update_sketch_geometry` 不接受 centerline（**本次最痛**）

- **复现**：`job 085e56a792c5473a82fdff1b7340b118`
  对一张含 `<centerline>` 的回转草图调用 `creo_update_sketch_geometry`（只传 arc + polyline）：
  ```
  failed_stage: execute_update_sketch_geometry
  message: "In-place edit must retain every named sketch entity"
  ```
  而把 centerline 一起传进去时，schema 层直接拒绝：
  ```
  0.update_sketch_geometry  Value error, In-place editing supports line, polyline,
  rectangle, circle, arc, ellipse and spline
  ```
- **矛盾点**：`create_sketch` 的文档明确要求 *"For revolve include one centerline"*，但 `update_sketch_geometry` 不支持 centerline → **所有回转类草图天生不可就地编辑**。
- **代价**：本次要修中心凹球的球心位置（R8 球心从 −25 移到 −31），无法改草图，只能把整条 30 特征链路重建一遍（两个模型、约 12 个 job）。
- **建议**：把 `centerline` 加进 in-place 支持的实体类型（它只是构造线，重算成本低）；或在 `update_sketch_geometry` 增加 `preserve_unlisted: true`，未列出的实体原样保留。后者更通用，也能解决"只想改一条边但要传全量"的体验问题。

### 2.2 无删除 / 抑制特征

- 任务书改一步、或实验性特征建错，就必须重建整模。`operations` 里只有 `drawing_delete`（图纸），没有 model feature 的 delete/suppress。
- **建议**：`{"op":"delete_feature","feature":"<label|id>","keep_children":false}` + `{"op":"suppress","features":[...]}`。

### 2.3 恒定半径 `round` 在近切收尾处失败

- **复现 A**（10 条边，R2）：`job dbaea9c036a54c1694dbfe12ace72166` → `failed_stage: execute_round`，"Regeneration produced a failed, suppressed or incomplete feature"，自动回滚。
- **复现 B**（只 1 条边，R2）：`job bc9575c08b914a1495aa07f7501c25ef` → 同样失败。
- **场景**：爪侧面（平面）与 R33 球面的交线，两端收敛于近切点，滚动球半径退化为零宽，恒定半径圆角无解。
- **建议**：(a) 支持 `variable_radius` / 半径表；(b) 支持 `stop_at_reference`、`extend_to_surface`（让圆角延伸到相邻曲面而不是在切点收尾）；(c) 失败时在错误里带上**冲突边的 id 与最小可行半径估计**，现在只能靠二分试。

---

## 3. P2：可用性与诊断

| # | 问题 | 证据 | 建议 |
|---|---|---|---|
| 1 | `creo_capabilities` 单次返回 104,552 字符，超客户端 tool-result 上限被截断落盘 | 本次首调即触发 | 支持 `section=`（tools/limits/references/families）分页；或默认精简、`detail:"full"` 才全量 |
| 2 | `creo_get_job` 只接受 `job_id` / `detail`，无 `wait_seconds` | 单 job 需 4–6 次轮询（每次 ~1–2 s） | 增加长轮询：`wait_seconds: 30`，完成即返回，与 MCP 的 progress 机制配合 |
| 3 | 失败 job 无根因 | `native_log_tail` 全是 `ProEdgeIdGet(...)=0`、`ProSurfaceDataGet(...)=0` 之类调用回显 | 失败时返回：失败特征名/ID、Creo 的 `ProFeatureError` 文本、涉及的面/边 id |
| 4 | `shell` 失败无法定位 | `job 7236a301fff446ea855bf66370e8b64b`（移除顶面）与 `job 244a2be09840486094118cbc6c693adb`（不移除）均 `execute_shell` 失败；实际原因是某处只剩 0.357 mm 料（< 2×0.3），偏置面自交 | 见 #3；另外建议 shell 前置检查：返回 `min_wall_feasible` 与最薄位置坐标 |
| 5 | 无壁厚/最小料厚/面积查询 | `inspect_model` 只有 `volume_mm3` | 加 `area`、`min_wall_thickness`（或 `thickness_at` 采样），否则"任意截面壁厚 0.3"无法直接验收 |
| 6 | `creo_new_part` 无输出目录参数 | 模型固定落 `models/<model_id>/output/*.prt.N` | 增加 `output_dir` |
| 7 | 预览固定 3/4 视角，不可指定 | 每个 job 的 `preview.jpg` 视角固定 | `export(format:"jpeg", view:"bottom"|"front"|"top", orthographic:true)` |
| 8 | 能力表与真实行为不一致 | `axis_pattern` 的 placement 家族称已验证"quilt rotate/translate/thicken/edit"，但 quilt 阵列没有明确条目；`loft` 的 limits 与任务书需求完全冲突却无替代提示 | 在 caps 里为每个 op 标注 `surface_support: yes/no/partial`，让调用方一眼筛掉不可用的路径 |

---

## 4. 建议的最小可用增强（MVR）

按这个顺序做，纯曲面法就能跑通，且每一步都是独立可验收的小改动：

1. **补 `constants.inc`**：`ProTrim.h` 的核心 5 个枚举共 15 个常量（薄修剪再加 11 个）。→ 低层 `creo_create_feature_tree` 立刻能构造曲面修剪（元素树照抄 `ProTrim.h` 第 25 行起的分支图）。
2. **高层封装 `creo_surface_trim`**：`target` / `tool` / `keep_side`，返回面积前后值。
3. **高层封装 `creo_quilt_merge`**：`targets` / `tools` / `intersect`，返回 `closed`。`PRO_FEAT_MERGE` 常量已在表内。
4. **`creo_loft` 支持 `mode:"surface"` 与 `new_body`**。
5. **`creo_boundary_blend`**（`PRO_E_BNDRY*` 已导出 21 条）。
6. **`creo_quilt_offset`**。
7. **`update_sketch_geometry` 支持 centerline 或 `preserve_unlisted`**（与曲面无关，但是迭代速度的瓶颈）。

做到 1–3，就能完成"曲面修剪 + 缝合 + 实体化"这条最小闭环；4–6 补齐放样、过渡、偏置；整条纯曲面法才真正可执行。

---

## 5. 复现证据（本次全部 job）

| job_id | 内容 | 结果 |
|---|---|---|
| `1f754860…` / `e1d5da24…` / `46388068…` | 筒+半球 / 单爪+轴 / 五爪阵列 | ✅ |
| `dbaea9c0…` | round R2，10 条爪谷交线 | ❌ execute_round，已回滚 |
| `bc9575c0…` | round R2，仅 edge 138（单边复测） | ❌ execute_round，已回滚 |
| `085e5679…` | update_sketch_geometry（含 centerline 的草图） | ❌ 必须是全部命名实体 / 不支持 centerline |
| `32cbea44…` | revolve + `new_body:true` 生成独立爪实体 | ✅（loft 的规避方案） |
| `6825be2c…` | `boolean_bodies` subtract（单 tool） | ✅ 407482.40 mm³，与手算误差 0.6 mm³ |
| `7236a301…` | shell 0.3（移除顶面） | ❌ execute_shell |
| `244a2be0…` | shell 0.3（不移除面，纯探测） | ❌ execute_shell |

模型：`cola_petal_bottom_final.prt`（加料版，30 特征，抽壳成功）/ `cola_petal_bottom_bool.prt`（求差版，28 特征，抽壳失败）。两者的 STL 都已导出，可用于回归对比。

---

## 6. 附：本次环境

```
platform   win32
creo       Creo Parametric 10.0.0.0 (D:\Program Files\PTC\Creo 10.0.0.0)
sdk        ProToolkit x86e_win64, release_numeric 42
mcp        0.3.5 (pre-release), tool_count 84, operations 60
transport  stdio
units      mm / degrees
```

> 说明：`shell` 失败的另一半原因在**任务书尺寸链自身**（上截面 R28 在爪高 16 处与 R33 球面只差 0.284 mm，留下 0.357 mm 刀口），不是 MCP 缺陷；写在这里只是说明"失败无根因"这一条对排查的实际代价——如果有最小料厚/冲突面提示，这类问题 10 秒就能定位。
