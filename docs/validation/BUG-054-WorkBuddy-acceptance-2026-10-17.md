# BUG-054 WorkBuddy 黑盒验收记录

日期：2026-10-17（Asia/Shanghai）。验收方式：WorkBuddy 通过已连接 MCP 工具黑盒执行 [BUG-054-WorkBuddy-test.md](BUG-054-WorkBuddy-test.md) 场景；开发者随后只读核对本地作业记录，两者分别记录、互不替代。受测服务为开发分支 `codex/bug-054-feedback033`（修复提交 `65ea3db`，基线 0.3.4 `7662f7e`）。

## 环境

WorkBuddy 报告：`creo_session_status` connected=true、toolkit_code=0、release_numeric=44（本机 Creo 12.4 唯一会话）；`creo_extrude`/`creo_revolve`/`creo_execute_plan`/`creo_inspect_model` 均可见且实际调用成功；服务版本 0.3.4（creo_check_update，prerelease）。全程无 busy / unknown_outcome，均按"提交→轮询"执行，无重复提交。

## WorkBuddy 场景结果（5/5 符合预期）

| 场景 | job_id | 终态 | 关键结果 |
| --- | --- | --- | --- |
| A 有效切除 (15,0) R2 | `58b4ffd842b4430288d62f696588a099` | succeeded | removed=125.66370614359039（40π）；体积 23497.345→23371.68146928204；revision +1；保存重载 true |
| B 板外切除 (100,100) R5（单计划） | `288aec1024954fc298fbdfa75aa42a99` | failed | message `Extrude cut removes no material…`；failed_stage=execute_extrude、index=1、rollback_succeeded=true；体积不变（rollback_verified）、revision 2→2、sha256 不变 |
| B 后续有效编辑 | `62b514a1c0d8449fa3ddd952803a7e83` | succeeded | 同模型 (15,0) R2 切除成功、removed 125.66、revision 2→3——证明失败后模型仍可编辑，且失败时 revision 确未推进 |
| C 重复切除 (−10,0) R2 | `5aea883b2aa84233b0b687a29950cb08` | failed | 同一契约；体积/revision/sha256 不变 |
| D-1 revolve 正例（XZ 中心线 + 环形截面） | `b0732e4a796b4e948de701bb9d015e73` | succeeded | removed=94.2478797209078（30π，轴在板底面仅上半环相交）；体积 24000→23905.752120279092；重载 true |
| D-2 revolve 负例（板外截面） | `598626c0fe48484bac4453103658b068` | failed | `Revolve cut removes no material…`；体积/revision 不变 |

基准模型各场景独立新建（A/B/C 含 Ø8 孔 23497.34517542563，D 纯板 24000.0），基准 Ø8 孔 removed=502.65482457436883（160π）精确。

## 开发者只读核对

按 BUG-022 惯例，开发者核对 WorkBuddy 所列 11 个作业（5 基准 + 6 场景）的本地 `job.json` / `native_result.json`：终态、message、revision、体积、`material_removed_mm3`、`rollback_succeeded`、保存重载标志**逐项一致**，未重新实施测试，不将核对计为新的 WorkBuddy 调用。

## 提示词基准歧义（如实记录）

交接提示词存在瑕疵：步骤 1 的通用基准含 (−10,0) Ø8 孔，而场景 D 的预期体积 23905.75（=24000−30π）基于纯板推导，两者矛盾。WorkBuddy 正确识别并按纯板建立 D 场景基准，结果与预期一致；其推算的带孔基准对照值 23403.10（=23497.345−94.248）亦正确。后续复用该提示词时应将场景 D 基准明确为纯板。

## 次要观察（未登记新条目）

`creo_execute_plan` 在 `mode=cut` + `depth_type=through_all` 时回显 `depth:1.0`（默认值占位；through_all 模式 depth 不参与建模，实际按通孔执行，几何与去料结果正确）。属参数回显消歧的小改进，不影响力结果；是否登记条目留待后续反馈汇总时决定。

## 未验证/无法确认

内部日志全文（WorkBuddy 仅见 native_log_tail 尾部）、Creo 会话 UI 状态、Toolkit 内部计时与重试预算；文件级 sha256 由接口观察，内部计算过程未验证。验收范围仅限提示词所列场景，未覆盖未列出的工具与分支；环境为本机单一 Creo 12.4 会话，不外推外部 Creo 10/9。

## 结论

WorkBuddy 公开黑盒验收通过。BUG-054 三层证据链闭环：开发侧实机 T01～T08（[BUG-054-cut-material-2026-10-17.md](BUG-054-cut-material-2026-10-17.md)）+ 离线单元回归 + 公开 MCP 黑盒；负例契约（可识别失败信息、体积/revision/sha256 不变、失败后可继续编辑、revolve 30π 语义）在黑盒侧全部复现。
