# 0.4.2 发布候选与主干交付核对

日期:2026-10-20(Asia/Shanghai)。版本类型:PATCH(用户 2026-10-20 明确指定并弃用开发期 0.5.0 编号;含新增公开工具 `creo_open_file`,按约定本应为 MINOR,作为本次例外)。工具数 86 → **87**。条目:FEAT-044(磁盘打开)、FEAT-023(capabilities 分页部分)、FEAT-022(server_version)、FEAT-006/008(接管 NO_CURRENT_MODEL/reason_code/refusal_details/support_status)、FEAT-045(仅登记)、FEAT-043(描述语义补写)。工作区在发版准备提交后保持干净,受测源码即合入 main 的提交。

## 本轮变更清单

- 代码:`native/generic.cpp`(open_file_native、会话枚举重构、组件完整性核对、adopt 稳定原因前缀、NO_CURRENT_MODEL);Python(`src/creo_mechdog/open_file.py`、`capability_pages.py`、`adoption.py` 结构化拒绝、`bridge.py` 分发/compact/超时、`server.py` 87 工具与 capabilities 分页/session_status、`capabilities.py` disk_open 族、`version.py` 0.4.2)。
- 测试:新增 `tests/unit/test_open_file.py`(13)、`test_capability_pages.py`(8)、adoption 结构化拒绝(2);既有 capabilities/runtime 路径测试随分页接口更新;工具计数断言 86→87。
- 文档:README 标题/版本段/工具表、RELEASE_NOTES_0.4.2、RELEASING/INSTALL/ADOPTION 版本行、BACKLOG、任务卡(FEAT-006/008/022/023/043/044/045)、反馈核对、验证记录(FEAT-044-live、WORKBUDDY-0.5.0-open-file 16/16)、WorkBuddy 提示词(错误码/幂等键/缺件隔离要点)。
- 种子链:两份 seed_manifest `compatible_server_version` → 0.4.2;种子包重建(9 枚种子身份不变);seeds.py expected_digest 同步。

## 检查与实机证据(Windows x64 / Python 3.12.14 / Creo 12.4.0.0 / 匹配 SDK)

- 单元:`python -m unittest discover -s tests` 全量 **434 项** 0 失败 0 错误;`tools/dev_check.py --work-item RELEASE-0.4.2` success、无语言回归。
- 原生回归:`tools/test_general.py` **GENERAL_CORE_SUCCESS=1**(native 改动后建模/保存重载全链)。
- 开发者实机:creo_open_file 12 场景(完整装配 2/2 组件、隔离缺件 `RETRIEVE_INCOMPLETE` 2/2 含用户监督复验、显式/最高数字版本 sha256 级核对、同名冲突、非空会话装配拒绝、中文空格路径、幂等重放、非法输入、源身份前后一致);MCP 层 stdio 直连(compact 10,471 字节/references 9 页/tools 87/server_version/稳定原因码);装配窗口 inspect 结构化拒绝(available=false+reason_code+refusal_details)。证据:[FEAT-044-live-2026-10-20](FEAT-044-live-2026-10-20.md)。
- WorkBuddy 黑盒:**16/16 通过**(含体积级版本选择 .1=48000/.2=38400、bug009_rect 数值最大选 .25、装配省略版本、分页错误处理;发现 session_fingerprint 标识连接而非内容、幂等键跨进程持久、缺件素材搜索路径掩盖,均已跟进)。证据:[WORKBUDDY-0.5.0-open-file-2026-10-20](WORKBUDDY-0.5.0-open-file-2026-10-20.md)。
- 打包与解压核验:源码包 656 文件、种子包 24 文件;解压核对 README 标题 0.4.2、version.py 0.4.2、双 manifest 0.4.2、RELEASE_NOTES_0.4.2 在包、seeds.py expected_digest == 种子包实际 SHA256、`src/creo_mechdog/open_file.py` 随包;重打包 SHA256 可复现。

## 附件与发布

- 合入 main 提交:**`24fc3d5`**(fast-forward 自 `codex/feat044-open-file`,ea19405..24fc3d5,远端已推送)。
- v0.4.2 标签指向:`24fc3d5`(远端 `git ls-remote` 核对 main 与 tag 同指)。
- Release 链接:https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.4.2(Pre-release 非草稿,id 418039183;Release body 含双附件 SHA256)。
- 源码包 SHA256:`8360c558d599871011e9c4ebedfad54aa4e8888c3ba1d34bbe2fac9201514db0`(656 文件;远端下载重算一致)。
- 种子包 SHA256:`ba0e04203ff36772e25c1c7ca10055c70e9483de201a4b8618703f1ccc3564a0`(24 文件,9 枚种子身份不变;与 seeds.py expected_digest 一致,远端下载重算一致)。

## 未测范围

FEAT-044/023(capabilities 部分)保持验收中:显示失败注入、open_file 路径 unknown_outcome(断连/超时)、真实并发、钣金件打开、Creo 窗口视觉显示(黑盒以 displayed/is_current 判断)、外部 Creo 13 环境未验;原反馈 `asm_mx.asm.16` 保持"待原环境复验";Creo 9 无 SDK 未验;Creo 10 独立复测按用户 2026-10-15 决定不作为门槛。同日另一份构建侧反馈(json.hpp 指纹清单、vcvars64_env 键集)不在本版范围,待后续登记条目跟进。

本回填段随交付即时提交入 main,不改变标签所指源码与附件(0.4.0/0.4.1 先例)。
