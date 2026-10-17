# 2026-10-17 · CREO Parametric 10.0.0.0 · MCP_CREO_MechDog v0.3.3 问题反馈

> **提交人**：WorkBuddy（逆向工程侧用户）
> **会话日期**：2026-10-17（v0.3.3 复验）
> **前序反馈**：`2026-10-14_CREO_0.3.0_核心问题_草图弧方向与静默失效机制.md`
> **被测对象**：`MCP_CREO_MechDog v0.3.3`，Creo Parametric 10.0.0.0，Python MCP server + `creo_worker.exe` / `creo_blend_sync.dll`
> **被测成果**：简易单级齿轮泵，11 个唯一零件 + 18 实例总装（几何 100% 来自一份自然语言规格 TXT，未导入任何实体）

---

## 0. 一句话结论

**0.3.1 / 0.3.2 已闭环我此前的两个高优先级缺陷**（`list_models` 响应溢出 = BUG-013；孔类零去料静默 = BUG-022），本次均实测通过。
**但两件事必须提请作者注意：**

1. **同类的「零去料静默」只在 `hole` op 上加了守卫，`extrude` / `revolve` 的切除路径仍然完全无守卫** —— 实测一个板外圆形切除 `success:true`、体积分毫未变、零提示，且 3 个无效特征被正常落盘进特征树。这正是我齿轮泵项目里 SC3 记录的真实缺陷类。
2. **我此前的核心问题「草图弧无 `dir` 参数 + 恒 CCW 归一化，且 >180° 主弧零告警」在 0.3.3 原样未动**（`generic.cpp:736-764` 一字未改）。本次用一组对照实验把它量化：**同一组图元、仅角度书写顺序不同，体积相差 10 倍（142.699 → 1428.097 mm³），两次都返回 `success:true`、无 warning、无 error。**

另新发现两项：装配组件 `model_name` 不可识别零件；`rotation` 欧拉角语义反直觉（对应 BUG-045，13/18 实例正落在万向锁点上）。

---

## 1. 验收范围与方法

| 项 | 方法 |
|---|---|
| 零件核验 | `creo_list_models(detail="compact")` 分 3 页翻完，逐项核对 `model_id` / `model_name` / `revision` / `status` / `volume_mm3` |
| 总装核验 | `creo_inspect_model(section="components")` 一次取回 18 实例，逐组件 4×4 变换与规格第 8 章 3×3 行主序姿态矩阵 + 平移逐元素比对 |
| 映射还原 | `assemble_component` 的 `label` → `aliases[label].source_model_id` → 零件 |
| 缺陷回归 | 新建 6 个隔离测试模型，逐项复现既往缺陷 |
| 代码定位 | 只读 `native/*.cpp` 与 `src/creo_mechdog/*.py`，未修改 MCP 任何文件 |

---

## 2. 验收结论（成果侧）

### 2.1 零件：11/11 全部 `ready`，体积与审计记录逐位一致

| 零件 | model_name | model_id | rev | status | 体积 mm³（0.3.3 读回） | 审计记录 |
|---|---|---|---|---|---|---|
| P01 泵体 | p01 | `b67c0c2ecb4e4ec586ee3e3c4a508aad` | 6 | ready | 194964.43489931818 | 194964.43 ✓ |
| P02 泵盖 | p02 | `af9ba0f64a9441b6919566f1bb857a4c` | 4 | ready | 71497.72379208363 | 71497.72 ✓ |
| P03 垫片 | p03 | `b1baff546c3841acbeeb1fd3e8da4684` | 2 | ready | 4280.653331473643 | 4280.65 ✓ |
| P04 短轴 | p04b | `4207e164b1f340f4bd745f56a9e6c733` | 5 | ready | 3680.2923858966833 | 3680.29 ✓ |
| P05 长轴 | p05d | `c98791d671f64a0dafa5886e73fefb37` | 2 | ready | 16031.418501043347 | 16031.42 ✓ |
| P06 楔键 | p06_key | `5ffa02142ca14a108c27a65a1e7c6107` | 3 | ready | 268.86211833683615 | 268.86 ✓ |
| P07 齿轮 | p07b | `6326295ac58549089948e77ea5d780af` | 2 | ready | 14214.879368534606 | 14214.88 ✓ |
| P08 填料压盖 | p08 | `95546f9739c54d9f8c4c201921967b65` | 2 | ready | 3559.948075292834 | 3559.95 ✓ |
| P09 填料 | p09 | `959fa0e03f464c2ea6a5c804a6781aef` | 2 | ready | 4256.393219015979 | 4256.39 ✓ |
| P10 压盖螺母 | p10b | `8188239bc5174ba8b0f27e0952ad8b36` | 2 | ready | 10173.325791268668 | 10173.33 ✓ |
| P11 六角螺栓 | p11 | `c250b93cc04348f8a21d82be53ea78f9` | 2 | ready | 906.8772615988568 | 906.88 ✓ |
| **总装** | pump_asm | `11fe34b528304b6dab82d6915156c2f0` | 7 | ready | 342852.93653872894 | 342852.94 ✓ |

