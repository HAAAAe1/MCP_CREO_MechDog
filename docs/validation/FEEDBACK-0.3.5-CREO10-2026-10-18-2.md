# CREO 10.0.0.0 · MCP_CREO_MechDog 0.3.5 核心问题反馈：草图弧无 dir 参数且恒 CCW 致静默主弧

> 反馈人：终端用户（非项目作者）
> 记录日期：2026-10-18（Asia/Shanghai）
> 实测版本：**0.3.5**（`version.py` → `VERSION = "0.3.5"`），从 0.3.3/0.3.4 升级
> 环境：Windows 10 x64 / **Creo Parametric 10.0.0.0**（`config.json: creo_root = D:\Program Files\PTC\Creo 10.0.0.0`，会话探测 `release_numeric=42`）/ Windows SDK 10.0.26100.0 / MSVC 14.44.35207 / Python 3.13
> 会话状态：`connected=true`、`toolkit_code=0`、`state="ready"`、`message="Toolkit connection verified"`、`coordinator_pid=61672`、`launch_attempt=15`
> 仓库：https://github.com/wudahua/MCP_CREO_MechDog

---

## 0. 摘要

**本轮为实机验收**：全部结论来自 Creo 10.0.0.0 上的真实建模作业（8 个 job、5 个诊断零件），未采用任何"读码推断"替代实测。

| 项 | 0.3.5 状态 | 证据强度 |
| --- | --- | --- |
| **BUG-054 / DEV-033**：extrude/revolve 实体切除零去料守卫 | ✅ **已修，5/5 实测通过** | 实机（见 §1） |
| **BUG-022**：hole 零去料守卫（姊妹守卫） | ✅ **仍然闭环** | 实机（§1 用例 6） |
| `material_removed_mm3` 回报 | ✅ 有效切除均正确返回 | 实机 |
| 失败回滚 / revision 不递增 / 无效特征不落盘 | ✅ 三项全部满足 | 实机 + 文件系统 |
| **P1 草图弧无 dir 参数且恒 CCW** | ❌ **仍未修（核心问题）** | 实机对照实验（§2） |
| **P3 自交轮廓诊断** | ❌ 仍只报原始 Toolkit 错误，无 `errors` 数组 | 实机（§3） |
| **P4 组件 model_name 不可识别** | ❌ 仍未修 | 源码 + 0.3.5 实读（§4） |
| **P5 旋转仅支持 XYZ 欧拉角** | ❌ 仍未修 | 源码（§5） |
| **P6 hole 无沉孔/锥孔** | ❌ 仍未修 | 源码（§6） |
| **P7 revolve 轴不回报** | ❌ 仍未修 | 源码 + 实机（§7） |
| BUG-013 `list_models` 分页 | ✅ 闭环 | 3 页翻完定位全部模型 |
| BUG-056 通道 ~37–41s 静默失效 | ⚠️ 本轮 8 job / 约 8 分钟连续建模**未复现** | 实机 |

**一句话结论**：0.3.5 把我在 0.3.3 反馈的 P2（切除零去料无守卫）做成了硬失败并完整落地，这是本轮最有价值的修复；但**同一条反馈里的 P1（弧方向）原样未动**，它依然是全工具链唯一会"静默产出错误几何"的缺陷——而新加的切除守卫恰恰拦不住它（错误弧向产出的是体积非零、形状错误的实体）。

---

## 1. ✅ BUG-054 / DEV-033 切除零去料守卫 —— 实测通过

这正是我 0.3.3 反馈文档中建议"把 `generic_hole` 里那 5 行去料量守卫搬到 `extrude_or_revolve` 的 cut 分支"的事项。0.3.5 已实现，且我按 6 个场景逐一实测。

诊断零件：`rt_cut_guard_a`（`model_id=1825bf70f4b540c4a7180adcfd60acf2`）、`rt_cut_guard_b`（`model_id=7cd81f7145ed4693b0c850cf004d4a94`）。

### 1.1 六用例结果

