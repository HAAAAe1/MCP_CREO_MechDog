# 问题反馈：MCP_CREO_MechDog 0.3.7 在 Creo 13.4.1.0 下的核心问题

> 反馈日期：2026-10-18
> 使用场景：通过 AI 客户端（WorkBuddy）调用 MCP 工具在 CREO 中自动建模"直径10mm球体"
> 作者参考目的：便于定位并优化。文中所有 job_id / model_id 均可在我机器上的日志中复查。

## 环境信息

| 项目 | 值 |
|---|---|
| OS | Windows（win32，x64） |
| CREO 版本 | **Creo Parametric 13.4.1.0**（release_numeric = 45），安装于 D:\PTC\CREO13 |
| MCP 版本 | MCP_CREO_MechDog **0.3.7**（stdio） |
| 连接状态 | `creo_check_environment` 全部通过，`ready_to_build: true`，Toolkit 连接正常 |
| 许可 | 实际建模测试通过（草图、放样、保存重载均成功），仅 revolve 失败 |

---

## 问题 1（核心）：`creo_revolve` 在 Creo 13 下始终创建失败

**现象**：所有 revolve 尝试均在 `ProFeatureWithoptionsCreate` 处返回 **-1**，与轮廓画法无关。工具宣称支持到 Creo 9/10/12，**疑似 Creo 13 的旋转特征元素树不兼容**。

**复现步骤（多种轮廓均复现）**：

尝试 A —— 圆弧+直线+中心线（autodim 尺寸策略）：
1. `creo_new_part`（成功，revision 1）
2. `creo_create_sketch`：XY 平面，arc(center=[0,0], r=10, 0°→180°) + line[-10,0]→[10,0] + centerline[0,-15]→[0,15]，dimensioning=`autodim`（**草图创建成功**，约束 8 条、半径尺寸 d=10 正确）
3. `creo_revolve(sketch="sphere_profile", angle=360, mode="add")` → **失败**
   - 错误：`Toolkit call ProFeatureWithoptionsCreate failed with code -1 during execute_revolve`
   - job_id: `5f30c76ae9284b8da0a8be6f9f55c240`（模型 sphere_r10）/ `2dea38904e644da7819bda098a424ab6`

尝试 B —— 官方示例同款（examples/turned_part.json 的画法：closed polyline + centerline，XZ 平面）：
1. `creo_execute_plan`：31 点闭合折线逼近半圆（r=5）+ 竖直 centerline，dimensioning=`autodim`（**草图成功**）
2. `op:"revolve", sketch:"sphere_profile2", angle:360` → **同样 `ProFeatureWithoptionsCreate = -1`**
   - job_id: `efb710634ba14f0281d0ac7d9090cbed`（模型 prt001）

失败后 `rollback_succeeded: true`，模型可继续操作，仅旋转不可用。

**对照证据**：同一会话中，草图创建、放样（seed 复用 Blend）、保存重载验证均成功，说明 Toolkit 许可与通道正常，问题局限于 revolve 元素树构建/创建环节。native.log 中元素树构建各步（ProElementAlloc/IntegerSet/DoubleSet）均返回 0，直到 `ProFeatureWithoptionsCreate=-1`。

**建议**：在 Creo 13 SDK 下用 `creo_create_feature_tree`/`creo_dump_feature_tree` 对照旋转特征的元素树差异（Creo 13 可能新增/修改了 PRO_E_STD_SECTION 或旋转轴相关元素要求），或补一台 Creo 13 实机加入验收矩阵。

**附带说明**：sketch 引用方式上，`sketch` 参数传标签字符串有效；传整数 feature_id 会报 `Unknown feature label: 40`（job `2dea38904e644da7819bda098a424ab6`）。与 `creo_loft.sections` 的"标签/整数ID均接受"行为不一致，建议统一或在校验信息中说明。

---

## 问题 2（核心）：无法接管/操作用户已在 CREO 中打开的模型