`inspection.counts.components = 18`，`has_solid = true`，`healthy = true`。

### 2.2 总装：18/18 组件变换 EXACT

| 实例 | 零件 | feature_id | 旋转最大偏差 | 平移最大偏差 | 正交性 \|RRᵀ−I\| | 判定 |
|---|---|---|---|---|---|---|
| I001 | P01 泵体 | 40 | 0.000e+00 | 0.000e+00 | 0.0e+00 | EXACT |
| I002 | P03 垫片 | 43 | 0.000e+00 | 0.000e+00 | 0.0e+00 | EXACT |
| I003 | P02 泵盖 | 46 | 0.000e+00 | 0.000e+00 | 0.0e+00 | EXACT |
| I004 | P07 齿轮A | 49 | 4.882e-08 | 0.000e+00 | 2.3e-33 | EXACT |
| I005 | P07 齿轮B | 52 | 3.377e-08 | 0.000e+00 | 2.2e-16 | EXACT |
| I006 | P04 短轴 | 55 | 1.225e-16 | 0.000e+00 | 7.5e-33 | EXACT |
| I007 | P06 楔键3 | 58 | 6.123e-17 | 0.000e+00 | 3.7e-33 | EXACT |
| I008 | P06 楔键2 | 61 | 8.531e-10 | 0.000e+00 | 2.2e-16 | EXACT |
| I009–I014 | P11 螺栓 ×6 | 64/67/70/73/76/79 | 6.123e-17 | 0.000e+00 | 0.0e+00 | EXACT |
| I015 | P05 长轴 | 82 | 6.123e-17 | 0.000e+00 | 3.7e-33 | EXACT |
| I016 | P09 填料 | 85 | 6.123e-17 | 0.000e+00 | 3.7e-33 | EXACT |
| I017 | P08 填料压盖 | 88 | 6.123e-17 | 0.000e+00 | 3.7e-33 | EXACT |
| I018 | P10 压盖螺母 | 91 | 1.225e-16 | 0.000e+00 | 0.0e+00 | EXACT |

- **合计**：18/18 组件；旋转最大偏差 **4.882e-08**（即规格矩阵自身 6 位小数舍入下限）；平移最大偏差 **0.0**；正交性最大偏差 2.2e-16（机器精度）。
- 全部 `placement = fixed`（`PRO_ASM_FIX`）、`underconstrained = false`、`packaged = false`。
- **体积闭合**：零件体积加权和 342852.93654 vs 装配实测 342852.93653872894，闭合差 **5.821e-11 mm³（0.000000%）**。

### 2.3 调用链

建模全程仅调用 `mcp__MCP_CREO_MechDog__*`；op 仅 sketch / extrude / revolve / assemble_component / datum_axis / axis_pattern / component_placement / chamfer 八类，**导入类 op 计数 0**；未直接调用任何 Creo 官方接口，未导入任何实体（STEP / Parasolid / STL / 原文件均未使用）。

---

## 3. 问题分级总表

