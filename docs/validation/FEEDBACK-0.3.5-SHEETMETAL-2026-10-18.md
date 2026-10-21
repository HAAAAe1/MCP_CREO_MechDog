# MCP_CREO_MechDog v0.3.5 验收报告（第四轮回归）

- **日期**：2026-10-18
- **被测版本**：MCP_CREO_MechDog **v0.3.5**（`creo_startup_status`：current 0.3.5 = latest 0.3.5；注意从 0.3.3 直接跳到 0.3.5）
- **验收方法**：对 v0.3.1 / v0.3.2 / v0.3.3 三轮报告中的缺陷逐条做最小复现回归，用体积、边缘坐标、变换矩阵做客观判定
- **结论**：**钣金工具链的 3 项阻塞缺陷（S1 钣金件增料 / S3 四壁折边 / S5 `sheetmetal_wall` depth=1）在 v0.3.5 中全部仍未修复**；P5（装配旋转反手）、P11（无装配打包导出）同样未修复。**连续四个版本（0.3.1 → 0.3.5）钣金侧无一项修复进展。**

---

## 一、回归结果总表

| 编号 | 缺陷 | v0.3.5 结果 | 证据（job_id） |
|---|---|---|---|
| **S1** | 钣金件上 `extrude(mode="add")` 一律失败 | ❌ **未修复（第 4 次）** | `b538a84f15d54498a710fa82ef7aa0d1` |
| **S3** | `sheetmetal_flange` 建不了封闭四壁盒（第 3 道垂直折边失败） | ❌ **未修复（第 4 次）** | `45334bdae289480fbf7e600dd069a8ab` |
| **S5** | `sheetmetal_wall` `depth=1` 被 thickness 覆盖 | ❌ **未修复（第 4 次）** | `8cd4732d9c9e4c6091e9f593ff74f85d` |
| **P5** | `assemble_component` 旋转欧拉角反手 | ❌ **未修复（第 4 次）** | `41c8e79170b146edaa612edbf2c1324d` 后 `list_components` |
| **P11** | 装配交付无 `native_bundle` 打包导出 | ❌ 未修复（format 仍仅 step/stl/iges/jpeg/pdf） | 工具 schema |
| **S10** | 计划失败后 `result.operations` 返回空数组 | ❌ 未修复（本轮 5 次失败均返回 `[]`） | `45334bdae…` 等 |
| **N1** | 钣金件 `inspection.counts.bodies` 恒报 2 | ❌ 未修复（本轮仍见单实体报 2） | `8cd4732d…` |
| S2 | 折边方向不可控（`flip` 无效，始终向外） | ⚠️ 未复测（0.3.3 实测仍向外；S1/S3 同代码路径未变） | — |
| S6 | `sheetmetal_unbend` 的 `fixed_surface` 不接受 datum_plane | ⚠️ 未复测（0.3.3 实测仍失败） | — |
| P3 | 草图 dict plane 的 `offset≠0` 被拒 | ⚠️ 未复测（0.3.3 实测仍被拒） | — |
| S7 | `startup_status` 长期 "checking" 不给 ready 信号 | ⚠️ 未修复（本轮会话起始同样只见 "checking"） | `creo_startup_status` |
| P1/P2/P4 | 多区域增料 / 共面合并 / polyline | ⚠️ 未复测（v0.3.2 已修，本轮聚焦钣金） | — |
| S9 / 诊断 | `list_components` 紧凑化 / 失败诊断 | ✅ 保持已修 | `41c8e791…` |

---

## 二、未修复项复现细节

### S1 钣金件增料 ❌（四轮未修，最高优先级）
- 用例：`acc35_sm`：185×232×232 钣金壁 → 草图矩形 X 88..98 / Z 100..110 于 XZ 面 → `extrude(mode="add", depth=10, direction=negative)`。
  **该块与既有实体真实体积重叠**（块 X 88..98 与实体 X ±92.5 在 88..92.5 段重叠），已排除"无重叠/仅共面"两类误判。
- 结果：`ProFeatureWithoptionsCreate failed with code -1 during execute_extrude`；同模型 `mode:"cut"` 正常。
- **影响**：钣金件上无法做任何实体增料 → 格栅筋条、底板冲压凸台、铰链座/销、端壁、第二/三段折边框边全部无法实现。

