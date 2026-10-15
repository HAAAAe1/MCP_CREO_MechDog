# P1 建模联合修复（2026-10-14）

状态：验收中；目标版本：未排期。

本任务包含 BUG-028、BUG-021、BUG-014、BUG-022、BUG-017、BUG-013。保留独立编号、分批提交和独立证据，联合回归后分别验收。基于含 BUG-007 修复的 HEAD 2b4dccc，分支 codex/p1-modeling-repair；此依赖尚未进入 main。已有未提交文档保留。

## 已有基线

[BUG-007 WorkBuddy 报告](../validation/BUG-007-WorkBuddy-acceptance-2026-10-14.md)确认标签引用的直接/计划放样、两/三截面、straight/smooth、已有底座追加、保存重载、revision、失败回滚和后续通道通过。整数引用公开路径失败单列 BUG-028。报告只确认 release_numeric=44；Creo10、并发、外部模态及策略场景不外推。开发者 stdio 整数引用成功证据原样保留。

## 顺序与验收

1. BUG-028：loft.sections 的整数、纯十进制字符串和标签归一化；独立工具与计划入口一致，重复引用拒绝，不做全局字符串转换。
2. BUG-021/014：简单件与含放样件尺寸/关系驱动、准确拒绝关系控制尺寸、保存重载与失败回滚；真实 inspection、计数、空件和未知状态。
3. BUG-022/017：基准面孔、实体边对照、通/盲孔及偏置；合法相交开放草图的原生筋及方向分支，非法输入回滚。
4. BUG-013：列表/检查默认摘要；详情 section 分页、revision绑定、32KiB响应预算、完整性指引，迁移现有调用方。

Windows：tools/dev_check.py；原生：匹配SDK构建及 tools/test_p1_modeling.py、受影响既有回归。成功修改要求几何/参数、revision推进一次及 saved_file_reloaded_and_verified=true；失败检查保存检查点、实际模型和revision。遇未知结果停止写操作。

本机Creo12.4与协助者Creo10证据分别记录。WorkBuddy仅MCP黑盒，不读源码、不执行本地脚本；开发者证据和最终公开接口验收分开。证据记录版本、commit、dirty、源码指纹、时间、环境和未测范围。不能用历史成功、编译或单元通过代替实机验收。

## 排除

不增加create_plate模型注册，不处理其他缺陷、全局通道恢复、capabilities瘦身或发布。不改变服务版本或自动重建风格基线。

## 当前结果

2026-10-15更新：BUG-022本环境边参考追加修复已由用户确认[WorkBuddy四场景全部通过](../validation/BUG-022-WorkBuddy-retest-20261015.md)，原Creo10来源仍待核实。本次确认授权提交、推送当前开发分支；其他条目及发布各自验收，不随BUG-022一并关闭。下段保留2026-10-14开发验证时的历史结论。

[本轮联合证据](../validation/P1-MODELING-REPAIR.md)：191项统一检查、匹配SDK构建、最终原生源码115个作业及阶段性31个作业均符合预期；原始Creo10 BUG-021/022仍待核实，其他四项开发验证通过，等待最终WorkBuddy。代码已分批提交，版本仍0.3.0，未发布。