| # | 场景 | job_id | 解析预期 | 实测 | 判定 |
| --- | --- | --- | --- | --- | --- |
| 1 | extrude cut 合法：Ø8 通孔穿 40×30×10 板 | `25b00a194e174675943f8de9c818b400` | removed = 502.6548245743669 | **502.654824574367** | ✅ |
| 2 | extrude cut 完全在板外（圆心 (100,100) R5） | `5520e320a06845a59e7e6338f693e976` | 硬失败 | `"Extrude cut removes no material; check the sketch position, direction and depth against existing geometry"` | ✅ |
| 3 | extrude cut **部分重叠**（圆心 (38,15) R5，跨越板右缘 x=40） | `a08d9aad6d334dd797ff69d1fc85d7e8` | removed = 587.229807114713 | **587.2298055236897**（相对误差 2.7e-9） | ✅ 无假阳性 |
| 4 | revolve cut 合法：R12–R14 环切 R10–R20 管 | `363e78b86c3b4a1c8f17e0007e1f875b` | removed = 4900.884539600077 | **4900.8845396000725**（相对误差 9e-16） | ✅ |
| 5 | revolve cut 完全在实体外（R30–R32 环，管外径 R20） | `874c1999c96146d1ae21b9c6acf54007` | 硬失败 | `"Revolve cut removes no material; check the sketch position, direction and depth against existing geometry"` | ✅ |
| 6 | hole 位置在实体外（BUG-022 姊妹守卫，offset2=100 → x=100） | `e5701f784e1549d4902c8708bb6cda84` | 硬失败 | `"Hole removes no material; check reference offsets, placement, flip and overlap with existing holes"` | ✅ |

### 1.2 失败路径的三项硬指标全部满足

以用例 2（`5520e320…`）为例：

| 指标 | 要求 | 实测 |
| --- | --- | --- |
| 可识别错误 | 明确失败并说明原因 | ✅ `message` 即上表文案；`failed_operation_index=1`、`failed_stage="execute_extrude"` |
| 回滚 | 回到已保存检查点 | ✅ `rollback_succeeded=true`、`inspection_source="rollback_verified"` |
| revision 不递增 | 保持 1 | ✅ 磁盘 `models/1825bf70…/model.json` → `revision=1` |
| 无效特征不落盘 | 无 `CUT_OUT` 特征 | ✅ 特征树止于 `CUT_OK_F`(id 85)；`output/` 仅有 `.prt.1`/`.prt.2`，**无 `.prt.3`** |
| 体积不变 | 11497.345175425633 | ✅ `volume_mm3=11497.345175425633`（逐位相同） |

用例 5（revolve）与用例 6（hole）同样满足：`rollback_succeeded=true`、`revision` 保持、无新特征、体积逐位不变。

### 1.3 回滚后模型仍可继续使用

用例 2 失败后，我用 `expected_revision=1` 继续提交用例 3 并成功，revision 正确推进到 2，`.prt.3` 落盘，`saved_file_reloaded_and_verified=true`。**失败不会把模型打成不可用状态**，这一点对长流程很重要。

### 1.4 判定阈值合理

`native/generic.cpp:983-988`（及 revolve 的同源实现）：

```cpp
double removed = before_volume - volume();
log("CUT_MATERIAL_REMOVED_MM3=%.12f\n", removed);
if (removed <= std::max(1e-9, fabs(before_volume) * 1e-12))
    throw std::runtime_error("... cut removes no material; check the sketch position, "
                             "direction and depth ...");
```

阈值 `max(1e-9, |before_volume|×1e-12)` 量级极小，等价于"完全未去料"，不会误伤微量切除。用例 3 的 587.23 mm³ 与用例 4 的 4900.88 mm³ 均远在阈值之上，正常放行。

### 1.5 边界行为记录（供作者参考，非缺陷）

1. `add` / `surface` 模式确实未返回 `material_removed_mm3`（与发行说明"add/surface 原行为保持"一致），实测 Job A 的 `solid`（add）op 结果仅含 `{label, op, succeeded}`。
2. 守卫触发时作业级 `toolkit_code` 报 `-1`，而 `disconnect_code=0`、通道本身健康。属于异常路径的汇总码，建议可与"Toolkit 真实故障"区分。
3. 新建零件上发生失败时（如 §3 蝴蝶结），`inspection=null`、`inspection_source="unavailable"`、`rollback_succeeded=false`，并残留一个 `status="failed"`、`revision=0` 的模型登记与 `.prt.1`。对新件而言"无检查点可回滚"是事实，但 `rollback_succeeded: false` 易被误读为"回滚失败"，建议对新件置 `null` 或 `not_applicable`。

---

## 2. ❌ P1（核心问题）：草图弧无 dir 参数且恒 CCW —— 仍未修

这是我在 0.3.0 / 0.3.3 两轮都报过的 P1，0.3.5 **原样未动**。

### 2.1 静态证据

**(a) Schema 无 `dir` 字段。** `src/creo_mechdog/schema.py` 的 `Arc(Circle)`（以及 MCP 侧实际下发的 `$defs.Arc`）字段为且仅为：

```
type / name / center / radius / construction / start_angle / end_angle
required = ["type","name","center","radius","start_angle","end_angle"]
additionalProperties = false
```

