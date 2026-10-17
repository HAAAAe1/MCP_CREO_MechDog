# 0.3.4 发布候选与交付核对

日期：2026-10-17（Asia/Shanghai）。条目：[DEV-032](../work-items/DEV-032.md)。阶段：候选与独立分发检查通过；最终主干/Release交付信息回填[PR #9](https://github.com/wudahua/MCP_CREO_MechDog/pull/9)。

用户要求关闭BUG-001并合并全部待合分支，随后明确指定版本0.3.4。本轮保留已知卡死及未完成验收，不连接Toolkit，不将旧实机/WorkBuddy结果改标为本版通过。BUG-001为用户决定关闭，FEAT-018/FEAT-029继续验收中。

源码基线：E盘 `codex/bug-001-hang-diagnosis@db820a4`，远端main为 `9ee923c`。七个待合分支的顶端均已包含在该基线：DEV-030建卡113c0ba、G0复现/白名单bcd90ab、E盘同步209e372、恢复实现5628a33、回调原分支879aebe、集成058f577、离线排查db820a4。原分支合并9766e87保留双方历史，不逐项重复采摘。

## 本次验证

环境：Windows 11 x64 / Python 3.12.14 / 本机Creo12.4 Toolkit SDK与MSVC x64。受测基线db820a4、dirty=true，包含本版元数据和文档改动；精确源码指纹见[JSON](RELEASE-0.3.4.json)。

| 命令或核对 | 实际结果 |
| --- | --- |
| `python tools/dev_check.py --work-item DEV-032` | 297项完整单元通过；语言增量检查通过，35条存量lint/25个存量未格式化文件保持基线，不宣称严格清零 |
| `python bridge.py build` | 返回源码指纹匹配的既有执行器；未连接Creo，不冒称本轮重新编译或原生建模 |
| `python -m tools.test_callback_payload` | 12项独立SDK/夹具ABI检查通过，无Creo会话连接 |
| 离线导入/工具定义 | 版本及editable包元数据0.3.4，84工具且两新增接口存在；未进入服务startup lifespan |
| 文档/证据/种子 | 195份历史验证文件SHA256不变，九个原生种子摘要不变，113个台账ID唯一，382条当前文档相对引用可达 |
| 种子包 | 24文件/9种子，SHA256 `e7e59429aa94e38e25002e2041b816747bca9cf6c766ed14ad8a65f44b901d59`；源码安装摘要已同步 |

从实际提交 `8533054` 的Git快照生成509文件候选源码包，195份历史验证文件与Git对象逐项一致，13份保护原件摘要匹配；无本机配置、SDK、常量表、二进制、运行数据或未跟踪计划稿。新的虚拟环境安装锁定依赖后，独立解压目录再次通过297项单元及语言增量检查，受测源码总指纹与E盘相同（`545729be4b3fb62b5c6b145f732cb810e391fe350c8c7eb6c2f4b4701d77d4f0`）。

独立目录依据本机12.4 SDK重新生成6521个常量并实际编译worker/回调产物，未复制常量表或连接Creo；真实 `setup.ps1 -CheckOnly`、84工具离线导入、种子ZIP实际安装和九种子摘要均通过。候选提交的push/PR两个Windows CI检查均通过。候选包摘要及环境见JSON，它们不是最终Release附件；最终附件须从实际main合并提交重新生成。主干提交、标签、Release公开状态和下载SHA256在同次交付[PR #9](https://github.com/wudahua/MCP_CREO_MechDog/pull/9)回填，不将此候选记录冒称已完成远端发布。

## 未测范围与已知问题

- 最新集成代码的完整原生恢复矩阵、62操作正常长任务、恢复再次中断、两个客户端原生竞争及最终WorkBuddy四动作未完成。
- 集成环境的直接/计划放样、生命周期升级/回退/并存、GUI注册和重启持久性未复跑；历史独立分支结果保持原身份。
- IPC初始化通信失败与Creo无响应的底层根因未定。无新Toolkit连接、GUI操作或故障注入；不解除原unknown保护。
- Creo9实机编译/运行时、Creo10独立复测及其他安装环境未验证。

## 主干、Release及附件

适用当前仓库的每次合入main同步发布规则。最终main提交、PR、v0.3.4标签、公开Pre-release及四份附件SHA256由实际主干产出后回填本次PR/Release。不得通过发布后额外主干提交补写本记录而留下未发布变更；本记录保留合入前真实检查范围。