**现象**：服务端所有权保护导致**只能修改本服务创建登记的模型**，对用户手动打开的零件（如本例中的 `001.prt`，会话当前模型）没有任何操作入口。文档已声明此边界，但该限制在实际使用中是最大痛点：用户经常希望 AI 直接在自己打开的文件里继续画。

**现状**：
- `creo_session_status` 能看到当前模型（显示为乱码 "▩0010001"，见问题 4），但所有建模工具均要求 registry 中的 model_id；
- `creo_reconcile_model` 明确拒绝 "Unsupported/unproven ownership"。

**建议（需求请求）**：提供"接管当前会话模型"的显式入口（例如 `creo_adopt_current_model`）：用 `ProMdlCurrentGet` 取当前模型，做一次性快照登记（记录基线 revision + 校验和），之后按现有所有权/回滚机制管理。人工修改后已有 `creo_refresh_model` 思路，可复用。

---

## 问题 3：草图三种尺寸策略中两种不可用/受限

- **`auto` + 约束（重合）**：对圆弧端点与直线端点加 `coincident` 约束时报错
  `ProSectionEntityGetSelected(...) failed with code -2 during execute_sketch`
  （job `7ee24b858b9f4ee588cc0981a5a31fb1`）。疑似 intent manager 开启后按名字解析图元引用失败。
- **`coordinates`**：完整坐标标注后求解器**移动了几何**，被防偏移守卫拒绝：
  `Coordinate dimensioning changed the supplied geometry; maximum deviation mm=14.5`（31 点折线时为 9.75）
  （job `5334df81e2bc4e91bcbf75f2c279db08` 等）。
- **`autodim` 正常**（本会话所有成功草图均用 autodim）。

**建议**：`auto` 模式下圆弧端点类约束的实体名解析需要修复；`coordinates` 模式对多顶点轮廓（折线展开后顶点多、约束多）容易过约束/漂移，建议对展开 polyline 的顶点采用独立基准标注而非两两坐标尺寸。

---

## 问题 4（次要）：模型命名校验过严 + 会话模型名乱码

1. `creo_new_part(model_name="001")`、`"PRT001"` 均被拒（`Invalid model_name`），实测仅纯小写开头可用（`prt001` 成功）。而 CREO 本体允许数字开头的模型名（用户实际打开了 `001.prt`）。建议放宽或在错误信息中写明命名规则。
2. `creo_session_status.current_model` 返回 `▩0010001`，存在编码/显示问题，建议修正编码后输出可读模型名。

---

## 问题 5（次要）：直接混合（Blend）依赖手工注册回调 DLL

`creo_loft`/直接混合要求先在 CREO「辅助应用程序」中**手动**注册并启动 blend callback DLL（`BLEND_CALLBACK_SETUP_REQUIRED`），注册状态 `no_runtime_identity_record`，无法自动化完成。种子复用路径（`creo_new_loft_part`）不受影响。
**建议**：提供脚本化注册/自动启动（如写入 config.pro 的 protk 启动项并验证），或在文档/错误信息中给出更醒目的一次性设置指引。

---

## 已验证可用的替代路径（供其他用户参考）

在 Creo 13 下用 **种子复用放样** 成功生成了球体：
- `creo_new_loft_part`：5 个 XY 圆截面（offset=-4/-2/0/2/4，r=3/4.5826/5/4.5826/3，半径尺寸驱动，`auto` 标注）+ smooth 插值
- 结果：`ball001.prt` 实体，体积 494.5 mm³（理想球 523.6，偏差约 5.5%），保存重载验证通过
- job_id: `916f5d8c2b2a47249f6029cf1913123a`

## 优先级建议

1. **问题 1（revolve on Creo 13）** —— 直接建模失败，影响最大
2. **问题 2（接管当前会话模型）** —— 用户最常见诉求，建议作为新特性
3. 问题 3（草图约束解析）
4. 问题 4/5（命名、乱码、回调注册体验）
