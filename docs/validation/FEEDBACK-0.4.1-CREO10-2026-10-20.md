# v0.4.1 / Creo 10 反馈核对结论（2026-10-20）

来源:[v0.4.1 报告原件](feedback-0.4.1-creo10-open-2026-10-20/report.md)与关联的 [v0.4.0 报告原件](feedback-0.4.1-creo10-open-2026-10-20/report-v0.4.0.md),字节不变归档,SHA256 见 [manifest](feedback-0.4.1-creo10-open-2026-10-20/manifest.json)。实施安排见[处理计划](../development/CREO10-0.4.1-FEEDBACK-PLAN.md)。

## 核对结论

1. **"P0 磁盘文件打开入口未闭环"的定性:是新增能力缺口,不是 v0.4.1 回归。** 磁盘 `.prt/.asm` 检索入口在本项目任何已发布版本中均未实现、也未在 v0.4.1 发布说明中承诺;该诉求于 2026-10-18 v0.4.0 反馈首次提出,v0.4.1 只是尚未覆盖。登记为 FEAT-044 新增能力,不写作"修复未完成"。
2. **"版本信息埋藏深"的准确缺口。** `creo_capabilities` 顶层已有 `version` 字段(v0.3.x 起持续存在,报告第 7 节自己也以 `version` 检索确认了 0.4.1)。真实缺口仅是 `creo_session_status` 返回不含 `server_version`,归 FEAT-022 本轮补齐。
3. **capabilities 单次输出 106,380 字符属实。** 与 FEAT-023 既有登记一致(0.3.x 起多轮反馈),本轮实施 compact 默认 + section/cursor 分页。
4. **P3-1 adopt 空窗口 `-8` 裸错误码属实。** `ProMdlCurrentGet` 在无当前模型时返回 -8,native 直接以 Toolkit 调用串抛出。归 FEAT-006/FEAT-008 本轮补 `NO_CURRENT_MODEL` 语义化错误,保留失败调用与原码。
5. **装配收养、reconcile 装配覆盖属于后续范围。** 本轮仅登记 FEAT-045(外部装配只读检查)为待规划项,不修改现有装配拒绝边界。
6. **报告确认的正面事实保留**:0.4.1 升级后注册稳定(loader/payload 指纹未变)、`creo_list_session_models` 与 adopt prepare/apply 契约按设计工作。这些与 WorkBuddy 2026-10-19 黑盒记录一致,不重复登记。

## 条目映射

| 反馈编号 | 登记/归属 | 本轮处理 |
| --- | --- | --- |
| P0 磁盘打开入口 | [FEAT-044](../work-items/FEAT-044.md) | 实施 `creo_open_file` |
| P1-1 adopt 契约细化 | [FEAT-008](../work-items/FEAT-008.md) | 拒绝稳定原因 + 实际单位;毫米/依赖准入边界不变 |
| P1-2 装配收养/reconcile | [FEAT-045](../work-items/FEAT-045.md) | 仅登记,后续规划 |
| P2-1 capabilities 体积 | [FEAT-023](../work-items/FEAT-023.md) | compact 默认 + 分页实施 |
| P2-2 顶层显式边界 | [FEAT-008](../work-items/FEAT-008.md) | 顶层支持状态表 |
| P2-3 server_version | [FEAT-022](../work-items/FEAT-022.md) | session_status 各分支统一携带 |
| P3-1 空窗口裸错误码 | [FEAT-006](../work-items/FEAT-006.md) / FEAT-008 | NO_CURRENT_MODEL 语义化 |

同日另一份构建侧反馈(`2026-10-20CREO10.0.0.0-0.4.1jsonhpp仍在指纹清单致注册失效隐患未根治.md`,涉及 json.hpp 指纹清单与 vcvars64_env 键集)不属于本计划范围,原件保留在用户侧,待后续单独登记条目跟进;其中"0.4.1 升级未触发注册换代"的对照事实与本结论第 6 条一致。
