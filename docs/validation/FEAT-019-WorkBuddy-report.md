# FEAT-019 建模验收报告（MCP_CREO_MechDog_dev 实测）

> 测试时间：2026-10-13 22:31–22:39 (GMT+8)
> 环境：Windows x64 · Creo Parametric 12.4.0.0 (release_numeric=44) · MCP_CREO_MechDog 0.2.5 (stdio)
> 工具来源：MCP_CREO_MechDog_dev（本地开发版）
> 测试模型：`feat019_probe`，model_id `8fa908a662b3407792d314b154362414`
> **总体结论：Toolkit 就绪 + 完整建模链路验收通过 → FEAT-019 可判定为完成**

---

## 0. 前置确认（用户指定项）

| 检查项 | 期望值 | 实测值 | 结果 |
|---|---|---|---|
| `runtime.server_entry` | `E:\Projects\MCP_CREO_MechDog\server.py` | `E:\Projects\MCP_CREO_MechDog\server.py` | ✅ 一致 |
| `runtime.source_changed_since_startup` | `false` | `false` | ✅ 一致 |
| `runtime.python_executable` | — | `E:\Projects\MCP_CREO_MechDog\.venv\Scripts\python.exe` | 参考 |
| `runtime.code_root` | — | `E:\Projects\MCP_CREO_MechDog` | 参考 |
| 工具规模 | — | 81 个（enabled 81，disabled 隐藏） | 参考 |

> 启动指纹（startup fingerprints）记录的 6 个源文件 SHA256 与运行中一致，故 `source_changed_since_startup=false` 成立，即当前运行实例代码未漂移。

---

## 1. 启动 / 连接就绪

| 步骤 | 观察值 | 结果 |
|---|---|---|
| `creo_check_environment` | exe/Toolkit SDK/async 库/pro_comm_msg/mmns 模板/vcvars64 全部存在，`ready_to_build=true` | ✅ |
| 首次 `creo_startup_status(retry=true)` | `state=checking`，Toolkit 忙于既有任务（等待，不重复拉起 Creo） | 轮询中 |
| 二次 `creo_startup_status` | `state=ready`，`connected=true`，`toolkit_code=0`，message=「Toolkit connection verified; modeling is available」 | ✅ |
| `creo_session_status` | `connected=true`，`current_model_code=0`，`model_type=2`(part)，`worker_exit_code=0` | ✅ |

> 说明：`selected_session_configured=false`，但 auto-start 协调器已成功拉起并连上唯一会话（`launched_by_coordinator=true`）。
> 首轮 `state=checking` 是上一轮被中断的启动任务仍在收尾，属正常串行等待，无需人工干预。

---

## 2. 完整建模链路（逐步 expected_revision 链式提交）

| # | 操作 | job_id | revision | 关键结果 | 断言 |
|---|---|---|---|---|---|
| 1 | `creo_new_part` | `ef065a85bb5c41d3b1770204f5f0e960` | 0→1 | 4 基准特征(RIGHT/TOP/FRONT+PRT_CSYS_DEF)，`saved_file_reloaded_and_verified=true` | ✅ |
| 2 | `creo_create_sketch`（XY 矩形 40×25） | `935b068afb8042ebb2b9c8eb823b0612` | 1→2 | PROBE_SKETCH(id40) 4 线 + 尺寸 d3=40/d2=25 + 12 约束 | ✅ |
| 3 | `creo_extrude`（blind 10，add） | `258afd752ceb47d8ad75a3c815a176ab` | 2→3 | 体积 **10000.0** mm³（40×25×10 精确吻合）、6 面/12 边/1 实体 | ✅ |
| 4 | `creo_dump_feature_tree`(probe_extrude) | `49c17a2e25104d0ead7c72a941278630` | 3 | 导出原生元素树 `feature_49.xml`(6785 B) | ✅ |
| 5 | `creo_set_dimensions`（d9 10→20） | `fb2fb91fadfa42d1a8c6e30d2449f9f9` | 3→4 | 体积 **20000.0** mm³（精确 2×） | ✅ |
| 6 | `creo_set_dimensions`（d9 20→10 还原） | `926509366ed3403d80406cba827826e3` | 4→5 | 体积回到 **10000.0** mm³ | ✅ |
| 7 | `creo_chamfer`（边 64，equal-distance 2） | `7e9aecae4b6f4276ba6e3afc89f64e28` | 5→6 | 体积 **9980.0** mm³（去 2×2/2×10=**20** mm³，精确吻合）；面 6→**7**、边 12→**15**、特征 8→**9** | ✅ |
| 8 | `creo_export_model`(step) | `e3614f430f234c1786e92c96ae1a0bd9` | 6 | 生成 `feat019_probe.stp`(9970 B) | ✅ |
| 9 | `creo_inspect_model` | — | 6 | 快照完整：9 特征（含 protrusion id49、chamfer id78/type914）、mm、`has_solid=true`、`healthy=true` | ✅ |

