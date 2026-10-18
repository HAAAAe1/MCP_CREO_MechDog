# FEAT-039：纯曲面链路算子（trim / merge / boundary_blend / offset 与检测查询）

日期：2026-10-18。类型：功能。优先级：P1。状态：待规划。目标版本：未排期。

来源：外部 0.3.5 曲面链路反馈 §1/§4（Creo 10.0.0.0 / release 42），触发场景为[可乐瓶五爪花瓣瓶底任务书](../validation/feedback-0.3.5-surface-2026-10-18/可乐瓶五爪花瓣瓶底建模任务书.docx)纯曲面法——8 步中 5 步无对应工具，链路几何上不可执行。见[反馈原件](../validation/feedback-0.3.5-surface-2026-10-18/report.md)。关联 [FEAT-009](FEAT-009.md)（loft 曲面模式）、[FEAT-017](FEAT-017.md)（曲面用法扩展）、[BUG-052](BUG-052.md)（曲面类型查询）。

## 缺口清单（反馈定 P0，供排期参考）

| 算子 | 现状 | SDK 常量就绪度 |
| --- | --- | --- |
| `surface_trim`（曲面修剪，keep_side/material_side） | 无任何 trim；`solidify{cut}` 仅基准面裁实体 | 元素名已导出，**ProSurfTrimType 等 5 个枚举 15 个常量未导出**（薄修剪另加 11 个） |
| `quilt_merge`（面组合并/缝合，返回 closed） | `boolean_bodies` 只接受 body 不接受 quilt | `PRO_FEAT_MERGE`/`PRO_E_MERGE` 已导出，**只差封装与验证** |
| `boundary_blend`（边界混合/G1 桥接，逐侧连续性与权重） | `surface_fill` 仅平面填充 | `PRO_E_BNDRY*` 已导出 21 条 |
| `quilt_offset`（面组偏置） | 无；`thicken` 是加厚成实体，语义不同 | 未核对 |
| loft 曲面模式/非平行截面 | 归 [FEAT-009](FEAT-009.md) | — |
| 检测查询：面积、`min_wall_thickness`/采样、斑马纹/曲率 | inspect 仅 volume_mm3 | — |

## 建议实施顺序（反馈 MVR，每步独立可验收）

1. 补 `constants.inc`：`ProTrim.h` 核心枚举 → 低层 `creo_create_feature_tree` 立即可构造曲面修剪；
2. 高层 `creo_surface_trim`（target/tool/keep_side，返回修剪前后面积）；
3. 高层 `creo_quilt_merge`（targets/tools/intersect，返回 closed——能否 solidify 的判据）；
4. `creo_loft` 曲面模式与 new_body（FEAT-009 范围，本项联动）；
5. `creo_boundary_blend`；6. `creo_quilt_offset`；7. 面积/最小壁厚查询。

做到 1–3 即完成"修剪 + 缝合 + 实体化"最小闭环。外部已提供 STL 回归基准（加料版/求差版两个模型）。

## 范围

- 每个算子先定输入引用格式（quilt_feature label/edge id）、keep_side 语义与返回字段（closed、面积前后值），再实现；沿用 capabilities 登记（`capabilities.py`）与 compact 白名单。
- 不改变既有 `solidify`/`thicken`/`surface_fill` 语义；loft 曲面模式在 FEAT-009 内推进、本项只联动验收。
- 曲面模式下 `axis_pattern` 对 quilt 的阵列有效性需补验证（反馈标注未验证）。

## 验收标准

| 环境 / 用例 | 命令或操作 | 可判断的预期结果 |
| --- | --- | --- |
| Windows / Python | schema + 单测 | 每算子的引用/参数校验与错误可判读；capabilities/文档同步 |
| 本机 Creo 12.4 | 任务书纯曲面法逐步最小用例（筒面+半球修剪、两截面放样曲面、五爪阵列修剪、中心封闭、merge→solidify） | 几何与体积对照解析值；保存重载通过；失败路径回滚与 revision 契约不变 |
| 回归基准 | 可乐瓶任务书整链 + 外部 STL 对比 | 仰视五瓣 72° 对称、爪尖着地、壁厚 0.3 无破面（min_wall 查询自证） |

## 实现与证据

2026-10-18 仅登记。正向旁证：同轮 `boolean_bodies` subtract 单 tool 成功（407,482.40 mm³，与手算差 0.6 mm³）、`revolve{new_body}` 绕道可生成独立爪实体。原始证据见反馈原件 §1/§4/§5。
