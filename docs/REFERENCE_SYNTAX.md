# 模型引用格式（BUG-006）

模型引用首先区分**几何对象**和**特征标签**，再区分单条引用与参数外层容器。`creo_capabilities.references` 保留原有示例键，新增 `syntax` 与 `by_tool`，应按具体工具和参数选用示例。工具列表中的 schema 和描述也给出轴、边、倒圆集合和草图支撑面的格式。

示例中的 ID 只说明 JSON 类型，实际值必须从当前模型巡检取得；几何 ID 和特征 ID 不能互换。标签必须是该模型已有的 MCP 别名。原生几何是否符合要求仍需实际解析、再生和保存重载验证。

## 轴阵列

`creo_axis_pattern.axis` 接受以下三种裸对象，不增加 `reference` 或 `edge` 包装：

```json
{"kind": "axis", "id": 83}
{"kind": "datum_axis_feature", "label": "t82_da1"}
{"kind": "datum_feature", "label": "t82_da1"}
```

第一种是几何轴 ID；第二种是明确的轴特征标签，推荐使用。第三种是为报告 §7-N1 增加的兼容写法：**仅在 axis_pattern.axis 中**按轴参数上下文转换为 datum_axis_feature。它不会把一个实际基准平面变成轴；标签指向的特征仍必须包含一根可解析的轴。

其它参数中的 datum_feature 继续代表基准平面。`{"kind":"datum_plane","axis":"z"}` 的 axis 表示平面法向，不能用作旋转轴。阵列轴必须先于 leader；必要时创建独立基准轴，再用 creo_reorder_features 调整顺序。高层工具和 execute_plan 使用同一规范化逻辑，非法轴类型、缺少 ID/标签会在入队前返回可操作示例，revision 防护保持有效。

## 各工具的外层形状

| 工具 / 参数 | 完整形状或规则 |
| --- | --- |
| datum_plane.reference | 裸平面/面引用，如 `{"kind":"datum_plane","axis":"z"}` 或 `{"kind":"datum_feature","label":"plane_label"}` |
| datum_axis.references | 裸引用数组，如两张基准平面；圆柱面、直边或现有轴需满足实际几何要求 |
| datum_csys / datum_points.reference | 裸坐标系引用，如 `{"kind":"default_csys"}`、几何 csys ID 或 datum_csys_feature 标签 |
| hole.placement/reference1/reference2 | 各自直接传入裸引用，placement 为放置面，reference1/2 为定位参考 |
| draft.surfaces/neutral_plane/pull_direction | surfaces 是裸面引用数组；neutral_plane 和 pull_direction 分别是裸单引用 |
| boolean_bodies.targets/tools | 裸 body 引用数组，须明确不同 body ID；不能传特征 ID |
| solidify.reference | 裸平面/曲面参考；平面裁剪示例使用 mode=cut，quilt 分支按既有能力限制验收 |
| surface_fill.sketch | 草图特征标签或特征 ID（字符串或整数），无需 `{kind:...}` 对象 |
| thicken.reference | 裸 quilt 或 quilt_feature 引用 |
| sheetmetal_flange.edge | 裸 `{"kind":"edge","id":N}`；参数内部不再加 edge/reference 包装 |
| round/chamfer.references | **集合对象数组**：`[{"edge":{"kind":"edge","id":N}}]`，或 `[{"surfaces":[{"kind":"surface","id":A},{"kind":"surface","id":B}]}]`；裸边数组不等于集合数组 |
| create_sketch.plane | 主平面字符串 `XY/XZ/YZ`；字典形式为 `{"reference":{"kind":"surface","id":N},"origin":[x,y,z],"u_axis":[x,y,z]}`，origin/u_axis 可省略，reference 容器必需 |

这些集合和坐标包装承载不同的参数含义，不能简单地给所有裸引用增加同一层包装。此修复兼容报告中的轴标签、补齐引用契约，不更改原生执行器或创建额外几何。

实现与当前验收范围见 [BUG-006](work-items/BUG-006.md) 和 [本次证据](validation/BUG-006.md)。

## 待核对的补充契约

[FEAT-008 首批任务](work-items/FEAT-008.md)跟进专用底板holes的客户端传输形状、对称拉伸depth口径与“查当前可编辑尺寸再修改”的闭环；[BUG-031](work-items/BUG-031.md)核对共面多候选/默认基准选择，结合字符串plane+offset产生构造特征的可见性说明。[履带反馈补录](validation/TRACK-FEEDBACK-2026-10-16.md)仅提供外部来源。上述是待核对工作，不是已新增字段或已变更接口；仍须按当前工具schema和真实返回使用，不把报告中的建议引用/参数当作已支持形式。
