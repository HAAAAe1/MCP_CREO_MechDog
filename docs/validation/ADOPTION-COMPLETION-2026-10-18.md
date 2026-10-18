# 现有模型纳管第二阶段：实现、离线验证与实机阻断

日期：2026-10-18（北京时间）。条目：FEAT-042、FEAT-043、BUG-071、FEAT-022。分支 `codex/feat-042-adoption-completion`，未合入main、未发布。

## 来源与实现

0.3.7新反馈[原件](feedback-0.3.7-adoption-2026-10-18/report.md)逐字节归档，SHA256为 `1182c2960ba586e6a699e3c5b6ff403f41538432e80b9ebcb5f1b2566f4679e7`，映射见同目录manifest。文中建议仅作证据，未合并临时adopt接口，未放宽普通origin/checkpoint/unknown保护。

- FEAT-042：沿用受管副本；新增无盘prepare，在同一原生调用中检查当前对象、复制、比较源与副本的特征/尺寸/参数/几何、保存擦除重载核验。准备保持原窗口，模型adopt_pending/revision=0；确认只读取冻结快照，ready/revision=1并显示副本。令牌十分钟，inspect(model_id)重新核验续签；幂等prepare定位同一持久化意图，重复请求不再次建模。提交决策后轮询仅补元数据，不覆盖后续revision。
- BUG-071：已保存来源的哈希、冲突和令牌写入均纳入锁与清理边界，model.json最后发布，避免无令牌半登记。空origin只读预检返回prepare指引，不将目录当文件哈希；非空来源读取失败不降级。
- FEAT-043：新增会话枚举，字段未知时null并附API code；类型查询失败显示complete=false/type_errors。默认20、最多50，32KiB页上限，同次快照十分钟分页；文件身份可证明时才关联受管ID。原生最多4096条，超出明确truncated，保留当前窗口，不加载/保存/自动接管。
- FEAT-022：已有启动指纹与变化检测保持；工具描述、README、安装与[接管流程](../ADOPTION.md)补重启/实际路径/工具清单核对。开发分支86工具，0.4.0正式附件历史85工具保持。

## 身份与环境

- 受测基底提交：`0ed68f4425f28683829f60fffda08b255d517e3e`，受测时dirty=true；基底提交不能独立代表本次改动。
- Windows 11 x64 / build26100；Python3.12.14；匹配Creo12.4.0.0 SDK。MSVC x64/UCRT/Windows SDK构建预检通过；编译器精确版本未独立采集。
- 最终统一检查源码指纹：`2fa8dce69f60e9fa88f4cf565828bc17c5b58ebbfecb7aa45f74bb68d18ab6eb`。运行源码逐文件指纹与构建证明见[source-evidence.json](adoption-completion-2026-10-18/source-evidence.json)。
- worker SHA256：`ba41b3a43fb1b293466c233366f699c8e893f6135109236199877d2521c10cf7`。本记录不分发二进制、常量表、配置或SDK内容。

## 开发验证

| 命令/场景 | 结果与可支持结论 |
| --- | --- |
| `.venv/Scripts/python.exe tools/dev_check.py` | 403项Windows单元全部通过，默认语言/格式基线检查通过；未增加基线容许项，不表示strict历史诊断清零。原始[开发报告](adoption-completion-2026-10-18/development-check.json)、[单元汇总](adoption-completion-2026-10-18/unit-test-report.json) |
| `.venv/Scripts/python.exe bridge.py build` | exit0，Creo12.4匹配SDK构建通过；不等于原生建模验收 |
| adoption业务及真实stdio协议 | 有文件inspect/apply兼容；无盘prepare、确认、续签、幂等、摘要来源；哈希/扫描/令牌写入故障无登记；源/快照在准入后变动时原生派发前拒绝；启动失败审计、原生未知保护、提交后仅补登记、不回退后续revision均通过。原生边界使用明确标注夹具，未借此声明Creo复制语义通过 |
| 实际双线程准入 | 隔离数据根上同时调用prepare，一项受理、一项busy，无第二个登记；runner启动为夹具。不外推为两个真实Creo客户端竞争已验证 |
| session_models业务及真实stdio协议 | 固定分页、过期/非法/被改cursor、null、路径+哈希关联、UTF-8页预算、busy与查询失败通过；原生枚举边界为夹具 |
| `.venv/Scripts/python.exe tools/test_adoption.py --help` | 新增无盘、dirty-current和冻结交互场景参数可加载；测试脚本改为手工在既有会话打开外部文件，避免shell关联启动第二个Creo；库存查询完整翻页 |

早轮开发检查曾在源文件继续编辑期间触发“启动后源码变化”断言；最终停止源码编辑后完整重跑403项通过，未用基线或跳过断言规避。历史中途失败日志保留在本机build目录。

## 本轮实机准入：阻断，未执行建模

用户在本轮明确确认既有记录已核对、会话可操作且001未保存长方体准备好，允许继续实机验收。随后从E盘开发源码通过真实stdio MCP运行：

```powershell
.\.venv\Scripts\python.exe tools\test_adoption.py --unsaved-box
```

北京时间22:50:32（`2026-10-18T14:50:32.918907+00:00`），首次启动就绪探测返回 `state=timeout`、`connection_state=probe_timeout`、预算9秒、`connected=false`，Toolkit原始错误码为null。脚本在准入处退出，`cases=[]`，没有prepare/apply/shell的job_id/model_id，更没有7152体积或保存重载成功结果。原始[就绪记录](adoption-completion-2026-10-18/live-readiness.json)保留协议返回。

已停止进一步连接，未自动retry、结束Creo/nmsd或清除unknown/pending保护。离线进程观察：xtop PID14868（13:12批次）、nmsd PID10548（08:52批次）仍在；不同启动时间只是观察，不证明超时由nmsd导致，不能据此重开已关闭BUG-056。Get-Process主窗口句柄为0，其Responding=true不作为GUI可操作证据。当前未取得这次连接超时的根因。

## 未测与下一步

- 无盘001→prepare/confirm→shell的24000/7152体积、revision0→1→2、原件保留、窗口不变均未实机验证；冻结后修改/关闭原件亦未验证。
- 有文件clean/dirty（尺寸、参数、新特征）、外部目录、钣金、原生失败回滚与真实多客户端并发未做本轮实测。对应脚本具备场景，但不能算通过。
- WorkBuddy未执行；[黑盒提示词](../WORKBUDDY_ADOPTION.md)只包含公开MCP操作与报告要求。连接器真实升级前/未重启/重启后对照未测。
- Creo13外部环境未验收，其他环境范围保持原状；未运行需要连接的test_general，不用历史成功替代本轮结果。
- BUG-071按已覆盖Python收尾范围完成；FEAT-042/043、FEAT-022继续验收中。下一轮先处理会话就绪阻断并核对可操作性，再执行上述本机矩阵及独立WorkBuddy；不把结束进程、重新提交计划或清保护作为默认恢复。