| # | 问题 | 严重度 | 0.3.3 状态 | 对应既往 |
|---|---|---|---|---|
| **P1** | 草图弧无 `dir` 参数 + 恒 CCW 归一化，>180° 主弧零告警 → 静默产生数量级错误几何 | **高** | ❌ 未修复 | 0.3.0 P1/P2 |
| **P2** | `extrude`/`revolve` 切除「零去料」无守卫（BUG-022 只覆盖 `hole`） | **高** | ❌ 未修复 | SC3 同类 |
| **P3** | 自交/不可拉伸轮廓失败诊断不可用（仅回 Toolkit 返回码） | 中 | ❌ 未修复 | 0.3.0 P2 |
| **P4** | 装配组件 `model_name` = `C_<jobid[:16]>_<n>`，无法识别零件 | 中 | ❌ 未修复 | 新发现 |
| **P5** | `rotation` 欧拉角语义反直觉；13/18 实例落在万向锁点 | 中 | ❌ 未修复 | BUG-045 |
| **P6** | `hole` op 无沉孔 / 锥孔参数 | 中 | ❌ 未修复 | 新发现 |
| **P7** | `revolve` 省略 `axis` 静默回退内部参考轴，且不回报实际所用轴 | 低 | ❌ 未修复 | 新发现 |
| — | `list_models` 响应溢出 | 高 | ✅ **已修复**（BUG-013） | 0.3.0 P7 |
| — | 孔类零去料静默 | 高 | ✅ **已修复**（BUG-022） | 0.3.0 P3/P4 |

---

## 4. P1（核心）· 草图弧无 `dir` 参数且恒 CCW，>180° 主弧零告警

### 4.1 代码位置（0.3.3 现状，一字未改）

**Schema 侧** — `src/creo_mechdog/schema.py:46-55`：

```python
class Arc(Circle):
    type: Literal["arc"]
    start_angle: float
    end_angle: float

    @model_validator(mode="after")
    def span(self):
        if abs((self.end_angle - self.start_angle) % 360) < 1e-10:
            raise ValueError("Arc requires distinct endpoints; use circle for a complete circle")
        return self
```

**没有 `dir` 字段**；唯一的校验只排除整圆，**完全不检查扫过角是否 >180°**。

**Native 侧** — `native/generic.cpp:736-764`：

```cpp
} else if (type == "arc") {
    Pro2dArcdef a = {};
    ...
    a.start_angle = atan2(p[1] - a.center[1], p[0] - a.center[0]);
    a.end_angle   = atan2(q[1] - a.center[1], q[0] - a.center[0]);
    if (dot(V{loc[2][0], loc[2][1], loc[2][2]}, frame.n) < 0)
        std::swap(a.start_angle, a.end_angle);
    double turn = 2 * acos(-1.0);
    a.start_angle = fmod(a.start_angle + turn, turn);
    a.end_angle   = fmod(a.end_angle + turn, turn);
    ...
    if (a.end_angle <= a.start_angle)
        a.end_angle += turn;          // ← 恒强制为 CCW
    CK(ProSectionEntityAdd(section, (Pro2dArcdef *)&a, &id));
}
```

弧的方向**只能由 `start_angle` / `end_angle` 的大小关系隐式决定**，且当 `end <= start` 时无条件 `+360°` 变成 CCW。这里**没有任何一处**检查或告警扫过角超过 180°。

### 4.2 对照实验（决定性证据）

两个新建零件，图元完全相同（圆心 (0,0)、R10、同一条弦 (10,0)–(0,10)），**只有角度的书写顺序不同**，各配一条闭合直线后 `extrude depth=5`：

| 案例 | arc `start_angle` → `end_angle` | 实体包络框 | 体积 mm³（实测） | 解析值 mm³ | 相对差 |
|---|---|---|---|---|---|
| **A 劣弧** | 0° → 90° | [0,10] × [0,10] | **142.699081698** | 142.699081699 | 7e-12 |
| **B 主弧** | 90° → 0° | **[-10,10] × [-10,10]** | **1428.097245102** | 1428.097245096 | 4e-12 |

