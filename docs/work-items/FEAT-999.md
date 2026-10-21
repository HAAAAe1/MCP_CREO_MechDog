# FEAT-999：真螺旋螺纹与螺旋线圈

类型：功能

优先级：P2

状态：验收中（2026-10-16；实机证据取自在 0.3.2 期本地源码，见"基线与证据边界"）

目标版本：未排期

来源与关联：台账 FEAT-011（螺旋扫掠分支）；BUG 无；原编号 FEAT-032 与上游曲线阵列卡撞号，2026-10-21 合并上游 0.4.5 时按用户指定改为 FEAT-999；分支 `codex/feat-032-helical-sweep`

## 问题或目标

MCP 此前只能沿二维草图轨迹做常截面扫描，做螺纹只能用每圈一个环形切除近似：牙型角、螺距、大径小径可以按标准做准，但没有螺旋升角，不能当真螺旋面用（干涉检查、螺纹测量、STEP 交付都不合格）。

目标：新增原生能力，直接创建**带螺旋升角的真螺旋几何**，覆盖外螺纹/内螺纹的切槽、螺旋凸起（线圈、盘绕结构），左右旋可选，并与解析体积闭环。

## 关键调查结论（决定实现路线）

Creo 有专用的"螺旋扫描"特征。Pro/TOOLKIT 头文件里确实存在 13 个 `PRO_E_HLSWP_*` 元素 id（`ProElemId.h` 第 3972 行起的 `/* Helical Sweep */` 分段），但：

- **没有任何头文件描述这棵树**：`ProSweep.h` 把普通扫描的 element tree 写全了，却没有一句提到螺旋；SDK 里不存在 `ProHlswp.h` 之类的头文件。
- **不存在取值常量**：全 SDK 搜不到任何 `PRO_HLSWP_*` 枚举，即 `PRO_E_HLSWP_HAND_OPT`（旋向）、`PRO_E_HLSWP_SEC_OPT` 等该填什么值是无从得知的。
- `PRO_SWEEP_TYPE` 只有 `MULTI_TRAJ` 与 `UNDEF`，没有螺旋分支；也没有螺旋扫描的特征类型常量。
- 官方示例（`protk_appls`）中唯一命中 helical 的是 `pt_geardesign`，那是**斜齿轮的螺旋角**，走 UDF，与螺旋扫描无关；OTK 文档也只把 `HLSWP` 当作元素名枚举列出，无教程无示例。

结论：`PRO_E_HLSWP_*` 是**元素 id 泄漏**，不是可用接口。据此**不拼这棵树**，改用两个各自有完整文档的特征组合：

1. **方程基准曲线** `PRO_CURVE_TYPE_FROM_EQUATION`（`ProDtmCrv.h` 有完整 element tree：`PRO_E_CRV_FR_EQ_REF_CSYS` / `_CSYS_TYPE` / `_PARAM_MIN` / `_PARAM_MAX` / `PRO_E_CRV_ENTER_EQUATION`），承载螺旋线；
2. **常截面扫描** `PRO_SWEEP`（`ProSweep.h` 已实现），轨迹取上面那条曲线的曲线链。

### 截面标架的关键结论（决定牙型能否成立）

Automatic 标架（`PRO_E_FRM_ORIENT=PRO_FRAME_MIN`）对螺旋轨迹是**无挠率旋转标架（Bishop/RMF）**：截面相对径向的偏转角 = Frenet 挠率 × 弧长。实测（r=2、pitch=1、2 圈）：起始面圆心在轨迹起点 + 精确 (-1,0,0) 偏移，终止面偏移仍为 1.0 但方向变为 (-0.5429, +0.0666, -0.8371)；解析 τ·L = 0.039539×25.212 = 0.99688 rad = 57.11°，Rodrigues 旋转后逐位吻合。**牙型截面用它必然随圈漂移，不能画螺纹。**