→ 无法表达"这段弧是顺时针画的"。

**(b) 原生侧恒强制 CCW。** `native/generic.cpp:764-765`：

```cpp
a.start_angle = fmod(a.start_angle + turn, turn);
a.end_angle   = fmod(a.end_angle   + turn, turn);
if (fabs(a.start_angle) < 1e-12) a.start_angle = 0;
if (fabs(a.end_angle)   < 1e-12) a.end_angle   = 0;
if (a.end_angle <= a.start_angle)
    a.end_angle += turn;          // ← 恒把 end 抬到 start 之后，即恒 CCW
```

无任何 `>180°` 扫过角检查、无告警。`native/generic.cpp:1445-1461` 存在第二处同源代码，同样未改。

### 2.2 实机对照实验（同图元，仅角度书写顺序不同）

草图：圆心 (0,0) R10 的整圆参数化弧 + 弦 (10,0)→(0,10)，闭合成区域，extrude depth 5。

| 模型 | 弧书写 | 体积 (mm³) | bbox | status | warning/error |
| --- | --- | --- | --- | --- | --- |
| `rt_arc_ccw`（`6489937ec64e4400885709763df5076a`） | `start=0°, end=90°` | **142.69908169840258** | [0,10]²×[0,5] | succeeded | 无 |
| `rt_arc_cw`（`87c5f41e2e354690aadb790064e74803`） | `start=90°, end=0°` | **1428.0972451017306** | **[-10,10]²×[0,5]** | succeeded | 无 |

- 理论值：劣弓形面积 `πR²/4 − R²/2 = 28.5398163397`，×5 = 142.6990816987 ✓（第一个模型逐位吻合）
- 优弓形面积 `πR² − 28.5398163397 = 285.6194490204`，×5 = 1428.097245102 ✓（第二个模型吻合）
- **体积相差 10.007 倍，两次都是 `success: true`、零 warning、零 error。**
- 与 0.3.3 轮实测值（142.699081698 / 1428.097245102）**完全一致**，说明行为无任何变化。

### 2.3 为什么这是最需要优先处理的一条

新加的 BUG-054 守卫按"去料量是否为 0"判定，而错误弧向产出的是一个**体积非零、形状错误**的实体——守卫完全放行。也就是说：

> 0.3.5 修好了"切了个寂寞"（零去料），但"切错了地方/切成了另一块"（弧向错误）依旧 100% 静默。

对逆向重建类任务（逐特征比对体积/面积/惯性），这是唯一能穿透全部数值验收的缺陷形态。

### 2.4 建议

1. **`Arc` 增加 `dir` 字段**（`+1` = CCW / `-1` = CW，默认 `+1` 保持兼容），原生侧按 `dir` 决定是否 `end_angle += turn`。
2. **至少加一条告警**：当归一化后扫过角 `> 180°` 时，在 job 结果里放 `warnings`（例如 `"arc 'a1' sweeps 270°; verify start/end order"`）。这一条成本最低、收益最直接。
3. 发行说明已写明"合法大弧…不因本次实体切除验收自动扩大支持"，我尊重这个范围决定；但请把"大弧静默"明确登记为一个待办条目，而不是让它继续藏在 `success:true` 里。

---

## 3. ❌ P3：自交轮廓仍只报原始 Toolkit 错误

实机：闭合 polyline `(0,0)→(20,0)→(0,20)→(20,20)`（经典蝴蝶结/8 字形），job `fbd7669e517b4ffc950c271ba6dc9056`。

| 观测项 | 值 |
| --- | --- |
| status | `failed` ✅（不会静默接受，这点是好的） |
| message | `"Toolkit call ProFeatureWithoptionsCreate failed with code -1 during execute_extrude"` |
| `failed_toolkit_call` | `"ProFeatureWithoptionsCreate"` |
| `toolkit_code` | `-1`（即 `PRO_TK_GENERAL_ERROR`） |
| `errors` 数组 | **不存在** |
| `inspection` | `null`，`inspection_source="unavailable"` |
| 残留 | 模型登记 `status="failed"`、`revision=0`，`rt_bowtie.prt.1` 落盘 |

**问题**：调用方拿到的是一条与业务无关的原始 Toolkit 错误码，必须自己猜"是不是轮廓自交了"。建议在提交原生创建前，对 polyline/arc 集合做一次**自交预检**（O(n²) 足够，草图实体数上限 500），命中时直接返回 `errors: [{"code":"self_intersecting_profile","entity":"bow","at":[10,10]}]` 之类结构化诊断。

---

## 4. ❌ P4：组件 model_name 仍是 job-id 派生名