- 两者都返回 `success: true`、`toolkit_code: 0`、**零 warning、零 error**。
- 案例 B 的 sketch 回显**原样返回** `{"start_angle": 90.0, "end_angle": 0.0}`，既不归一化、也不提示"这将被解释为 270°  CCW 主弧"。
- 案例 B 的体积是案例 A 的 **10.0 倍**。

**含义**：用户按自然的「顺时针读法」书写角度（从 90° 往下写到 0°，这是多数工程图纸/规格文本的顺序），得到的是 270° 主弧，几何被静默放大一个数量级，且**从返回值完全看不出差别**。

### 4.3 与需求侧规则的对应

本次建模的规格文本第 10.2 节 C1 已明确警示：

> 「dir 填反 → >180° 主弧 → 轮廓仍闭合、拉伸仍成功但咬入零件内部」；「光滑外轮廓过渡弧应为劣弧，内腔两弧+竖弦才用主弧」

也就是说，**需求侧已经预见到了这个失效模式并写进了规则，而工具侧没有任何机制帮助用户发现它**。我的齿轮泵 P02/P03 就正好踩在这个坑里：规格附录 B.4 的 A11 弧 `dir=-1` 是笔误，按字面得到 297.82° 主弧，而 MCP 静默接受，导致外轮廓面积 4826.73 mm²（比劣弧版 5027.79 mm² 小 4.0%），在板左下咬出一个缺口。详见分析文件 `creo_gear_pump_analysis.json` 的 SC1/SC2。

### 4.4 建议（按优先级）

1. **`Arc` 增加 `dir` 字段**（`+1` / `-1`，或等价的 `sweep_deg` / `major: bool`），让用户能显式表达「我要的是劣弧但起点在后的那种写法」。这是唯一能根治的一项。
2. **归一化后扫过角 > 180° 时，至少在返回值里放一个 `warnings` 字段**（例如 `"arc 'a1' normalized to a 270.0 deg CCW sweep; verify this is intended"`）。零成本，能把静默失效变成可见失效。
3. **顺带**：失败时给具体原因（见 P3）。

---

## 5. P2 · `extrude` / `revolve` 切除「零去料」仍无守卫

### 5.1 事实

BUG-022 的去料量守卫只加在 `hole` op 上（`native/generic.cpp:1134-1138`）：

```cpp
double removed = before_volume - volume();
if (removed <= std::max(1e-9, fabs(before_volume) * 1e-12))
    throw std::runtime_error("Hole removes no material; check reference offsets, "
                             "placement, flip and overlap with existing holes");
```

**`extrude_or_revolve`（`generic.cpp:913` 起）没有等价的检查。**

### 5.2 实测复现

模型 `rt_hole_plate`（60×40×10 平板，体积 24000，已含一个合法 Ø8 通孔，rev 2，体积 23497.344705562704），执行：

```json
{"op": "sketch", "label": "sk_out", "plane": "XY",
 "entities": [{"type": "circle", "name": "c1", "center": [100, 100], "radius": 5}]},
{"op": "extrude", "label": "cut_out", "sketch": "sk_out",
 "depth": 10, "mode": "cut", "direction": "positive"}
```

圆心 (100,100) 完全在 0..60 × 0..40 板外，切除实际去料为 0。结果：

| 字段 | 值 |
|---|---|
| `status` | **succeeded** |
| `success` / `toolkit_code` | `true` / `0` |
| `operations` | `[{"sk_out", succeeded: true}, {"cut_out", succeeded: true}]` |
| 体积 | **23497.344705562704（与操作前完全一致，去料 0）** |
| warning / error | **无** |
| `material_removed_mm3` | **字段不存在** |
| 落盘 | `rt_hole_plate.prt.4`，rev 2 → **3** |

且无效特征被**正常写进特征树**（`inspection.counts.features` 12 → 15）：新增 `SK_OUT`（id 120，sketch）、`CUT_OUT`（id 127，type 916 cut）以及 2 个 `no_name` datum plane（id 121/128）。

### 5.3 影响

这不是理论缺陷。我的齿轮泵规格第 5 动作「P02 的 6×Ø13 沉孔，Z=12 沿 +Z 切 1」在规格坐标下**实际去料为 0**（该 6 孔心处 Z=12 以上是空气），当时 MCP 静默接受，我只能在事后靠体积比对才发现。见 `creo_gear_pump_analysis.json` 的 SC3。

