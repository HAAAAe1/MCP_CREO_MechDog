# FEAT-023：控制工具返回体积——capabilities 摘要与分页实施卡

日期：2026-10-20 细化（原为统一台账条目）。类型：功能。优先级：P2。状态：验收中（capabilities 部分）。目标版本：0.5.0。

来源：多轮能力边界反馈；最新 [v0.4.1 / Creo 10 反馈](../validation/FEEDBACK-0.4.1-CREO10-2026-10-20.md) P2-1（capabilities 单次 106,380 字符，超宿主单次工具结果上限被截断落盘）。

## 目标与范围

本卡为 FEAT-023 中 **`creo_capabilities` 摘要与分页** 的实施部分。其余体积议题（jobs compact 日志、组件清单内联身份、翼型请求体量、union 校验错误、履带请求与日志）仍留台账原条目，随各自触发项处理，不在本轮范围。

## 实施契约

- `creo_capabilities(detail="compact"|"full", section=None, limit=50, cursor=None)`；默认 `detail=compact`。
- compact 返回顶层摘要：名称、版本、更新、工具计数、scope、顶层支持状态表、operations 与 families 名录、section 清单与查询示例、分页说明。单次控制在既有序列化口径内。
- detail=full 按 section 分页：`overview`（除下列大节外的顶层契约）、`tools`（工具清单与 unavailable）、`families`（能力族）、`references`（引用格式）、`seeds`（种子库）、`evidence`（验证证据）、`runtime`（运行身份与源码指纹）。
- 单页按现有序列化口径限制 32 KiB（UTF-8 字节，含分页元数据）；超大集合按条目拆分，不静默截断；单条自身超预算时明确报错并给指引。
- 详情使用进程内冻结快照：600 秒过期；服务重启、cursor 过期/失效、快照指纹变化时明确拒绝并指引重新以无 cursor 查询。
- compact 与 full 的 overview 字段保持一致（同一快照派生）。
- 同步修改默认返回结构变化的迁移指引（capabilities 说明与 README）。

## 验收标准

| 场景 | 可判断的预期结果 |
| --- | --- |
| 默认 compact | 无参调用返回摘要页，显著小于旧全量输出，含 section 清单与 next_cursor 指引 |
| 分页遍历 | 逐 cursor 翻完每个 section 无遗漏、无重复；页大小不超 32 KiB |
| 超大单项 | 单条超预算明确报错/标记，不静默截断 |
| 错误 cursor | 未知 section、非法 cursor、快照变更后拒绝并指引 |
| 过期与重启 | 超过 600 秒或服务重启后旧 cursor 拒绝 |
| compact/full 一致 | 摘要字段与 full/overview 同源一致 |
| 迁移指引 | 文档说明默认结构变化与旧消费者迁移方式 |

开发侧以单元测试覆盖分页/游标/过期/一致性；实机仅验证真实调用路径（compact + 至少一个 full section）。

## 实现与证据

2026-10-20 实施：包内 `creo_mechdog/capability_pages.py`（进程内冻结快照 600 秒+实例 id、compact 摘要、七 section 条目化分页、32 KiB 预算、oversize 显式标记、cursor 失效拒绝）；server `creo_capabilities(detail,section,limit,cursor)` 默认 compact 并携带迁移说明；README 开发分支段同步迁移指引。证据：新增 8 项单元（遍历无遗漏/oversize/过期/快照变化/一致性）；stdio 直连实测 compact 10,471 字节（旧 106,380）、references 9 页翻完、tools 87 条 complete、非法输入拒绝，见[验证记录](../validation/FEAT-044-live-2026-10-20.md)第二节。600 秒过期与重启拒绝由单元覆盖，实机等待注入与超大真实 evidence 单项观察未执行；其余体积议题仍留台账原条目。
