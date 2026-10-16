# MCP_CREO_MechDog 0.3.3：SDK 编译探测与安装诊断

日期：2026-10-16。兼容修复与工程改进，发布为 Pre-release。继承已公开的 0.3.2；本版实现范围为 DEV-028 / BUG-033、DEV-019～022，并同步 DEV-026 反馈归档和后续 WorkBuddy 验收记录。

## 改动

- BUG-033：依据本机 Toolkit SDK 生成两个孔常量的存在性探针；底板与通用孔路径在常量缺失时省略相应元数据节点，避免旧 SDK 对这两个常量的硬引用。新版 SDK 保留原节点。生成表仅在字节变化时写入，不携带跨机器生成的 constants.inc。
- DEV-019：原生构建失败附错误摘要，最多读取日志尾部 128 KiB、保留末尾 15 条 error；C2065 的实际未声明标识符为 PRO_ 时提示 SDK 版本方向，不断言具体最低版本。
- DEV-020：补充 VS Build Tools --includeRecommended 官方命令及退出码成功但组件缺失的诊断。
- DEV-021：config.json 的 vcvars64_env 和 setup.ps1 的 -VcVars64Env 支持完整 INCLUDE/LIB/PATH；显式环境不要求 vcvars64 文件存在，保留 compiler_preflight。缺省 null 沿用原入口；参数优先级、非法字符校验和回写见[安装说明](INSTALL.md)。
- DEV-022：Python 路径命中 WindowsApps 时在执行前说明商店占位程序，并指引 -Python 指定真实解释器。
- 种子分发文本统一按 LF 入包，消除 Windows 工作区与 Git 导出的 ZIP 摘要差异；PRT 二进制保持原样，安装许可只容许 CRLF/LF 差异，内容篡改仍拒绝。
- 保留 0.3.2 发布时的测试夹具 ROOT 隔离、原始反馈格式精确排除及 C++ 验证夹具分发；补齐本次 WorkBuddy 原件的源码包白名单。

## 验证与边界

本次集成、发布回归、源码包独立安装及附件验证见 [0.3.3 发布记录](validation/RELEASE-0.3.3.md)。原开发与 [WorkBuddy](validation/DEV-028-WorkBuddy-review-20261016.md) 证据保留各自提交、版本和日期，不改标为本次新的全量黑盒验收。

Creo 9 / Toolkit 9 的上述编译探测修复已实现；本机无 Creo 9 SDK，Creo 9 实机编译和运行时建模均未验收。当前原生验收限定 Windows x64 / Creo 12.4.0.0 / 匹配 SDK，未测试所有建模家族、所有参数分支或其他维护版。Creo 10 独立复测不设门槛。

WorkBuddy 的通用计划单孔、通孔+盲孔已测范围通过；底板快捷工具 holes 参数据报在客户端序列化阶段受阻，仍未完成该入口的黑盒验收，原因待核实归 FEAT-008。其通用计划替代不覆盖专用原生路径；本版未修改 holes 的可空列表契约。独立 FEAT-029 生命周期实现不属于本次发布。

## 升级

等待任务终态，保留本机 config.json、models/jobs 及未知任务记录，更新完整源码和配套 seed_library，以匹配 SDK 重新运行 setup.ps1 或安装依赖/重新构建，再重启 MCP 连接。公开版本应为 0.3.3，部署身份通过运行路径和源码指纹确认。

九个种子 PRT 摘要保持不变，两份清单及种子 ZIP 安装摘要同步至 0.3.3。附件为源码 ZIP、种子 ZIP 和各自 SHA256；不包含本机配置、SDK、许可、生成常量表、执行器二进制或运行模型。最终标签指向本次实际 main 提交，公开 Release 和远端附件校验在合并 PR 回填。