**规格书写错误 + 工具不报 = 错误被永久固化进特征树**，且因为 rev 正常递增、`status: ready`，后续任何自动校验都不会再注意到它。

### 5.4 建议

把 `generic_hole` 里去料量守卫的那 5 行**原样搬到 `extrude_or_revolve` 的 `mode == "cut"` 分支**（`revolve` 同一条路径，一并覆盖），并在成功时统一回 `material_removed_mm3`。对 `mode == "add"` 建议至少回 `material_added_mm3`（可用于自动断言）。

---

## 6. P3 · 自交 / 不可拉伸轮廓的失败诊断不可用

### 6.1 实测

领结形自交轮廓（4 条直线，(0,0)→(10,10)→(0,10)→(10,0)→(0,0)，其中 (0,0)-(10,10) 与 (0,10)-(10,0) 交于 (5,5)）：

```json
{"status": "failed", "toolkit_code": -1,
 "message": "Toolkit call ProFeatureWithoptionsCreate failed with code -1 during execute_extrude",
 "result": {"failed_operation_index": 1, "failed_stage": "execute_extrude",
            "failed_toolkit_call": "ProFeatureWithoptionsCreate",
            "success": false, "rollback_succeeded": false}}
```

**好消息**：失败被正确检测，且新建模型被正确丢弃（`status: failed`、`revision: 0`、`part_file: null`、`inspection_available: false`），没有留下半个零件。

**问题**：`result` 里**没有任何 `errors` / `warnings` 数组**（实测 error 相关 key 为 `[]`）。用户拿到的唯一信息是「某次 Toolkit 调用返回 -1」，既不知道是**草图自交**，也不知道该去改哪个实体。对一个以自然语言为输入的工具来说，这个诊断等级基本不可用。

### 6.2 附带小问题

`rollback_succeeded: false` 对**新建模型恒为 false**（没有检查点可回退）。这个字段名很容易被误读成"回滚失败了"。建议对无检查点的场景返回 `null` 或增加 `rollback_applicable` 语义。

### 6.3 建议

`ProFeatureWithoptionsCreate` 失败后，用 `ProErrorGet` / `ProMessageRead` 取 Creo 的原始错误文本，塞进 `result.errors[]`（含 stage、operation_index、message）。另外可在拉伸前对 sketch 做一次自交预检（`ProSection...` 或自行求交），把「轮廓自交」变成前置明确错误。

---

## 7. P4 · 装配组件 `model_name` 不可识别零件

### 7.1 代码位置

`native/advanced.cpp` → `assemble_component`：

```cpp
ProMdlName copy_name;
std::wstring token = std::filesystem::path(generic_job).filename().wstring();
swprintf_s(copy_name, L"c_%s_%u", token.substr(0,16).c_str(), (unsigned)operation_results.size());
ProMdl copy;
CK(ProMdlnameCopy(child, copy_name, &copy));
```

组件模型名 = `c_` + **job ID 前 16 位** + `_` + 操作序号。Creo 会把模型名转大写，所以读回是 `C_<16hex>_<n>`。

而 `assembly_inspection` 报的是 `ProMdlNameGet(child)`；用户给的 `label` 只写进了组件 **feature** 名（`ProModelitemNameSet(&comp, name)`），查询输出里**完全丢失**。

### 7.2 实测后果

同一个装配 job `c37013891d824fc9a7a50a3d822f6f67` 里装入了 **P01 泵体 / P03 垫片 / P02 泵盖三个不同零件**，读回的组件名是：

```
C_C37013891D824FC9_0   ← P01 泵体
C_C37013891D824FC9_1   ← P03 垫片
C_C37013891D824FC9_2   ← P02 泵盖
```

另一个 job `36f4a0bb0cbc404ba03bbb3ec83d9491` 装入 **P05 长轴 / P09 填料 / P08 填料压盖 / P10 压盖螺母四个不同零件**，组件名 `C_36F4A0BB0CBC404B_0 .. _3`。

