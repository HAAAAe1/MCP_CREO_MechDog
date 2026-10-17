# BUG-054 WorkBuddy 黑盒验收提示词（待执行）

按项目 WorkBuddy 约定执行：仅通过已连接的 MCP 工具对最终用户可见行为做黑盒验收，不查看/分析源码，不执行本地 Python 脚本、单元测试或开发检查，不读取本机配置或仓库状态。环境、会话、可见工具与服务版本用 MCP 公开接口确认；接口未提供的构建身份记"无法确认"。开发侧实机证据见 [BUG-054-cut-material-2026-10-17.md](BUG-054-cut-material-2026-10-17.md)，两者分别记录、互不替代。

---

## 提示词

你在做 MCP Creo 服务的黑盒验收。只调用已连接的 MCP 工具完成下列场景，逐项记录：工具名与完整输入、job_id/model_id、终态 status 与 message、操作前后 volume_mm3、revision、保存重载标志、操作明细中的 material_removed_mm3（如有）。所有修改提交后只轮询 `creo_get_job`（detail=compact）直到终态，不重复提交；若返回 busy 按提示处理；若出现 unknown_outcome 停止新写入并报告。每个场景使用全新隔离模型（`creo_new_part`），不要复用历史 model_id。

### 0. 环境确认

1. `creo_session_status`：记录 connected、toolkit_code、release。
2. 列出可见工具，确认 `creo_extrude`、`creo_revolve`、`creo_execute_plan`、`creo_inspect_model` 存在；记录服务版本（接口未提供则记"无法确认"）。

### 1. 基准模型（每场景重复建立）

`creo_new_part`（模型名自定，互不相同）后，用 `creo_execute_plan` 提交：XY 平面矩形草图 min=[-30,-20] max=[30,20]，`extrude` add depth=10 positive；再提交 XY 平面圆草图 center=[-10,0] radius=4，`extrude` cut depth_type=through_all positive。终态应为 succeeded，最终体积 ≈23497.34（24000−160π），记录 revision。

### 2. 场景 A：有效切除（正例）

在基准模型上追加：XY 圆草图 center=[15,0] radius=2，`extrude` cut depth=10 positive。预期：succeeded；`creo_inspect_model` 体积 ≈23371.68（24000−200π）；revision 恰好 +1；作业明细最后一条 extrude 操作含 material_removed_mm3 ≈125.66（40π）；保存重载 true。

### 3. 场景 B：板外切除（BUG-054 核心负例）

新建基准模型，单次 `creo_execute_plan` 同时提交：XY 圆草图 center=[100,100] radius=5（label 如 sk_out）+ `extrude` cut depth=10 positive（label 如 cut_out）。预期：作业 failed，message 含 "removes no material"；`creo_inspect_model` 体积与提交前一致、revision 不变；随后在同一模型追加场景 A 的有效切除应成功（模型仍可编辑）。

### 4. 场景 C：已去除区域重复切除

新建基准模型（含 (−10,0) Ø8 孔），提交 XY 圆草图 center=[-10,0] radius=2 + cut depth=10 positive。预期：failed，message 含 "removes no material"；体积与 revision 不变。

### 5. 场景 D：revolve 对照

两个独立基准模型：
1. XZ 平面草图：centerline (20,0)→(25,0) + 矩形 min=[20,2] max=[25,4]，`revolve` cut angle=360 positive。预期：succeeded；material_removed_mm3 ≈94.25（轴线在板底面，仅上半环与板相交，30π）；体积 ≈23905.75。
2. XZ 平面草图：centerline (100,0)→(105,0) + 矩形 min=[100,2] max=[105,4]，`revolve` cut 360。预期：failed，message 含 "removes no material"。

### 6. 报告要求

输出表格式记录（场景 | 输入摘要 | job_id | model_id | 终态 | message 摘要 | 前后体积 | revision 变化 | material_removed_mm3 | 保存重载）。任何与上述预期不符的结果原样记录，不要重试掩盖；接口不可观察的项目（如文件哈希、内部日志）记"未验证/无法确认"。不要求测试未列出的工具或分支。
