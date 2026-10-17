# MCP_CREO_MechDog v0.3.3 验收报告（第三轮回归）

- **日期**：2026-10-17
- **被测版本**：MCP_CREO_MechDog **v0.3.3**（`creo_startup_status`：current 0.3.3 = latest 0.3.3）
- **验收方法**：对 v0.3.1/v0.3.2 两轮报告中的全部缺陷逐条做最小复现回归，用体积、边缘坐标、变换矩阵、预览图做客观判定
- **结论**：**钣金工具链的 3 项阻塞缺陷（S1/S3/S5）与折边方向（S2）在 v0.3.3 中全部未修复**；P3/P5/P11/S10/S6 亦未修复。v0.3.2 已修的实体侧缺陷本轮未复测。本轮新增一项正面改进（`list_components` 的 aliases 带回钣金折边/壁的构造明细）。

---

## 一、回归结果总表

| 编号 | 缺陷 | v0.3.3 结果 | 证据（job_id） |
|---|---|---|---|
| **S1** | 钣金件上 `extrude(mode="add")` 一律失败 | ❌ **未修复** | `37c2b07d0e494a9a94cccbe1ed654d35` |
| **S3** | `sheetmetal_flange` 建不了封闭四壁盒（第 3 道垂直折边失败） | ❌ **未修复** | `ae6d61c4c3274f17a7ae80e99177d377` |
| **S5** | `sheetmetal_wall` `depth=1` 被 thickness 覆盖 | ❌ **未修复** | `3390fe06e79142a5b36d70420a6a0746` |
| **S2** | 折边方向不可控（`flip` 无效，始终背离驱动面） | ❌ **未修复** | `62f4956662d54413a53eaf6c5c46ca08` |
| **S6** | `sheetmetal_unbend` 的 `fixed_surface` 不接受 datum_plane | ❌ **未修复** | `8d90ceb46f414dda9095377d0dbd75a4` |
| **P3** | 草图 dict plane 的 `offset≠0` 被拒 | ❌ **未修复** | `629fa81828f1466a9d17b55d50265e38` |
| **P5** | `assemble_component` 旋转欧拉角反手 | ❌ **未修复** | `43f3760e57124119aa08fd1f4f7bb291` 后 `list_components` |
| **P11** | 装配交付无打包导出（`native_bundle`） | ❌ 未修复（format 仍仅 step/stl/iges/jpeg/pdf） | 工具 schema |
| **S10** | 计划失败后 `result.operations` 返回空数组 | ❌ 未修复（本轮 5 次失败均返回 `[]`） | `ae6d61c4…` 等 |
| S7 | `startup_status` 长期 "checking" 不给 ready 信号 | ⚠️ 未修复（本轮会话起始同样只见 "checking"） | `creo_startup_status` |
| S9 | `list_components` 输出过大 | ✅ 保持已修（紧凑内联） | `43f3760e…` |
| — | 失败诊断信息 | ✅ 保持已修（`BUILD_FAILED` / `PHASE=` / 具体 Toolkit 调用） | 各失败 job |
| P1 / P2 / P4 | 多区域增料 / 共面合并 / polyline | ⚠️ 未复测（v0.3.2 已修，本轮聚焦钣金） | — |

---

## 二、未修复项的复现细节

### S1 钣金件增料 ❌（三轮未修，最高优先级）
- 用例：`acc33_sm2`：185×232×1 钣金底板（V=42 920 ✅）→ 草图 10×10 于 XY offset 0 → `extrude(mode="add", depth=5)`。
- 结果：`ProFeatureWithoptionsCreate failed with code -1 during execute_extrude`（op index 3）；同模型 `mode:"cut"` 正常。
- **影响**：钣金件上无法做任何实体增料 → 格栅筋条、底板冲压凸台、铰链座/销、端壁、第二/三段折边框边全部无法实现。

### S3 封闭四壁盒 ❌（三轮未修）
- 用例：同底板，边 104/105/106/107 一次挂 4 道 `sheetmetal_flange`（h=80, R2.54, Y=0.5）。
- 结果：**前 2 道（±X）成功，第 3 道（−Y）失败** `ProFeatureWithoptionsCreate -1`，整体回滚到只剩底板。行为与 v0.3.1/v0.3.2 完全一致；仍无折弯释放（bend relief）参数。

### S5 `depth=1` ❌（三轮未修）
- 用例：`sheetmetal_wall(depth=1.0, thickness=232.0)`，草图线长 185。
- 结果：体积 **9 957 440 = 185×232×232**（应为 185×232×1 = 42 920）。`depth` 被静默替换为 `thickness`。
- 连带：**无法用 `sheetmetal_wall` 直接铺 1 mm 底板**，必须绕道（草图画在 YZ 平面 + offset、thickness=1、depth=面内长边、direction=negative）。

### S2 折边方向 ❌（本轮直接复测）
- 用例：±X 两壁（h=80）建成后，从 **+X 壁顶内缘**（edge 220，X=91.5, Z=80）挂第二段折边 h=20, R2.54, Y=0.5。
- 结果：体积 78 970.58 → **83 075.87**（+4 105.29，与 v0.3.1/0.3.2 的"向外"单侧增量 4 105.3 完全一致）；预览图确认水平框边**向箱外伸出**。
- 即 TXT 要求的"围壁顶部内缘向内折 20 mm 形成水平框边"仍无法实现（向内应到 X=72.5，实测向外到 X≈111.5）。
- `flip` 参数在 v0.3.1 已实测无效，本轮仍未作为可控项。