`native/advanced.cpp:82` 与 0.3.3/0.3.4 **逐字相同**：

```cpp
ProMdlName copy_name;
std::wstring token = std::filesystem::path(generic_job).filename().wstring();
swprintf_s(copy_name, L"c_%s_%u", token.substr(0,16).c_str(), (unsigned)operation_results.size());
ProMdlnameCopy(child, copy_name, &copy);
```

0.3.5 实读 `creo_inspect_model(section="components")`（pump_asm，18 实例）返回的 `model_name` 仍是 `C_C37013891D824FC9_0`、`C_6612F49ABA9B460D_0` 这类形式。用户 label 只写进组件 feature 名，而 `assembly_inspection` 只报 `ProMdlNameGet(child)`，**label 在组件清单里丢失**。

建议：组件副本名直接采用用户 label（或 `label_<n>`），或在 `assembly_inspection` 的每条记录里同时输出 `label`。

---

## 5. ❌ P5：旋转仍只接受 XYZ 欧拉角，不支持矩阵直填

`native/advanced.cpp:62`：

```cpp
V angles = vec(op["rotation"]);
for (auto& a : angles) a *= acos(-1.0)/180;
double cx=cos(angles[0]), sx=sin(angles[0]), cy=cos(angles[1]), sy=sin(angles[1]), cz=cos(angles[2]), sz=sin(angles[2]);
double R[3][3] = {{cz*cy, cz*sy*sx-sz*cx, cz*sy*cx+sz*sx},
                  {sz*cy, sz*sy*sx+cz*cx, sz*sy*cx-cz*sx},
                  {-sy,   cy*sx,            cy*cx}};
memset(matrix, 0, sizeof(ProMatrix));
for (int i=0;i<3;i++) for (int j=0;j<3;j++) matrix[i][j] = R[j][i];
for (int j=0;j<3;j++) matrix[3][j] = op["translation"][j];
matrix[3][3] = 1;
```

- Schema 侧 `rotation` 是 `list[float]`，`minItems=maxItems=3` → **无法传矩阵**。
- 这段代码顺带再次确认了两件我已写入验收口径的事实：
  - **ProMatrix 是行向量约定**：`v_world = v_local · M`，平移在**最后一行**（`matrix[3][j]`），不是最后一列；
  - **`rotation=[0,90,0]` 存储结果是 Ry(−90°)**，不是 Ry(+90°)（对应 BUG-045，仍未修）。
- 本任务 18 个实例中 **13 个 `|ry|=90°` 正处万向锁**，只能约定"锁点 `rz=0` + 9 位小数欧拉角"绕行。

建议：`rotation` 增加接受 3×3 / 4×4 数组的分支；或在 `assemble_component` 结果里回显实际存入的 4×4 矩阵，便于调用方核对。

---

## 6. ❌ P6：hole 仍无沉孔 / 锥孔

`src/creo_mechdog/schema.py` 的 `HoleOp` 字段为且仅为：

```
op / label / placement / reference1 / reference2 / offset1 / offset2 / diameter / depth / flip
```

原生侧 `native/generic.cpp:1104-1125` 的 `PRO_E_HLE_COM` 只设置 `PRO_E_DIAMETER` 与 `PRO_E_HOLE_STD_DEPTH`，全库无 counterbore/countersink 相关标识符。沉孔/锥孔只能靠"孔 + 回转切除"两步手工拼。

建议：`HoleOp` 增加 `counterbore: {diameter, depth}` 与 `countersink: {diameter, angle}`（均可选，缺省保持现行为）。

---

## 7. ❌ P7：revolve 轴省略时静默回退且不回报实际轴

`src/creo_mechdog/schema.py:370-379`：`RevolveOp.axis: dict | None = None`（可选）。
`native/generic.cpp`（revolve 分支）：`op.contains("axis") ? PRO_REV_AXIS_EXT_REF : PRO_REV_AXIS_INT_REF`。

实机证据（Job D，`363e78b8…`）：我**故意省略 `axis`**，靠草图内 centerline 驱动，几何结果完全正确（管体 bbox [-20,20]²×[0,30]、圆柱面 R10/R20、切除面 R12/R14 全部符合预期）——功能是好的。但**结果里没有任何字段说明实际用了哪根轴**：`tube_f` 别名仅含 `{"feature_id": 52, "op": "revolve"}`，sketch 别名只报 `normal/u_axis/v_axis/section_normal_sign`。

对含多根 centerline 或多 datum axis 的复杂草图，"静默选了一根"意味着选错时无法从结果侧发现。建议在 revolve 结果里回显解析到的轴（id / label / 起点终点方向）。