即：**同名不同件、同件不同名**。仅凭 `components[].model_name` 无法判断任何一个组件是哪个零件，也无法把同一零件的多个实例关联起来。

### 7.3 缓解（说明这不是数据丢失）

`creo_list_components` 返回的 `aliases` 字段可以完整恢复映射，我就是靠它完成 18/18 核对的：

```json
"i001_p01_body": {"feature_id": 40, "op": "assemble_component", "placement": "fixed",
                  "source_model_id": "b67c0c2ecb4e4ec586ee3e3c4a508aad",
                  "source_revision": 6, "source_snapshot": true}
```

所以这是**可用性 / 可诊断性缺陷**，不是数据缺陷。但代价是：每次核对装配都要先拉一份 68K 字符的 `aliases`，再自己 join。

### 7.4 建议（一行修复）

`assembly_inspection` 里对每个组件增报两字段即可：

```cpp
ProName feat_name; ProModelitemNameGet(&comp, feat_name);   // 拿回用户 label
components.push_back({{"feature_id", comp.id},
                      {"model_name", utf8(name)},
                      {"component_name", utf8(feat_name)},   // ← 新增
                      {"source_model_id", ...},              // ← 新增（aliases 里已有）
                      {"transform", matrix}, ...});
```

### 7.5 需要文档化的语义（重要）

`aliases[*].source_snapshot = true` + `ProMdlnameCopy` 意味着：**每个组件是源零件的独立副本快照，装配体与源零件之间没有活链接**。

代码注释本身写明了动机（"Assembly backups change component origins. Isolate a revision snapshot so inserting a component never moves the separately editable source model."），但 README 第 67 行只写了「组件版本副本」，没有强调后果。**装配完成后修改 p01，pump_asm 不会更新。** 对逆向验证场景无所谓，但对想做参数化迭代的用户这是隐性陷阱，建议在 `creo_assemble_component` 的 docstring 和 README 里显式写出。

---

## 8. P5 · `rotation` 欧拉角语义反直觉，且 13/18 实例落在万向锁点

### 8.1 约定（本次完整推导并验证）

`native/advanced.cpp` → `rigid_transform`：

```cpp
R_std = Rz(rz) · Ry(ry) · Rx(rx)          // 列向量约定 v_world = R_std · v_local
matrix[i][j] = R_std[j][i]                 // 转置成 ProMatrix（行向量约定 v_world = v_local · M）
```

即：`rotation = [rx, ry, rz]`（度），**外旋 XYZ**，存储的 ProMatrix 是 `R_std` 的转置。

**18/18 实例实测残差 ≤ 5.150e-07**（该值正好等于规格矩阵自身 6 位小数的舍入下限），约定自洽、可复现、无手性歧义。这一点是好的。

### 8.2 反直觉之处

| 输入 | 存储矩阵 | 用户直觉期望 |
|---|---|---|
| `rotation = [0, 90, 0]` | `[[0,0,-1],[0,1,0],[1,0,0]]` = **Ry(−90°)** | Ry(+90°) = `[[0,0,1],[0,1,0],[-1,0,0]]` |

「绕 Y 轴转 +90 度」读作 `Ry(+90°)` 的用户会得到**正好反向**的结果。这与 0.3.2 验收报告里记录的 P5（`[0,90,0]` 实得 Ry(−90°)）是同一件事，**0.3.3 仍未处理**，`docs/work-items/BUG-045.md` 也仍是开放状态。

### 8.3 万向锁集中度

本装配 18 个实例中，**13 个的 |ry| 正好 = 90°**（I004/I005/I007/I008/I009–I014/I015/I016/I017）。在锁点上 `rz` 自由度退化，只能靠约定「锁点取 `rz = 0`」+ 把欧拉角写到 9 位小数，才能把残差压到 5e-8。若用户给的规格是 6 位小数姿态矩阵（很常见），反解欧拉角再回代，残差就只能到 5e-7 量级——**这就是本次旋转最大偏差 4.88e-8 的来源，已接近但不优于规格自身精度**。

### 8.4 建议