### S6 展开固定面 ❌
- 用例：`sheetmetal_unbend(fixed_surface={kind:'datum_plane', axis:'z', offset:0})`。
- 结果：`ProFeatureWithoptionsCreate failed with code -1 during execute_sheetmetal_unbend`。
- 仍需先 `inspect_model(section=surfaces)` 取真实 surface id 才能展开（v0.3.1 时传 surface id 成功）。

### P3 dict plane offset≠0 ❌
- 用例：`plane={"reference":{"kind":"datum_plane","axis":"x","offset":20}}`（已按文档加 `reference` 容器）。
- 结果：仍报 `Plane reference must identify exactly one surface; inspect the model and use a surface ID`。
- 仍需先用 `creo_datum_plane` 建面再按 label 引用。

### P5 旋转反手 ❌（三轮未修）
- 用例：`assemble_component(rotation=[0,90,0])` → `creo_list_components` 回读：
  ```
  [[0,0,-1],[0,1,0],[1,0,0]]  →  Ry(−90°)
  ```
  期望 Ry(+90°) = `[[0,0,1],[0,1,0],[-1,0,0]]`。**仍需传 [0,-90,0]**，且工具不回显变换矩阵。

### P11 / S10 ❌
- `creo_export_model` 的 `format` 枚举仍为 `step/stl/iges/jpeg/pdf`，无装配原生打包；复制 `.asm` 出去仍需手工携带 `C_*.prt` 快照（v0.3.2 的 P11 问题依旧）。
- 计划失败时 `result.operations` 仍为空数组，无法知道哪些操作已成功，只能整批重发。

---

## 三、本轮新发现

### N1. `inspection.counts.bodies` 对钣金件恒报 2（误报）
- 单个 185×232×1 实体底板（6 面 / 12 边 / V=42 920，几何上只有一个 body）在 **v0.3.1 / 0.3.2 / 0.3.3 三个版本都报 `bodies: 2`**；而普通实体件（含 2 个不相邻凸台的零件）正确报 `bodies: 1`。
- 影响：使用者无法用 `bodies` 判断钣金件是否意外分裂，只能靠体积校验。建议修正该计数或至少在文档中说明钣金件该字段不可靠。

### N2. 正面改进：`list_components` 的 aliases 带回钣金构造明细
- v0.3.3 起 `aliases` 对 `sheetmetal_flange` 返回 `dimension_ids:{"height":…}`、`entity_ids:{"attachment":3,"wall":4}`、`section_path`、`solver`；对 `sheetmetal_wall` 返回 `construction:"thin_extrude_then_native_sheetmetal_conversion"`。
- 这对"找挂接边/核对折边高度"非常有用，也正面披露了第一壁的实现方式（thin extrude + native conversion）。**建议保留并在文档中说明这些字段的含义。**

---

## 四、建议（按收益排序，与 v0.3.2 一致且更迫切）

1. **修 S1（钣金件增料）**：三轮未修，是钣金链路的唯一硬阻塞；修好后第二轮配电箱的格栅筋条/凸台/铰链/端壁可全部补齐。
2. **修 S3 并提供折弯释放**：四壁开口箱是钣金最基本形态；建议加 `relief` 参数（矩形/扯裂/圆形）或自动角部处理。
3. **修 S5 并文档化 S4**：`depth`/`thickness`/草图线长三个方向请在工具描述中画清楚，并对被改写的参数返回告警。
4. **让 S2 的 `flip` 生效**（或新增 `direction`/`side` 参数），使第二段能向内折。
5. **修 P5 并在 `assemble_component` 返回中回显 4×4 transform**，避免使用者必调 `list_components` 自查旋转反手。
6. **S6**：`fixed_surface` 支持 datum_plane，或报错时提示"请传 `{kind:'surface',id:N}`（可用 `inspect_model(section=surfaces)` 获取）"。
7. **P3**：让 dict plane 的 `offset` 生效，或报错直接提示"先 `creo_datum_plane` 再按 label 引用"。
8. **P11**：`creo_export_model` 增加 `native_bundle`（.asm + C_*.prt 一起导出）。
9. **S10**：计划失败返回 `operation_outcomes`。
10. **N1**：修正钣金件的 `bodies` 计数或注明其不可靠。

---

## 五、本轮验收模型（可复查）

| 模型 ID | 名称 | 用途 |
|---|---|---|
| `552decf19f054d60bc0917e67eadcfd8` | acc33_sm | S5 复现：185×232×232 |
| `497a26d8f611461e86e0e2a99a1cb4cb` | acc33_sm2 | S1 / S3 / S2 / S6 复现（底板 + ±X 壁 + 向外第二段折边） |
| `add5133989b14b288ee82fdd53e7c08c` | ai_part_add5133989b1 | P3 复现 |
| `e4015d098f994a97b93e2412544997d2` | acc33_asm | P5 复现 |

> 既有交付物不受影响：`out/`（实体方案）、`out2/`（钣金方案）及 v0.3.1/v0.3.2 两份反馈文档仍然有效。