---

## 8. 已修项闭环

| 条目 | 状态 | 证据 |
| --- | --- | --- |
| BUG-013 `list_models` compact 分页 | ✅ 闭环 | 3 页翻完，11 零件 + `pump_asm` 全部定位，`model_id`/`revision`/`volume_mm3` 与审计记录逐位一致 |
| BUG-022 hole 零去料守卫 | ✅ 闭环（本轮复测） | §1 用例 6，实机硬失败 + 回滚 |
| BUG-054 / DEV-033 切除守卫 | ✅ **本轮新修并实测** | §1 六用例 |
| BUG-055 `expected_pending_job_id` 契约 | ⬜ 本轮未涉及（无 pending 场景） | — |
| BUG-056 通道 ~37–41s 静默失效 | ⚠️ 本轮未复现 | 8 job / 约 8 分钟连续建模，末次 `creo_session_status` 仍 `connected=true`、`toolkit_code=0`、`state="ready"` |

---

## 9. 对既有交付成果的影响声明

本轮全部测试均使用**新建诊断零件**（`rt_cut_guard_a/b`、`rt_arc_ccw/cw`、`rt_bowtie`），未触碰「简易单级齿轮泵」交付物：

- 11 个零件模型：状态与体积未变（#16 轮已逐位核对）
- `pump_asm`（`11fe34b528304b6dab82d6915156c2f0`）：`revision=7`、`status=ready`，**未变**
- 18 实例逐组件变换：0.3.3 轮结论为 18/18 EXACT（旋转最大偏差 4.882e-08、平移 0.0、正交性 2.2e-16、体积闭合 5.821e-11）；本轮抽样 3 实例与 0.3.3 读回值逐位比对**无漂移**
- 未终止 Creo、未清除任何 unknown 保护、未修改作业/模型登记的历史内容

---

## 10. 需要作者回复的问题

1. **§2 P1**：`Arc.dir` 是否排期？若短期不加字段，能否先加"扫过角 > 180° 时告警"？这是目前唯一静默产出错误几何的路径，且能穿透全部数值验收。
2. **§3 P3**：是否愿意在提交原生创建前做自交预检并返回结构化 `errors`？
3. **§4 P4**：组件副本名能否采用用户 label（或在组件清单里输出 label）？
4. **§5 P5**：`rotation` 能否接受矩阵，或至少回显实际存入的 4×4？
5. **§6 P6**：hole 的 counterbore/countersink 是否排期？
6. **§7 P7**：revolve 结果能否回显实际使用的轴？
7. **§1.5**：新件失败时 `rollback_succeeded=false` 易误读，是否改为 `null`/`not_applicable`？
8. 需要材料我随时可提供：全部 8 个 job 的 `request.json`/`job.json`、`native_log_tail`、5 个诊断零件的 `model.json` 与 `.prt` 文件、本机 `config.json`。

---

## 11. 本轮实机作业清单（可复查）

| job_id | 模型 | 操作 | 结果 |
| --- | --- | --- | --- |
| `25b00a194e174675943f8de9c818b400` | rt_cut_guard_a (1825bf70…) | 建板 + Ø8 合法通孔 | succeeded, rev 1 |
| `5520e320a06845a59e7e6338f693e976` | rt_cut_guard_a | 板外 Ø10 通切 | failed（守卫触发）+ rollback |
| `a08d9aad6d334dd797ff69d1fc85d7e8` | rt_cut_guard_a | 部分重叠 Ø10 通切 | succeeded, rev 2 |
| `363e78b86c3b4a1c8f17e0007e1f875b` | rt_cut_guard_b (7cd81f71…) | 建管 + R12–R14 合法回转切 | succeeded, rev 1 |
| `874c1999c96146d1ae21b9c6acf54007` | rt_cut_guard_b | R30–R32 管外回转切 | failed（守卫触发）+ rollback |
| `e5701f784e1549d4902c8708bb6cda84` | rt_cut_guard_a | 实体外 Ø6 孔 | failed（BUG-022 守卫）+ rollback |
| `21bb0ac32788486c8c8ec30a1432578f` | rt_arc_ccw (6489937e…) | 弧 0°→90° 劣弓形 | succeeded, 142.69908169840258 mm³ |
| `7ecebbb17b11408197a69b712ed63163` | rt_arc_cw (87c5f41e…) | 弧 90°→0° 优弓形 | succeeded, 1428.0972451017306 mm³ |
| `fbd7669e517b4ffc950c271ba6dc9056` | rt_bowtie (17db7e80…) | 蝴蝶结自交轮廓 | failed（原始 Toolkit -1） |
