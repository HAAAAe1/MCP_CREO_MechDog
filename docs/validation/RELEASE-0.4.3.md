# 0.4.3 发布候选与主干交付核对

日期:2026-10-20(Asia/Shanghai)。版本类型:PATCH(0.3.7 反馈修复合集与观察性增强,无新增公开工具;工具数 87)。合入范围:`codex/bug-057-feedback-037` 实现线三提交(BUG-036/057/074,f43de43/d4097be/e16ad69,36 文件 +2225/-139)+ BUG-075 登记与补测(bedc1dc)+ 0.3.7 收尾文档与 IMPROVEMENT 计划入库(ca286e5)。工作区在发版准备提交后保持干净,受测源码即合入 main 的提交;附件由该提交工作区生成(合入时 git 行尾规范化使包哈希相对发版前工作区变化,以 main 提交重打包为准并验证可复现)。

## 检查与实机证据(Windows x64 / Python 3.12.14 / Creo 12.4.0.0 / 匹配 SDK)

- 单元:全量 **458 项** 0 失败 0 错误(0.3.7 线新增 24 项);`tools/dev_check.py --work-item RELEASE-0.4.3` 无语言回归。
- 原生:`bridge.py build` 通过(0.3.7 线 native 大改 advanced.cpp +737/generic.cpp/component_transform.h);`tools/test_general.py` **GENERAL_CORE_SUCCESS=1**。
- 0.3.7 线自带验收:三驱动/真实并发/关闭原件确认/回调全生命周期实机(`tools/test_feedback037_modeling.py`)、隔离 C++(component_transform/legacy recovery),见 [FEEDBACK-0.3.7-IMPLEMENTATION](FEEDBACK-0.3.7-IMPLEMENTATION-2026-10-20.md);WorkBuddy 黑盒 **16/16**([WORKBUDDY_037_REMAINING_RESULT](../WORKBUDDY_037_REMAINING_RESULT.md));开发者补测(英寸拒绝/四类型枚举/families 全量/异常候选只读 inspect,[补测记录](WORKBUDDY-037-REMAINING-SUPPLEMENT-2026-10-20.md))。
- 打包与解压核验:源码包 677 文件、种子包 24 文件;解压核对 README 标题/version.py/双 manifest 均 0.4.3、RELEASE_NOTES_0.4.3 与三个新模块/头文件/黑盒报告/IMPROVEMENT 计划随包、seeds.py expected_digest == 种子包实际 SHA256;main 提交工作区重打包 SHA256 可复现。

## 附件与发布

- 合入 main 提交:**`186b6a5`**(fast-forward,cfcea22..186b6a5,远端已推送)。
- v0.4.3 标签指向:`186b6a5`(远端 `git ls-remote` 核对 main 与 tag 同指)。
- Release 链接:https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.4.3(Pre-release 非草稿,id 418494422;body 含双附件 SHA256)。
- 源码包 SHA256:`7bfb307983f4962309373a9cad050a52e09e84f28021e6e4cdd80597040e7b6e`(677 文件;远端下载重算一致)。
- 种子包 SHA256:`23b1d462832769fe80c57efb73c85b98d0c351f05914fe0ddd226abf34138674`(24 文件,9 枚种子身份不变;与 seeds.py expected_digest 一致,远端下载重算一致)。

## 未测范围

BUG-074 真实跨重启四动作与 WorkBuddy(需操作者控制的 Windows 重启后重新 inspect);BUG-057 外部原环境(Win10 19045/Py3.13)复验;BUG-036 实机几何与外部 Creo 9;BUG-075 复现定位;FEAT-042/043/029 剩余边界归原卡。IMPROVEMENT 计划(DEV-027 指纹归一化、DEV-030 vcvars64_env、FEAT-044/023 补验收)已入库**待实施**,不随本版。本回填段随交付即时提交入 main,不改变标签所指源码与附件。
