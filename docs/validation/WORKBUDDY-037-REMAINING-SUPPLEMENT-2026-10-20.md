# 0.3.7 剩余事项补测记录(开发者侧,2026-10-20 晚)

对应 [WorkBuddy 黑盒验收](WORKBUDDY-037_REMAINING_RESULT.md)第 11/12 节遗留项,由开发者在本机完成(素材经一次性 fixture/MCP 准备,非黑盒方式,证据分开记录)。环境:服务 0.4.2 / Creo 12.4(release 44)/ 会话 `8910005913213731761`。

## 1. 场景 4 补全——英寸件接管拒绝字段(通过)

素材:`wb_inch_part`(fixture 基于 `inlbs_part_solid_abs.prt` 模板创建,2×1.5×1 英寸块,`LENGTH_UNIT=in`,体积 3 立方英寸,设为当前窗口;`ProMdlnameCopy` 产生的副本落盘于 `C:\Users\Public\Documents\`,为文件来源)。

`creo_adopt_current_model(mode=inspect)` 实测:

- `available=false`、`reason="Adoption requires millimeter model units"`、**`reason_code="non_millimeter_units"`**
- **`refusal_details.actual_units="in"`、`actual_units_known=true`、`units_query_code=0`**(实际单位可靠给出)
- `current_model.volume_mm3=null`(非毫米体积不标 mm³)、`millimeter_units=false`、`dependency_free=true`、`healthy=true`
- 依赖清单 `dependency_inventory="unknown"` 及说明、健康合并口径说明均在

黑盒报告第 11.1 项的未验证字段全部取得实测值。

## 2. 场景 4 补全——类型枚举(通过)

新增素材:MCP 建钣金 `wb037_sm_enum`(首壁 40×1,sheetmetal)、装配 `wb037_asm_enum`、图纸 `wb037_dwg_enum`(源为钣金件,A4)。

`creo_list_session_models` 单页快照:`total=11`、`complete=true`、`type_errors=[]`,类型分布 **part×5 / sheetmetal×2 / assembly×2 / drawing×2**——无盘件(`WB_UNSAVED_04`,origin 空且 modified)、英寸件、受管模型(model_id 正确挂接)与非受管对象(null)混合在场,类型字段与受管关联全部正确。

小观察(如实记录):该快照中所有条目 `is_current=null`(当前窗口查询返回空),发生于图纸任务将当前窗口切至 DRW 后;不影响类型枚举结论,窗口语义另行归 FEAT-043 既有边界。

## 3. 场景 1 补全——families 分区全量分页(通过)

`detail=full&section=families&limit=10` 逐 `next_cursor` 翻页:**3 页、23 族**,键无重复无遗漏,每页 ≤32 KiB,无 oversize 条目;`complete=true` 收尾。23 族含 0.4.2 新增的 `disk_open`。黑盒报告第 11.4 项关闭。

## 4. 场景 6——异常候选只读 inspect(完成,apply 被保护性阻断)

对黑盒报告第 7 节两个候选执行不带 live 的 `creo_reconcile_model(mode=inspect)`(只读):

| 模型 | 状态 | pending_job | 四动作 |
| --- | --- | --- | --- |
| `wb_conc_a`(bd429fcc…) | new / rev0 | ef52edc9…(job 记录已不存在) | 全部 `available=false`:"Previous runner/worker is active or cannot be proven stopped" |
| `wb_conc_b`(b52c2555…) | new / rev0 | 63e6b4f7… | 同上 |

owners 证据:runner 记录 pid 22376(observed 已停止但 recorded 陈旧为 alive)、worker 身份不可得("Native owner identity is unavailable");guidance 明确:**"Job timestamps do not predate the verified Windows boot … After an operator-controlled restart, inspect again; no action can bypass uncertain ownership"**——即 BUG-074 契约的历史残留:四动作在当前 Windows 启动周期内被正确拒绝,解锁需操作者控制的 Windows 重启后重新 inspect。

**结论**:场景 6 的 inspect 侧完成且保护行为符合设计;四动作 apply 在本机当前启动周期内**无法安全执行**(非"指定模型即可测"),留待操作者重启 Windows 后(或下次自然重启)再执行第二轮 inspect+apply。是否安排重启由用户决定。

## 5. 本轮登记

- 新登记 [BUG-075](../work-items/BUG-075.md)(P2 待复现):Toolkit 状态探针偶发 `invalid_probe_result`(黑盒报告第 0.1 节建议)。

## 6. 剩余未验证(不变)

场景 8(Creo 9 实机)、故障注入类(快照改写/真实再生失败/恢复再中断,按约定不人为制造)、场景 7 升级/回退/重启分支。
