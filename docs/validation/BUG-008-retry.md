# BUG-008：WorkBuddy retry 失败后的继续修复

日期：2026-10-15（Asia/Shanghai）。分支 `codex/bug-008-channel-recovery`，源码提交 `001a4b8088344249c0a04eca0dbe6dc923435950`，dirty=true，服务版本 0.3.1。准确指纹、命令、任务与原始输出哈希见 [结构化证据](BUG-008-retry.json)。这是开发者补测，不替代 WorkBuddy 黑盒复验。没有推送、合并、发布或 C 盘部署。

## 当前结论

[WorkBuddy 原报告](BUG-008-WorkBuddy-acceptance-2026-10-15.md) 的场景 1/2/3/4/5/7 通过；场景 6 及补测 6.2 中 retry 返回无明细错误，未通过。用户确认测试已结束后，继续修复并完成以下开发验证，状态回到**验收中，等待本次实现的 WorkBuddy 复验**。原报告保留原样，其失败不改写为通过。

现有会话的单次和两个真实重叠 retry 已可返回结构化状态并完成连接验证。共享启动记录损坏且无可信现有会话时，会返回 `selection_required` / `startup_state_unreadable`，停止自动启动并给出人工处理说明。本环境的关闭后自动启动仍未通过；不能以此记录声称该路径修复完成，也不能将需要人工打开的路径计为自动恢复。

## 已确认原因与边界

开发者先在隔离夹具复现：共享 `state.json` 为空或非法 JSON 时，旧 `start(retry=True)` 在启动线程之前同步抛出 `JSONDecodeError`，公开 MCP 仅出现通用错误。

随后在实际 Explorer 桌面启动的 E 盘客户端中捕获到共享记录：380 字节全部为 NUL，SHA256 为 `08c3e5bbea4fba57201a69d4bf70a0d255df921fdef4924c22da087f9338c2bc`。这证明受测桌面客户端当前确实面对非法 JSON，与外部报告中的解析错误一致。未确认是何时、由谁或因何写坏；不能推断为重启、许可或 SDK 导致。

C 盘连接器和 E 盘客户端按相同桌面/Creo/PSF 选择计算到同一协调路径。工具宿主的另一次读取曾看到有效旧 JSON，而实际桌面客户端读到 NUL；只保留各次观察，不推断它们差异的底层原因。没有修改 C 盘实现、结束它的服务或覆盖共享历史。原报告中的 `tasklist` 观察作为用户/发起者提供的环境旁证，不纳入 MCP 黑盒结论。

## 修复

- 新模块 `src/creo_mechdog/startup_state.py` 校验共享 JSON 对象、启动次数/保留标志、时间戳和 deadline。读取失败或缺少启动历史均视为未知，不能当成 attempt=0，也不能清空保留状态。
- `start(retry=True)` 不再同步漏出该解析异常；后台在预算内处理。无可信会话时返回需要人工处理的结构化结果；已有匹配会话时只探测连接，保留 `launch_state_known=false`、`automatic_launch_allowed=false` 和原始损坏记录。
- 损坏历史下的多个探针仍服从单 Toolkit 通道，忙碌时在连接预算内等待。两个客户端可以分别完成只读验证；不声称它们共享同一个 `verified_at`。有效历史的原有协调路径继续复用结果。
- MCP retry 经 `invoke` 分派到线程，磁盘/协调互斥等待不阻塞异步协议循环。运行指纹加入新状态模块，便于确认客户端实际加载的实现。
- 沿用 preparation 180 秒及总预算 180 秒加启动预算；损坏历史的现有会话检查另受连接阶段预算限制。未知作业、模型 revision、保存基线和 pending_job 保持保护。

## 本轮验证

环境：Windows 11 x64，Python 3.12.14，Creo 12.4.0.0，Toolkit release_numeric=44。没有进一步修改 C++，复用首轮已按匹配 SDK 构建的 worker，SHA256 `4bb3c984d9c083f271bb7760f48b968bd5ede6b9e83e9031b328d2d9754f786b`。首轮原生/受控证据仍见 [BUG-008.md](BUG-008.md)，其 222 项单元和源码指纹只属于当时实现。