正解在 `ProSweep.h` 有明文：`PRO_E_FRM_NORMAL=PRO_FRAME_PIVOT_DIR(1<<9)` + `PRO_E_FRM_PIVOT_DIR` 方向参考（取丝锥轴）+ `PRO_E_FRM_ORIENT=PRO_FRAME_CONSTANT(3)`，即界面里的"垂直于投影"：截面平面恒垂直于螺旋在 ⊥轴 平面上的投影圆 = **过轴平面随螺旋做螺旋运动**，轴剖面即所画牙型（ISO 螺纹定义方式）。实测标架映射：**局部 +u = 径向向外，+v = 轴向向下**，且探针体积与解析值（⊥截面积 = A·cos 螺旋角）闭合到 0.03% 内。

## 范围

包含：

- 新 op `datum_curve_equation`：按方程创建原生基准曲线，柱坐标 / 直角坐标 / 球坐标，可指定参考坐标系，参数区间可调；曲线可单独作为后续扫描轨迹使用。
- 新 op `helical_sweep`：由参数（半径、螺距、长度、起始 z、旋向）自动生成螺旋线方程并创建曲线，再沿其做常截面扫描，支持 `add` / `cut`。
- 对应 MCP 工具 `creo_equation_curve`、`creo_helical_sweep`。
- `generic_sweep` 增加**可选**帧控制（`frame_normal` / `frame_orient` / `frame_user_x` / `frame_pivot_direction` / `frame_z_direction` / `frame_start_x_direction`，支持字符串别名与原生 int），默认值与原行为完全一致，用于控制牙型截面朝向；`creo_sweep` 工具同步透传这些键。

不包含：

- 变螺距、锥螺纹、退刀槽、螺纹收尾；螺纹标准件库（按规格自动查表）；修饰螺纹（`ProThread.h` 的 cosmetic thread，另一条独立路线，未纳入本条目）。
- 装配级螺纹。

## 基线与证据边界

本条目目前的实机证据取自在 **0.3.2 期本地源码**上构建的 worker。该份本地源码相对 0.3.2 主干另含 4 处与本功能无关的本地改动（`#include "constants.inc"`、hole 参数宏守卫、jpeg/pdf 输出目录、`latest_model_file` 兼容 `save_file_iterations no`），本分支**未带入**。

本分支基于 `main`（0.3.3）且**只含本功能改动**，因此受测源码指纹与分支源码不同，不能把已有结论外推为分支源码已验收。合入前必须：

1. 在分支源码上重建 worker（`bridge.py build`）；
2. 按下方验收标准重跑 `tools/test_helical.py` 与 `tools/test_helical_thread.py`；
3. 重点核对 `saved_file_reloaded_and_verified`：上游 `latest_model_file()` 只识别 `<name>.prt.N`，而本机 `save_file_iterations` 为 `no`（Creo 保存为无版本名，`mcp` 输出目录下无任何 `.prt.N`），分支在本机可能报 `Saved native model version not found`。

## 验收标准

| 环境 / 用例 | 命令或操作 | 可判断的预期结果 |
| --- | --- | --- |
| Windows / Python | `.venv\Scripts\python.exe -m py_compile server.py capabilities.py src/creo_mechdog/schema.py`；schema 校验两个新 op | 语法与契约校验通过，`creo_capabilities` 注册 62 个 op、84 个工具 |
| Windows / MSVC + Creo 12 SDK | `.venv\Scripts\python.exe bridge.py build` | `creo_worker.exe` 重新编译并链接通过 |
| 本机 Creo 12.4 / 匹配 SDK | `tools/test_helical.py` | 方程曲线特征创建成功且曲线几何可被扫描引用；螺旋扫描作业成功；扫描件体积与解析螺旋体积一致 |
| 本机 Creo 12.4 / 匹配 SDK | `tools/test_helical_thread.py` | 牙槽由单条 `helical_sweep cut` 切除；体积与螺旋运动数值积分一致；`saved_file_reloaded_and_verified` 为真；STEP 回读确认螺旋面 |

按当前项目规则不要求 Creo 10 独立复测。

## 实现与证据

变更文件：

