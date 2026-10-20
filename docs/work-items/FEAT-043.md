# FEAT-043：只读枚举当前 Creo 会话模型

日期：2026-10-18。类型：功能。优先级：P2。状态：验收中。目标版本：未排期。

来源：现有模型无法纳管反馈第5项；关联 FEAT-042、FEAT-023。

## 目标与范围

新增 creo_list_session_models(limit=20, cursor=None)，最大50条；返回名称、类型、是否当前、origin、有无保存来源、未保存修改状态及可证明的受管关联。分页绑定同一快照，无法确认的字段为 null。查询不加载、保存或切换模型，不自动接管；用户在 Creo 切到目标后使用现有接管工具。通道 busy 立即拒绝，无自动重试。

## 验收

单元与真实 stdio MCP 覆盖分页、过期/非法cursor、状态未知、读取失败、受管关联和busy；本机 Creo12.4/匹配SDK 枚举已保存、无盘、dirty、不支持类型与已受管对象，检查当前窗口不变。开发证据与 WorkBuddy 黑盒分开；当前会话限制满足前不建立新连接。

## 实现与证据

本轮在 codex/feat-042-adoption-completion 实施。原生枚举受支持查询类型，不支持/失败的类型保留type_errors与complete=false；逐字段返回query_codes/null。Python固定快照分页，十分钟有效、32KiB分页上限，只按已核验文件身份关联登记。规则及真实stdio（原生边界替换）回归、全量403项单元和匹配12.4 SDK构建通过。2026-10-18开发脚本首次就绪探测超时的[历史记录](../validation/ADOPTION-COMPLETION-2026-10-18.md)保持原样。2026-10-19用户转贴WorkBuddy报告已真实发现无盘WB_UNSAVED_01（origin空、has_saved_origin=false、modified=true、model_id=null），并观察准备前后原件/副本及当前窗口；一次真实busy含blocking字段，不能据此判定实际并发测试通过。见[黑盒补录](../validation/ADOPTION-WorkBuddy-2026-10-19.md)。后续WorkBuddy在9模型会话以limit=2遍历5页，相同snapshot_id/checked_at、无重复遗漏、末页next_cursor=null且不切窗，真实多页通过；同时观察无盘、clean、dirty、sheetmetal、assembly与受管副本。unknown字段失败路径、其他类型及实际并发仍未验。session_model_id跨类型重复沿用临时发现提示边界，不作身份键；query_codes仅保留实际查询的诊断，subtype目前只查询part分支。

## 2026-10-20：session_model_id 取 0 与重复的再确认

[0.5.0 open-file 黑盒验收](../validation/WORKBUDDY-0.5.0-open-file-2026-10-20.md)附带发现：重启后的新会话中 WBOPEN_V1 与残留 WBOPEN_ASM2 同时返回 session_model_id=0，上一会话也出现过装配与子件同值——与既有定性一致（Creo 会话内整数 ID 可为 0 且跨类型重复，仅作临时发现提示）。工具描述已补写"可能取 0 或跨类型重复，定位模型用 name+model_type"；session_fingerprint 标识连接/进程会话、不随会话内容变化这一语义也已写入描述，避免以指纹判断会话内容。不改字段行为。