| 检查 | 结果与限制 |
| --- | --- |
| 完整 `tools/test_unit.py` | 230 项通过，0 failure / 0 error；含新增 8 项 retry 回归、真实隔离 stdio、异步循环响应、损坏历史保护、忙碌预算及有效历史单次启动夹具 |
| 语言/格式 | 变更 Python 文件 Ruff 检查通过；全仓标准入口仍被无关的旧 SDK 原始报告 Markdown 代码块格式问题阻塞，没有更改原件或基线。仅排除该份原始报告格式检查的补充语言检查无新增问题；不能写成标准入口通过 |
| 真实无 Creo、损坏历史 | E 盘两个新 stdio 客户端，retry RPC 重叠约 3.3302 ms，均返回有明细的 `selection_required`；无任务、无自动启动。测试脚本当时要求 ready，因此原报告 success=false 原样保留，只支持安全停止/错误可见，不能当作自动恢复成功 |
| 显式人工启动路径 | 确认桌面无 Creo 后，开发者显式打开已配置 Creo；约 17.6 秒后实际连接 code=0。不是 retry 启动。共享状态哈希未变 |
| 真实已有会话 retry | E 盘两个新 stdio 客户端，源码漂移 false；retry RPC 实际重叠约 7.2944 ms，两端进入 ready，分别取得新验证时间；后续单次 retry 和实时 session code=0 通过 |
| 恢复后建模 | 模型 `e6b63ac86df3432a963dcceba350f254`；新建 job `863bbf18726d493696e5354bbc28fad2` revision=1；编辑 job `5d5e2cbfa9f94336ab92573f425bc077` revision=2，矩形 4×6 拉伸 5，体积 120 mm³，参数 `RETRY_VERIFIED=1`。两次 succeeded，保存重载 true、delivery_complete=true、disconnect_code=0 |
| 原保护对象 | 历史 job `272513b7238040c68dce4b923725d870` 仍派生 unknown_outcome；其 job.json、model.json 和保存 PRT 前后哈希一致，没有清 pending、重放或推进 revision |
| 无重复启动/退出 | retry 前后及 MCP 客户端关闭后 parametric PID=17232、xtop PID=4616 和各自创建时间一致；二者是同一 Creo 的正常进程，不能要求总进程数等于 1。最终只读快照中共享记录仍为相同 380 字节 NUL |

验证命令（仓库根目录，PowerShell）：

```powershell
.\.venv\Scripts\python.exe tools\test_unit.py
.\.venv\Scripts\python.exe tools\dev_check.py --work-item BUG-008 --skip-unit
.\.venv\Scripts\python.exe tools\test_startup_retry.py --require-cold --output build/bug008-retry/native.json
.\.venv\Scripts\python.exe tools\test_startup_retry.py --output build/bug008-retry/warm-native.json
```

真实 MCP 脚本通过 Explorer 桌面隐藏启动，沿用 BUG-005 开发诊断路径；这不证明 Codex 普通宿主差异已修复。`--require-cold` 仅检查开始时无 Creo，本脚本不关闭会话。完整原始输出位于忽略的 `build/bug008-retry/`，公开 MCP 验收不要求 WorkBuddy 执行这些命令。

## 尝试与未测范围

首次实际冷态脚本预检也未捕获损坏 JSON，尚未发起 MCP/建模；修正预检记录后才取得上述冷态负例。首次暖态脚本已验证重连，但错误要求进程总数为 1 而停止，未产生建模任务；保留为 `warm-inventory-assertion.json`。修正仅为比较 PID/创建身份，最终暖态完整通过。离线异步测试最初被夹具的全局假时钟阻塞，修正为真实事件循环时钟后取得上述完整 230 项结果；未将这些失败尝试混为最终通过。

补充语言检查曾复用首轮 `build/bug008/check-scoped.py`，覆盖了其 `build/bug008/scoped-style.json`。首轮归档 JSON 中的旧哈希仍属当时记录，该大输出现在不能再按旧路径/旧哈希复核。本轮另存 `build/bug008-retry/scoped-style.json`，后续只更新本轮路径；首轮已归档源码、模型/任务证据与其他原始测试输出保持原样。

未验证：有效且已核对启动历史下的真实关闭后自动启动（仅有隔离回归）、损坏记录的写坏来源/人工核对后重置流程、历史 transform→保存后未交付→-38 完整链、故意损坏实际 Creo 后的无人干预恢复，以及本次修复的最终 WorkBuddy 黑盒。当前共享损坏记录仍保留，若关闭 Creo，不能承诺 retry 自动打开；需要人工打开或先核对启动历史。复验按 [WorkBuddy 定向提示词](BUG-008-WorkBuddy-retest.md) 执行，分别报告已有会话重连和自动启动，不能互相替代。

## 2026-10-16：用户确认再次重启后的代为启动

用户反馈误操作重启，并询问是否必须亲手恢复。根据该请求，开发者确认实际桌面没有 Creo、当前配置目标可识别且启动协调锁可取得，在启动锁和 Toolkit 通道保护下只发出一次显式启动请求。09:01:33（Asia/Shanghai）实际探针返回 connected=true、toolkit_code=0、release_numeric=44。共享损坏记录、历史 unknown job/model 与保存文件哈希均未改变，没有解除 reservation、重放任务或修改实现。

该操作属于“用户请求后代为启动”，不要求用户亲手点击，也不等于 MCP retry 已自行修复损坏历史或自动启动通过。WorkBuddy 可在可用会话下继续步骤 2/3/5/7；本次没有代签这些黑盒场景。准确身份、命令、进程、时间线与未测范围见 [本次运行证据](BUG-008-assisted-start-2026-10-16.json)。
