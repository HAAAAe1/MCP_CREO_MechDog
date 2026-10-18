# DEV-036 WorkBuddy 黑盒验收提示词（待执行）

按项目 WorkBuddy 约定执行：仅通过已连接的 MCP 工具（本机为 `MCP_CREO_MechDog_dev`，指向 E 盘主 worktree）对最终用户可见行为做黑盒验收；不查看/分析源码，不执行本地 Python 脚本、单元测试或开发检查，不读取本机配置、仓库或 Git 状态。环境、会话与可见工具用 MCP 公开接口确认；接口未提供的构建身份记「无法确认」。开发侧证据见 [BUG-056 核实记录](BUG-056-DEV-036-investigation-2026-10-17.md)，两者分别记录、互不替代。

前置条件：MCP 服务已重启加载最新代码；Creo 会话可连接（`creo_session_status` connected=true）。测试全部使用本次新建的自有模型（模型名含随机后缀，不复用任何历史名称，不触碰历史失败模型）。

---

## 提示词

你在做 MCP Creo 服务（`MCP_CREO_MechDog_dev`）的黑盒验收，共五个部分。逐项记录：工具名与完整输入（尤其是可空参数的实际取值——记录你发送的是 JSON null、省略字段、空串 "" 还是字符串 "null"）、job_id/model_id、isError 与完整 message、返回的关键字段、作业终态、模型 status/revision。已接受的作业只轮询 `creo_get_job`（detail=compact）到终态，不重复提交；busy 按提示等待后重试；任何 unknown_outcome 停止并报告，不清保护、不重放。不要调用 `creo_capabilities`（响应可能超出客户端上限；版本与工具总数记「无法确认」即可）。

### 0. 会话状态与新字段验证

调用 `creo_session_status`，记录 connected、connection_state、toolkit_code、release。预期 connected=true。**检查返回中是否存在 `creo_process_snapshot` 字段**：预期 available=true，processes 数组包含 parametric.exe 与 xtop.exe 的 pid、name、created_at、matches=true。若本次返回不含该字段（可能走了启动快照路径），间隔 30 秒重试一次；两次都没有则如实记录「字段未出现」。快照中的 pid 与 created_at 原样记录。

### 1. 稳定性对照（间隔探测）

以约 60 秒间隔连续调用 3 次 `creo_session_status`（共 3 次，覆盖至少 2 分钟），预期每次 connected=true、connection_state=connected、toolkit_code=0。记录每次调用的实际时刻（含 `creo_process_snapshot` 是否在场）。任一次 connected=false：记录完整返回并**停止后续所有部分**，报告为稳定性异常。

### 2. 简单建模闭环（新建→编辑→保存重载）

1. `creo_execute_plan` 新建模型 `wb_dev036_loop_<随机>`（model_type 默认 part），operations：

```json
[
  {"op": "sketch", "label": "base_profile", "plane": "XY",
   "entities": [{"type": "rectangle", "name": "rect", "min": [-25, -15], "max": [25, 15]}]},
  {"op": "extrude", "label": "base_pad", "sketch": "base_profile", "depth": 10}
]
```

   轮询该 job 到终态。预期 succeeded、revision 0→1、result 中 saved_file_reloaded_and_verified=true。
2. `creo_inspect_model`（detail=compact）该模型：记录 revision=1、体积（预期 50×30×10=15000 mm³，记录实际值）。
3. 再 `creo_execute_plan` 编辑同一模型（model_id=上述模型，expected_revision=1），operations：

```json
[
  {"op": "sketch", "label": "hole_profile", "plane": "XY", "offset": 10,
   "entities": [{"type": "circle", "name": "c1", "center": [0, 0], "radius": 4}]},
  {"op": "extrude", "label": "center_hole", "sketch": "hole_profile",
   "mode": "cut", "depth_type": "through_all", "direction": "negative"}
]
```

   轮询到终态。预期 succeeded、revision 1→2、saved_file_reloaded_and_verified=true；再次 inspect 记录体积（预期 15000−π×16×10≈14973.6 mm³，允许小数尾差）。
4. 全程任一次 `creo_session_status` 或作业中出现连接类失败（如 not_found_or_unreadable、worker_exit_code≠0 的连接失败）：停止并完整记录。

### 3. 造错样本与空值协议（稳定通道下的完整终态）

1. 新建模型 `wb_dev036_t07_<随机>`，`creo_execute_plan` 三步：

```json
[
  {"op": "sketch", "label": "base_profile", "plane": "XY",
   "entities": [{"type": "rectangle", "name": "rect", "min": [0, 0], "max": [60, 40]}]},
  {"op": "extrude", "label": "base_pad", "sketch": "base_profile", "depth": 10},
  {"op": "set_dimensions", "values": [{"id": 999999, "value": 5}]}
]
```

   预期作业 failed（message 指向 set_dimensions 的 Toolkit 失败）、模型 status=failed、revision=0、无 part 基线。记录 job_id/model_id。记为 T。
2. `creo_reconcile_model`（mode=inspect，仅 model_id=T）：记录 pending_job、recovery_pending、abandon_new available=true、evidence_token（600 秒有效期，后续步骤尽快连续完成）。
3. **空串防护**：apply（action=abandon_new，expected_revision=inspect 返回的 revision，evidence_token=本次 token，idempotency_key 自定唯一值，`expected_pending_job_id` 发送空字符串 ""）。预期 isError=true，message 含 "expected_pending_job_id must be the pending job id" 且回显 received ''，不含 "Stale"；模型与作业状态不变。
4. **字面 "null" 完整终态**：重新 inspect 取新 token，apply 时 `expected_pending_job_id` 发送字符串 "null"（字面值）。预期：按已发布契约被接受为 null（mcp SDK 预解析兼容），isError=false，返回独立 recovery job_id。轮询该作业到终态：预期 succeeded、revision=0；再次 inspect T：status=abandoned、recovery_pending 清除；原始失败作业仍可 `creo_get_job` 查询且状态仍为 failed。
5. **幂等**：用与步骤 4 完全相同的参数再 apply 一次：预期返回同一 job_id，不产生新作业。
6. 若你的客户端无法发送字符串 "null" 之外还想测 JSON null：显式发送 JSON null，按已知客户端行为可能被降级为空串而收到 received '' 拒绝——如实记录实际形状与 message，改用省略字段完成一次 apply 作为对照终态（预期同样 succeeded）。两种形状都发不出去时记录客户端限制，不伪造。

### 4. 已收尾模型的公开状态确认

`creo_inspect_model`（model_id=`5f2b0bc868c24ad3a6be90c7939937a1`，detail=compact）：预期 status=abandoned、revision=0。仅读取报告，不做任何写操作。

### 5. 报告要求

输出表格式记录：部分 | 场景 | 工具 | 关键输入（含空值形状） | isError | job_id/model_id | 终态 | message 摘要 | 模型 status/revision 变化。汇总回答：① `creo_process_snapshot` 是否出现及其 pid/created_at；② 3 次间隔探测是否全部 connected=true；③ 建模闭环两步的 saved_file_reloaded_and_verified 与体积；④ 字面 "null" 的完整终态是否取得；⑤ 空串拒绝与幂等是否符合预期。与预期不符的结果原样记录，不重试掩盖；接口不可观察的项目（文件哈希、内部日志、部署指纹、构建身份）记「未验证/无法确认」。不要求测试未列出的工具或动作。