- `native/helical.cpp`（新增）：`helix_equations`、`generic_equation_curve`、`generic_helical_sweep`。
- `native/generic.cpp`：include `helical.cpp`；`execute_operation` 分发 `datum_curve_equation` 与 `helical_sweep`。
- `native/advanced.cpp`：`generic_sweep` 的帧设置改为读 op 可选键（默认值不变），支持 pivot / constant_z / start_x 方向参考与字符串别名。
- `src/creo_mechdog/schema.py`：`EquationCurveOp`、`HelicalSweepOp`、`SweepFrameOptions`（sweep/helical_sweep 共用帧校验）及其在 op 联合中的注册。
- `capabilities.py`：`REGISTERED_OPERATIONS` 增加两项，`families()` 增加 `equation_curve` / `helical_sweep` 边界说明（含标架 twist 结论与本次真机记录）。
- `server.py`：`creo_equation_curve`、`creo_helical_sweep` 工具（后者带全帧参数）；`creo_sweep` 透传帧控制；`_SOURCE_NAMES` 补 `native/advanced.cpp`、`native/helical.cpp`。
- `docs/BACKLOG.md`：本条目。
- `tools/test_helical.py`、`tools/test_helical_frame.py`、`tools/probe_sweep_frame.py`、`tools/test_helical_thread.py`（新增）：探针、取证与验收脚本。

关键决策：不按 `PRO_E_HLSWP_*` 拼树（理由见上）；改用"方程曲线 + 普通扫描"两个文档化特征的组合；螺纹必须用 `frame_normal="pivot"` + `frame_orient="constant"` 的"垂直于投影"标架（Automatic 标架 twist 会使牙型随圈漂移）。

## 验证记录

以下证据取自在 **本机 0.3.2 期源码 + 本功能**上构建的 worker（Creo 12.4 实机），范围见"基线与证据边界"。

1. **契约**：`py_compile server.py capabilities.py src/creo_mechdog/schema.py` 通过；`creo_capabilities` 注册 62 op / 84 工具；`HelicalSweepOp` 接受 `frame_normal="pivot"` 并拒绝缺 `frame_pivot_direction` / 非 constant `frame_orient` 的组合。
2. **编译**：`bridge.py build` 通过（源码变更后通道自动重建 worker，作业需等待就绪）。
3. **真螺旋几何**（`tools/test_helical.py`，Creo 12.4 实机）：线圈 r=2、pitch=1、长 2、丝径 Ø0.4 体积 3.168252 vs 解析 3.168258；包围盒 x/y=±2.199（预期 ±2.2）、z=[1.80,4.28]（预期 [1.8,4.2]），特征表含 949（`PRO_FEAT_CURVE`）。
4. **标架取证**（`tools/probe_sweep_frame.py` + 元素树 XML + 曲面清单）：Automatic 标架 twist 57.11° 与 Frenet 挠率积分解析值逐位吻合（详见上节）。
5. **pivot 标架标记探针**（`tools/test_helical_frame.py`）：org/pu/nu/pv 四标记体积与解析闭合到 ≤0.03%，+u=径向向外、+v=轴向向下、z 平移精确 ±1。
6. **端到端验收**（`tools/test_helical_thread.py`）：M3.5×0.6×5 六角螺丝，牙槽单条 `helical_sweep cut`（pitch 半径 1.55515 螺旋，轴平面 60° 梯形截面）切除；实测体积 101.3568 vs 螺旋运动数值积分 101.1486（相对误差 0.21%，偏差为牙顶延伸翼在头部下方并集重叠的积分模型误差）；`saved_file_reloaded_and_verified=true`；STEP 回读含 4 个 B_SPLINE_SURFACE（牙槽两侧牙面 + 牙底，与 4 段截面线一一对应）；JPEG 预览确认牙距均匀、螺纹到头。

## 待办

- 在分支源码上重建 worker 并按验收标准复核（含 `saved_file_reloaded_and_verified`）。
- `latest_model_file` 对 `save_file_iterations no` 的兼容、jpeg/pdf 输出目录、hole 参数宏守卫这三处本地改动未纳入本分支，需另登记条目后单独提交。