**体积闭环核对**（三重独立验证，全部命中解析解）：
- 拉伸：40 × 25 × 10 = **10 000** mm³ ✅
- 尺寸驱动：40 × 25 × 20 = **20 000** mm³ ✅
- 倒角减料：0.5 × 2 × 2 × 10 = **20** mm³ → 10 000 − 20 = **9 980** mm³ ✅

---

## 3. 健壮性 / 负例

| 用例 | 传入 | 结果 | 断言 |
|---|---|---|---|
| 过期 revision | `creo_extrude{expected_revision:1}`（当前 5） | 提交即拒：`Stale revision: current model revision is 5`，**未产生 job** | ✅ 乐观并发防护有效 |
| 错误引用格式 | `creo_chamfer{references:[{kind:"edge",id:64}]}` | 内核阶段 failed：`key 'edge' not found`；`rollback_succeeded=true`，revision 未推进，无残留特征 | ✅（见问题 O1） |
| 失败后完整性 | 用 `creo_inspect_model` 复核 | revision 6、体积 9980、几何齐全，失败任务零残留 | ✅ 回滚有效 |

---

## 4. 与历史报告的差异（本次新增发现）

- **O1｜`creo_chamfer`/`creo_round` 的 references 结构不直观**：工具描述写「Each set is {edge:reference} or {surfaces:[reference,reference]}」，但直接传裸引用 `{kind:"edge",id:64}` 会以内核错误 `key 'edge' not found` 失败；必须传包裹形式 `[{edge:{kind:"edge",id:64}}]` 才成功。**这与 `creo_capabilities` 中 `references` 一节展示的裸引用写法（`{"kind":"edge","id":...}`）不一致**，容易误导。建议：schema 给出集合对象的完整示例，或在错误中提示期望结构。
- **O2｜失败路径 inspection 计数清零（复现历史问题）**：失败 job 的 `result.inspection.counts` 全为 0，属占位值，**不代表模型真实状态**；必须用 `creo_inspect_model` 复核，否则易误判「模型被清空」。
- **O3｜P1 stale revision 仍只在文本回传**（复现历史问题）：`current model revision is 5` 仅出现在 message，结构化 payload 无 `current_revision` 字段，Agent 需多一轮往返。

> 正面确认（历史亮点保持）：保存-重载-校验闭环（`saved_file_reloaded_and_verified=true`）在新建/草图/拉伸/改尺寸/倒角 5 类操作中全部成立；`creo_get_job` 的「Poll, do not resubmit」防重提示有效。

---

## 5. FEAT-019 判定

用户给定的未通过项：
- ✅ **Toolkit 就绪** —— `toolkit_code=0`、`connection_state=connected`、`worker_exit_code=0`、`state=ready`。
- ✅ **完整建模验收** —— 新建零件 → 草图（含尺寸/约束）→ 拉伸实体（体积精确）→ 特征树导出 → 尺寸驱动重生成（体积精确）→ 边引用特征倒角（体积增量精确）→ STEP 导出 → 快照校验，**9 个环节全部 succeeded，toolkit_code 均为 0**。
- ✅ **自动打开 Creo** —— 协调器拉起 + 连接验证通过（用户已确认）。

**结论：FEAT-019 的「Toolkit 就绪」与「完整建模验收」两项阻塞项本次均已通过，FEAT-019 可标记为完成。**

---

## 6. 产物清单（本机绝对路径）

| 类型 | 路径 |
|---|---|
| 模型版本 | `E:\Projects\MCP_CREO_MechDog\models\8fa908a662b3407792d314b154362414\output\feat019_probe.prt.1 … .prt.7` |
| STEP 导出 | `E:\Projects\MCP_CREO_MechDog\jobs\e3614f430f234c1786e92c96ae1a0bd9\output\feat019_probe.stp` |
| 特征树 XML | `E:\Projects\MCP_CREO_MechDog\jobs\49c17a2e25104d0ead7c72a941278630\output\feature_49.xml` |
| 渲染预览 | `E:\Projects\MCP_CREO_MechDog\jobs\e3614f430f234c1786e92c96ae1a0bd9\output\preview.jpg` |

---

## 附：测试覆盖边界

本次聚焦「就绪 + 核心建模链」的**收敛验证**（连接→草图→拉伸→改尺寸→倒角→导出），共 9 个正向环节 + 2 个负例，全部命中解析解。与 `MCP_CREO_MechDog_测试问题报告.md` 一致，以下家族仍为 schema/文档审查级、未在本次逐一实测：钣金、装配、工程图、翼型、UDF、种子库、曲面/布尔/筋、阵列/镜像/分组/重排。