### S3 封闭四壁盒 ❌（四轮未修）
- 用例：`acc35_sm2`：185×232×1 钣金底板（V=42 920 ✅）→ 一次挂 4 道 `sheetmetal_flange`（h=80, R2.54, Y=0.5，边 104/105/106/107）。
- 结果：**前 2 道（±X）成功，第 3 道（−Y）失败** `ProFeatureWithoptionsCreate -1`，整体回滚。行为与 0.3.1/0.3.2/0.3.3 完全一致；仍无折弯释放（bend relief）参数。
- **附带发现**：若底板过厚（本例 185×232×232），连**第 1 道**折边都会失败（`Regeneration produced a failed, suppressed or incomplete feature`）——因为折边被折向驱动面一侧、全部落在既有实体内、不产生新材料。说明折边方向对底板厚度敏感，`flip` 又不可控，可用性很差。

### S5 `depth=1` ❌（四轮未修）
- 用例：`sheetmetal_wall(depth=1.0, thickness=232.0)`，草图线长 185。
- 结果：体积 **9 957 440 = 185×232×232**（应为 185×232×1 = 42 920）。`depth` 被静默替换为 `thickness`。
- 连带：**无法用 `sheetmetal_wall` 直接铺 1 mm 底板**，必须绕道（草图画在 YZ 平面 + offset、thickness=1、depth=面内长边、direction=negative）。

### P5 旋转反手 ❌（四轮未修）
- 用例：`assemble_component(rotation=[0,90,0])` → `creo_list_components` 回读：
  ```
  [[0,0,-1],[0,1,0],[1,0,0]]  →  Ry(−90°)
  ```
  期望 Ry(+90°) = `[[0,0,1],[0,1,0],[-1,0,0]]`。**仍需传 [0,-90,0]**，且工具不回显变换矩阵。

### P11 / S10 / N1 ❌
- `creo_export_model` 的 `format` 枚举仍为 `step/stl/iges/jpeg/pdf`，无装配原生打包；复制 `.asm` 出去仍需手工携带 `C_*.prt` 快照。
- 计划失败时 `result.operations` 仍为空数组，无法知道哪些操作已成功，只能整批重发。
- 钣金件 `inspection.counts.bodies` 仍恒报 2（单个 6 面/12 边实体也报 2），而实体件正确报 1；该字段对钣金件不可用。

---

## 三、建议（与前三轮一致，按收益排序）

1. **修 S1（钣金件增料）**：四轮未修，是钣金链路的唯一硬阻塞；修好后配电箱的格栅筋条/凸台/铰链/端壁可全部补齐。
2. **修 S3 并提供折弯释放**（矩形/扯裂/圆形参数或自动角部处理）；同时修 S5 让 `depth` 不再被 `thickness` 覆盖。
3. **让 `flip` 真正翻转折边方向**（或新增 `direction`/`side`），并使第二段能向内折；注意折边方向对底板厚度的敏感性。
4. **修 P5 并在 `assemble_component` 返回中回显 4×4 transform**，避免使用者必调 `list_components` 自查旋转反手。
5. **S6**：`fixed_surface` 支持 datum_plane，或报错提示"请传 `{kind:'surface',id:N}`"。
6. **P3**：让 dict plane 的 `offset` 生效，或报错直接提示"先 `creo_datum_plane` 再按 label 引用"。
7. **P11**：`creo_export_model` 增加 `native_bundle`（.asm + C_*.prt 一起导出）。
8. **S10**：计划失败返回 `operation_outcomes`。
9. **N1**：修正钣金件的 `bodies` 计数或注明其不可靠。
10. **版本号**：本次从 0.3.3 直接跳到 0.3.5，建议在 `creo_capabilities` 中补一个 changelog/version history，便于回归定位"哪一版修了哪一项"。

---

## 四、本轮验收模型（可复查）

| 模型 ID | 名称 | 用途 |
|---|---|---|
| `e211d53b8b95460998575d505df283a8` | acc35_sm | S5（185×232×232）+ S1（增料失败）+ S3 厚底板边界用例 |
| `9c7222e7e94a4053aa19f972359a5224` | acc35_sm2 | S3 复现：1mm 底板 + 四壁折边第 3 道失败 |
| `8d8153e30ff54c0c9015c0fe1b3a0fe2` | acc35_asm | P5 复现 |

> 既有交付物不受影响：`out/`（实体方案）、`out2/`（钣金方案）及 v0.3.1/v0.3.2/v0.3.3 三份反馈文档仍然有效。