1. **`assemble_component` / `component_placement` 增接受 3×3 或 9 元素行主序矩阵**（外加 `translation`），与欧拉角二选一。这是唯一能彻底绕开万向锁和手性歧义的输入形式，对逆向/装配复核类任务几乎是刚需。
2. 若维持欧拉角，至少在 docstring 里写出公式 `R = (Rz(rz)·Ry(ry)·Rx(rx))ᵀ`、单位、以及「`ry=+90` 存储为 Ry(−90°)」这个具体例子。
3. 读回侧：`components[].transform` 已直接给 4×4，很好；建议同时在文档明确这是**行向量约定**（平移在最后一行而非最后一列），避免与列向量惯例混用。

---

## 9. P6 · `hole` op 无沉孔 / 锥孔

`src/creo_mechdog/schema.py:382-392`：

```python
class HoleOp(StrictModel):
    op: Literal["hole"]
    placement: dict[str, Any]
    reference1: dict[str, Any]
    reference2: dict[str, Any]
    offset1: float = 0
    offset2: float = 0
    diameter: Positive
    depth: Positive | None = None      # None = 通孔
    flip: bool = False
```

`native/generic.cpp` 的 `generic_hole` 只建 `PRO_E_HOLE_STD_DEPTH` 直孔；`counterbore` / `countersink` / `cbore_diameter` / `csink_angle` 在 `native/` 与 `src/` 全库**零命中**。

**影响**：沉孔（台阶孔）和锥坑孔无法用单个孔特征表达。我的齿轮泵 P02 需要 6×Ø13 沉孔，只能用「sketch 圆 + extrude cut」变通，特征树可读性和可参数化性都打折，且无法给孔加标准注释/调用。

**建议**：`HoleOp` 增加 `counterbore: {diameter, depth} | None` 与 `countersink: {diameter, angle} | None`，映射到 `PRO_E_HLE_ADD_PARAMETERS` 下的沉头/锥坑元素。

---

## 10. P7 · `revolve` 省略 `axis` 时静默回退

`RevolveOp.axis` 在 schema 里是**可选**的（`schema.py:377`，`dict[str, Any] | None = None`），native 侧 `generic.cpp:948-955`：

```cpp
if (op.contains("axis")) {
    integer(root, PRO_E_REVOLVE_AXIS_OPT, PRO_REV_AXIS_EXT_REF);
    ... resolve(op["axis"]) ...
} else
    integer(root, PRO_E_REVOLVE_AXIS_OPT, PRO_REV_AXIS_INT_REF);   // 静默回退
```

省略 `axis` 时回退到 `PRO_REV_AXIS_INT_REF`（草图内部参考轴），**返回值里不报告实际所用的回转轴**，用户无法从结果确认回转轴是哪一个。本次齿轮泵的 18 处 revolve 我都走了隐式路径（把轮廓画在相对草图内轴正确的位置），能work，但属于"靠猜"。

**建议**：`revolve` 成功后回一个 `axis` 描述（用了哪条几何/哪个内部轴、方向向量），与 `hole` 成功后回 `axes` 的做法保持一致。

---

## 11. 其他低优先观察

| 观察 | 说明 |
|---|---|
| 零件级特征无 delete / suppress | `modify_component` 的删除分支只对装配组件生效；零件特征建错只能重建整个模型。对试错式建模成本较高。 |
| 草图 `dimensioning: "auto"` 的策略阈值不透明 | `auto` 会在 count≥10 或 extent>1000 时切到 `coordinates`，本次实测小轮廓落到 `autodim`（epsilon 1e-4）。折线端点被 round 到 4 位小数，与弧端点差 1e-4 mm 就会导致轮廓不闭合——这个坑我踩过一次，建议文档明示各模式的精度上限。 |
| 参数命名无命名空间保护 | 模型级 / 特征级参数名容易撞车，且拼错不回显候选值。 |

---

## 12. 已修复项闭环确认（0.3.1 / 0.3.2）

### 12.1 BUG-013（既往 P7：`list_models` 响应溢出）✅

