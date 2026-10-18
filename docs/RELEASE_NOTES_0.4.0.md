# 0.4.0 版本说明

发布日期：2026-10-18。版本类型：MINOR（新增公开工具与接口能力）。工具数 84 → **85**（新增 `creo_adopt_current_model`）。

来源：[0.3.7 / Creo 13 反馈](validation/FEEDBACK-0.3.7-CREO13-2026-10-18.md)五项问题全部闭环，外加 DEV-042/BUG-019。

## 变更内容

- **FEAT-042 `creo_adopt_current_model`（新工具）**：显式接管用户已在 Creo 打开的当前模型为**受管副本**。inspect 只读探针返回身份证据（origin 路径 + 文件 sha256 + live 快照 + 会话指纹，显示名不参与身份）与 evidence_token；apply 幂等复制当前会话状态到新受管模型并走完整保存/擦除/重载/验证闭环。用户原件与会话原模型不修改、不擦除、不改名。首批独立 part/sheetmetal（mm 单位、无外部依赖、无不健康特征）；同源重复接管明确拒绝并指向已有 model_id；失败按 unknown_outcome 保护并用 `creo_reconcile_model abandon_new` 收尾。不放宽任何既有所有权保护。
- **BUG-069**：模型名放宽数字开头（`[a-z0-9][a-z0-9_]{0,30}`），大写输入统一规范化为小写并回显实际名，错误信息含完整规则；plate/generic submit/adopt 三校验点统一。`001`、`PRT001`、`prt001` 全部可用；会话同名碰撞仍拒绝。特征 label 规则不变。
- **BUG-070**：`creo_session_status.current_model` 乱码（`▩名0001`）修复——deprecated `ProMdlNameGet` 失败不写缓冲且未初始化导致栈残留暴露；改用继任 `ProMdlMdlnameGet` + 零初始化 + 返回值检查，新增 `name_read_code` 诊断字段。
- **BUG-067**：旋转/拉伸创建失败（`ProFeatureWithoptionsCreate=-1`）报错补跨轴截面提示与元素级错误透传。外部报告的两例经本机复现定性为非法跨轴旋转截面（非 Creo 13 元素树不兼容）。
- **BUG-068**：草图约束引用修复——`ProSectionEntityGetSelected` 参考点按实体类型计算真实点（弧圆心在原点时 `{0,0}` 退化导致 -2）。
- **BUG-050**（验收中，本轮修复主线成因）：coordinates 模式构造中心线按无限轴处理（偏置打位置尺寸、不打端点尺寸）并去重共享顶点尺寸，消除求解器重排几何导致的防偏移守卫拒绝。
- **DEV-042/BUG-019**：圆角/倒角 `radius`/`distance` 字段别名与 `size` 回显一致性（别名冲突拒绝、compact 保留 size）。
- **FEAT-029**（部分，继续验收中）：回调一次性设置指引置前——README 安装节新增 5 步小节（含 `build\blend_callback_protk.dat` 路径示例与 config.pro 持久化），`not_loaded` 状态 instruction 首行即注册入口并含实际 registry_file 路径；readiness 拆分 `not_loaded`（可确定未加载）/`unknown`（无法确认）语义。脚本化注册/自动启动维持待评估未实施。

## 验收摘要

本机 Windows x64 / Creo 12.4.0.0 / 匹配 SDK 与许可（外部 Creo 13 环境未测，见下）。逐项证据：[BUG-067](validation/BUG-067-repro-2026-10-18.md)、[BUG-068/050](validation/BUG-068-BUG-050-repro-2026-10-18.md)、[FEAT-042](validation/FEAT-042-adoption-2026-10-18.md)、[BUG-069/070](validation/BUG-069-BUG-070-2026-10-18.md)、[FEAT-029 指引](validation/FEAT-029-guidance-2026-10-18.md)。全量单测通过（含新增 test_adoption 9 用例、test_model_naming 6 用例）、`tools/dev_check.py` 通过、`tools/test_general.py` GENERAL_CORE_SUCCESS=1、`tools/test_sketch_stability.py` 8 用例通过；FEAT-042 实机接管全链路（inspect 身份核对、apply 复制验证、原件 sha256 不变、接管后编辑保存重载 verified、重复接管拒绝）通过。

## 已知问题与未测范围

- 外部 **Creo 13.4.1.0 / MCP 0.3.7 报告环境未复测**：本机 12.4 结论不外推；BUG-067/070 的 Creo 13 表现、FEAT-042 接管与 BUG-069 新命名规则在 13 上未验证。
- FEAT-042 未测：未保存修改的复制语义（ProMdlnameCopy 是否携带未保存改动）、sheetmetal 实机接管、用户目录原件场景、WorkBuddy 黑盒。
- FEAT-029 继续验收中：实机加载后 ready 分支、升级/回退/并存生命周期矩阵、WorkBuddy；BUG-019 待 MCP 服务重启后 WorkBuddy 别名/冲突复核。
- BUG-050 原 Creo 10 切线链完整输入未取得，卡保持验收中；BUG-057/058 开放中。
- Creo 9 实机编译与建模运行时未验收（本机无 Creo 9 SDK）。

## 附件及 SHA256

见 [validation/RELEASE-0.4.0.md](validation/RELEASE-0.4.0.md) 与 Release 页面；附件由 `v0.4.0` 标签指向的 main 提交生成。
