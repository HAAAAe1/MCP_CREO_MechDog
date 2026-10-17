# BUG-055 WorkBuddy 黑盒验收提示词（待执行）

按项目 WorkBuddy 约定执行：仅通过已连接的 MCP 工具（本机为 `MCP_CREO_MechDog_dev`，指向 E 盘主 worktree）对最终用户可见行为做黑盒验收；不查看/分析源码，不执行本地 Python 脚本、单元测试或开发检查，不读取本机配置、仓库或 Git 状态。环境、会话、可见工具与服务版本用 MCP 公开接口确认；接口未提供的构建身份记"无法确认"。开发侧协议与实机证据见 [BUG-055-fix-2026-10-17.md](BUG-055-fix-2026-10-17.md)，两者分别记录、互不替代。

前置条件：Creo 会话可连接（`creo_session_status` connected=true）。测试全部使用本次新建的自有模型，不要触碰历史失败模型；也不要复用任何之前出现过的模型名（同名残留会话模型会让 abandon_new 被 owned 保护正确拒绝）。

---

## 提示词

你在做 MCP Creo 服务恢复工具 `creo_reconcile_model` 的黑盒验收。只调用已连接的 MCP 工具完成下列场景，逐项记录：工具名与完整输入（尤其是 `expected_pending_job_id` 的实际取值——记录你发送的是 JSON null、省略字段还是字符串）、job_id/model_id、isError 与完整 message、inspect 返回的 revision/pending_job/evidence_token/actions、恢复作业终态、恢复后模型 status/revision。已接受的作业只轮询 `creo_get_job`（detail=compact）到终态，不重复提交；busy 按提示处理；unknown_outcome 停止并报告。

### 0. 环境与契约确认

1. `creo_session_status`：记录 connected、toolkit_code、release。
2. 列出可见工具确认 `creo_reconcile_model` 存在；记录服务版本与工具总数。若客户端能查看工具 schema，记录 `expected_pending_job_id` 的类型定义（预期允许 string 或 null，默认 null）；不能查看则记"无法确认"。

### 1. 制造待恢复模型（两次，模型名互不相同且含随机后缀）

对每个新模型：`creo_execute_plan`（新模型）提交三步——XY 矩形草图 min=[0,0] max=[60,40]、`extrude` add depth=10、`set_dimensions` values=[{id: 999999, value: 5}]。预期：作业 failed（message 指向 set_dimensions 的 Toolkit 失败），模型 status=failed、revision=0、无 part 基线。轮询到终态后记录 job_id/model_id。两个模型分别记为 M1、M2。

### 2. 场景 A：显式 null 的完整恢复闭环（M1，BUG-055 核心正例）

1. `creo_reconcile_model`（mode=inspect，仅 model_id）：记录 pending_job（预期 null）、abandon_new available=true、evidence_token。
2. `creo_reconcile_model` mode=apply，action=abandon_new，expected_revision=inspect 返回的 revision，`expected_pending_job_id` 必须发送 JSON null（不是字符串 "null"、不是空串 ""），evidence_token=本次 inspect 的 token，idempotency_key 自定 8–80 位唯一值。预期：isError=false，返回独立 recovery job_id；message 提示轮询该作业、原计划不重放。
3. 仅轮询该 recovery job：预期 succeeded，revision=0。再次 inspect M1：status=abandoned。原始失败作业 job.json 仍可 `creo_get_job` 查询且状态仍为 failed。
4. 用完全相同的参数重复一次 apply：预期返回同一 job_id（幂等），不产生新作业。

若你的客户端无法发送 JSON null，如实记录"客户端无法发送 null"并改用省略该字段重试步骤 2–3；两种形状都不可用时记录客户端阻断，不得改发空串冒充通过。

### 3. 场景 B：空串与字面值防护（M2）

1. inspect M2 取新 token。
2. apply 发送 `expected_pending_job_id=""`（空字符串），其余同场景 A。预期：isError=true，message 含 "expected_pending_job_id must be the pending job id"，且不含 "Stale"；模型与任何作业状态不变。
3. 再发送字符串 `"null"`（字面值）重试。记录实际行为与 message（若被接受为 null 属预期兼容；若拒绝为输入错误也如实记录）。
4. 最后用 JSON null（或省略字段）完成 M2 的 abandon_new 并轮询到 succeeded，模型 abandoned。

### 4. 报告要求

输出表格式记录（场景 | 实际发送的 expected_pending_job_id 形状 | isError | job_id/model_id | 终态 | message 摘要 | 模型 status/revision 变化 | 幂等重放结果）。与预期不符的结果原样记录，不重试掩盖；接口不可观察的项目（文件哈希、内部日志、部署指纹）记"未验证/无法确认"。不要求测试未列出的工具或动作。