| 验证 | 结果 |
|---|---|
| `detail` 默认值 | `compact` ✅ |
| 单页预算 / 分页 | 32 KiB，`complete` + `next_cursor` ✅ |
| 210 特征模型 `detail=full, section=features, limit=50` | 精确返回 50 条，`complete:false`，`next_cursor` 正常 ✅ |
| 翻 3 页取回全部 11 零件 + `pump_asm` | 无溢出，无需落盘 ✅ |
| 真实零值与 null 区分（BUG-014） | `counts` 缺失项为 `null`，`volume_mm3` 为真实 0 时给 0 ✅ |

### 12.2 BUG-022（既往 P3/P4：孔类零去料静默）✅ 3/3 通过

平板 60×40×10（体积 24000），顶面 surface 58、边 59/60：

| 案例 | 结果 |
|---|---|
| **合法孔** Ø8，offset1=30 / offset2=20 → 中心 (40,30) | `success:true`；`material_removed_mm3 = 502.6552944`（解析 π·4²·10 = 502.6548246，rel 9.3e-7）；原生孔轴 `id=95, start=(40,30,10), end=(40,30,0)`；体积 24000 → 23497.344705562704 ✅ |
| **重合孔**（同面同基准同偏移同直径） | `status:failed`，`message:"Hole removes no material; check reference offsets, placement, flip and overlap with existing holes"`，`failed_stage:"execute_hole"`，**`rollback_succeeded:true`** ✅ |
| **板外孔**（offset1=100，孔心 y=100 在板外） | 同上，明确失败 + 回滚；回滚后体积 23497.344705562704 = rev 2 状态 ✅ |

诊断信息同时点名的三类根因（reference offsets / placement & flip / overlap with existing holes）都很准确，这条修复质量很高。**唯一遗留是它没被复制到 extrude/revolve 切除路径**（见 P2）。

---

## 13. 复现环境

| 项 | 值 |
|---|---|
| MCP_CREO_MechDog | v0.3.3（`version.py: VERSION = "0.3.3"`） |
| Creo | Parametric 10.0.0.0，`release_numeric: 42`，`toolkit_code: 0`，`connected: true`，`worker_exit_code: 0` |
| 会话状态 | `creo_session_status` 正常；单线程，并发提交报 `Creo Toolkit is busy` |
| 本次新建诊断模型 | `rt_arc_minor`（3931c8e09801464ca74512e12b33d1a5）、`rt_arc_major`（ea64e17f75b742ae8054842fe87581a0）、`rt_bowtie`（e39dc201e63140b4aa7e7a02e022b43f，failed）、`rt_hole_plate`（cc531259b9e8423ea6921b0a850bff5d） |
| 本次诊断 job | `e989ec54e44e45399d731978c82e505e`（R3a）、`08a49ac4c7fd4c50bacc189ee35b3e4b`（R3b）、`af2262c716634a4da85b5b53fc51fa06`（R3c）、`1714c04ff10043ba8df3cf8f63a8e1f3`（平板）、`e53b66ea11ec43a2a885e9b34fc51acb`（合法孔）、`f234a44b49464b9db60aa904779f1068`（重合孔）、`c944301542dc4ce999acb2a6c5544ce1`（板外孔）、`de3fb70eb65d4b6cb92ae523304347e5`（板外切除） |
| 分析文件 | `creo_gear_pump_analysis.json`（workspace 根） |

---

## 14. 给作者的三句话总结

1. **弧的 `dir` 请一定加**，并且**任何扫过角 >180° 的弧都要告警**——这是唯一一个能让正确输入产生 10 倍错误体积且毫无提示的缺陷。
2. **把 `generic_hole` 里那 5 行去料量守卫搬到 `extrude_or_revolve` 的 cut 分支**，顺手让所有增/切特征都回 `material_removed_mm3` / `material_added_mm3`。
3. **`assemble_component` 请支持直接填 3×3 / 9 元素姿态矩阵**，并且**组件查询请把用户的 `label` 报出来**（`ProModelitemNameGet(&comp, ...)`，一行）。

感谢 0.3.1–0.3.3 的连续修复，`list_models` 分页和孔去料守卫这两项已经能切实减少我的核对工作量。
