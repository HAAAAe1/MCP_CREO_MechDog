# MCP_CREO_MechDog 0.4.4 版本说明

日期：2026-10-21。版本类型：**PATCH**（两份 Creo 10 构建侧反馈的完善计划实施，稳定性修复与工程放宽，无新增公开工具；工具数保持 87）。实施计划：[CREO10-0.4.1-FEEDBACK-IMPROVEMENT-PLAN-2026-10-20](development/CREO10-0.4.1-FEEDBACK-IMPROVEMENT-PLAN-2026-10-20.md)；第二份反馈原件归档 [feedback-0.4.1-creo10-build-2026-10-20](validation/feedback-0.4.1-creo10-build-2026-10-20/report.md)（SHA256 `92590f8c…cef17`）。

## 修复

- **DEV-027（json.hpp 换行差异致 loader 世代换代、注册失效隐患）**：保留 `native/third_party/json.hpp` 于 loader/payload 依赖清单（二者实际使用，移出会错误复用旧 DLL）；构建指纹改按 CRLF→LF 归一化内容计算（新算法标识 `sha256-repo-lf-v1`，`src/creo_mechdog/build_fingerprints.py`），SDK 头、有效配置、二进制完整性与发布附件仍按原始字节。构建缓存增加 `algorithm` 与 `generation_key`；旧格式缓存按原始/LF/CRLF 全组合重算原算法，精确命中且不可变镜像 SHA 正确时**复用原世代与注册路径**；无法证明等价时重编并说明原因。元数据逐文件原子发布、成功后才更新缓存标记。新修复：非确定性重编回到历史指纹时世代目录被占用的构建死锁，以派生键 `<指纹>-<sha256[:12]>` 并存解决，历史不可变副本不动。
- **DEV-030（vcvars64_env 只接受恰好三键）**：Python 与 `setup.ps1` 统一为**必须包含大写 INCLUDE/LIB/PATH，其余键接受并忽略**（不执行、不透传、不影响构建指纹）；缺键错误列出缺失项与最小配置示例；忽略提示仅列键名不回显值（Python 写 stderr）；安装回写规范化三键并保留其他配置属性；缺省/null 与显式 vcvars 路径优先级不变。

## 补验收（已交付能力）

- **FEAT-044**：钣金件打开（`model_type=sheetmetal`、displayed）；显式 `.asm.N` 精确版本选择（`.asm.4`=2 组件、`.asm.6`=3 组件）；PrintWindow 只读目视（窗口标题 "WBOPEN_ASMV (启用的)"）；`model_id=null`/`adopted=false`/源文件 SHA 前后一致。
- **FEAT-023**：capabilities 分页补充跨实例（等价服务重启）旧 cursor 拒绝、篡改 cursor 拒绝、大实际内容分节完整遍历与 600 秒真实过期注入。

## 验收摘要

- 469 项单元（新增 `tests/unit/test_build_fingerprints.py` 8 项指纹/迁移/派生键/中断发布用例，更新 install_config 三键契约用例）+ `tools/dev_check.py` 通过（无新增诊断、无基线豁免）。
- 实机构建链：从 0.4.3 真实缓存出发的迁移复用（世代 `695fdd07…` 保留、仅 worker 重编一次、第二次快速返回）、`json.hpp` 全量行尾翻转零重建、真实内容变化重建生效、显式三键+额外键构建通过；`tools/test_general.py` 原生回归；FEAT-044/023 实机场景全过。见 [验证记录](validation/DEV-027-030-IMPROVEMENT-2026-10-21.md)。

## 环境与未测范围

- 本机 Windows x64 / Python 3.12 / Creo 12.4.0.0 / 匹配 SDK 与 MSVC。未测：外部 Creo 10 / Win10 受限环境（reg.exe 拦截）复验、`asm_mx.asm.16` 原环境、显示失败注入/unknown/真实并发（受 BUG-001 后限制）、DEV-027 剩余范围（同源码二进制可复现性、payload 目录累积盘点与安全回收）。
- 升级后请重启目标 MCP 连接器使新构建逻辑生效；已有注册在旧格式缓存下会被等价复用（注册路径不变），无法证明等价时按 stderr 说明重建。

历史版本：[0.4.3](RELEASE_NOTES_0.4.3.md)、[0.4.2](RELEASE_NOTES_0.4.2.md)、[0.4.1](RELEASE_NOTES_0.4.1.md)、[0.4.0](RELEASE_NOTES_0.4.0.md)。
