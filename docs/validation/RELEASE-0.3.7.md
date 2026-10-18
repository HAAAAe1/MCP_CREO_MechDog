# 0.3.7 发布候选与主干交付核对

日期：2026-10-18（Asia/Shanghai）。条目：DEV-041 补充交付（README 勘误版）。起因：0.3.6 发布时遗漏 README 版本段同步，用户在 GitHub 页面发现；按"合入 main 必须随同次发版"规则以 0.3.7 纯文档版补齐。无代码与接口变更，工具数 84 不变，功能交付与 0.3.6 一致。

## 本轮变更清单

- `README.md`：标题与版本段更新（0.3.6 交付事实 + 0.3.7 定位说明），移除已过时的 BUG-056 待核实/M2 未收尾表述。
- `version.py` → 0.3.7；[RELEASE_NOTES_0.3.7.md](../RELEASE_NOTES_0.3.7.md)。
- 0.3.6 交付回填记录入库：`validation/RELEASE-0.3.6.md` 回填段、`work-items/DEV-041.md` 完成态、`development/RELEASING.md` 版本行、`BACKLOG_COMPLETED.md` DEV-041 行、`BACKLOG.md` 当前安排与版本（0.3.6 交付后按惯例本应随下次开发提交，本次随勘误版一并入库）。
- `docs/work-items/DEV-042.md`：BUG-019 执行卡建卡与台账同步。
- 种子清单 `seed_library/seed_manifest.json` 与 `docs/seed_manifest.json` 的 `compatible_server_version` → 0.3.7；`seeds.py` expected_digest 同步新种子包 SHA256（9 枚种子身份不变，仅清单标记变化）。

## 检查

- `tools/dev_check.py`：success=true、unit_tests passed，无新增语言问题，存量 35 lint/25 未格式化基线保持。
- 无 C++ 改动：无原生回归适用项；历史实机证据按原身份保留。
- 附件从 `v0.3.7` 标签指向的 main 提交生成；种子包内容仅 manifest 版本字段变化。

## 附件与发布（回填）

- 合并 main 提交：（回填）
- v0.3.7 标签指向：（回填）
- Release 链接：（回填）
- 源码包 SHA256 / 种子包 SHA256：（回填）
