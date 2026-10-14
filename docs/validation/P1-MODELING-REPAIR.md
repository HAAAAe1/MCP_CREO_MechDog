# P1联合修复开发验证（2026-10-14）

分支：`codex/p1-modeling-repair`。服务版本仍0.3.0，未发布、未合并main。BUG-007核心最终WorkBuddy验收已接受，整数接口缺陷独立为BUG-028。

## 交付与边界

| 条目 | 本次实现/验证 | 当前结论 |
| --- | --- | --- |
| BUG-028 | 仅loft.sections兼容整数/纯数字字符串/标签，归一化后重复拒绝；公开工具与计划写入同一规范请求；两入口实机原生参数、体积、重载、revision通过 | 开发验证通过，待本轮WorkBuddy |
| BUG-021 | 关系控制查询/明确拒绝；失败首个Toolkit调用、阶段和操作序号保留；简单件/含放样件自由尺寸、关系、参数传播、回滚后继续修改通过 | 原Creo10系统失败未复现，根因不判定，保持待核实 |
| BUG-014 | 缺失计数null、恢复inspection与失败中间状态分开、未保存模型不宣称保存快照、空件无实体、plate仅返回可核实分类计数 | 开发验证通过，待本轮WorkBuddy；未注入回滚失败/未知结果 |
| BUG-022 | 平面放置/参考有效性、与放置面平行或重复定位约束明确拒绝；基准面通/盲孔、实体边和零偏置通过 | 原Creo10合法基准面失败未复现，保持待核实 |
| BUG-017 | 材料侧仅在原生剖面定义后设置；无实体/闭合轮廓拒绝；无效材料侧/不相交有可行动错误；两flip配相应剖面方向、三厚度侧真实rib体积通过 | 开发验证通过，待本轮WorkBuddy；不能称所有原始剖面已修复 |
| BUG-013 | 默认摘要、详情section分页、revision/内容绑定游标、32KiB内容预算；保留工程图及额外inspection字段；小full兼容布局，调用方页收集迁移 | 单元及真实stdio查询通过，待本轮WorkBuddy |

原报告[归档](CREO10-0.3.0-dimensional-edit-2026-10-14.md) SHA256=`05460bd7bfd3c07a76ae33c700dae642cc579b62aed894895282d31189fc37e3`。原始失败jobs未取得本机日志/模型。版本0.3.0相同不足以证明受测构建一致；报告里的“误入Blend”和“全部编辑失败”是待核实判断，不能当已确认根因。

孔阵列对照：60×40×10、孔直径8、定位30/20、d13步进8×4，然后位置30→40，独立尺寸与`D13=40`关系都成功（体积21939.115137602806）。“阵列越界导致失败”推测未获本环境对照支持，不写成根因。Rib同剖面向不相交材料侧失败，但反向端点配flip=true合法成功；两类输入分开记录。

## 本次证据

[结构化记录](P1-MODELING-REPAIR.json)保存各轮原始源码指纹、commit/dirty、MCP输入、job/model IDs、终态、几何、revision、重载、回滚及原始错误；不提交运行日志、模型、SDK或二进制。

- Windows / Python3.12.14 / Creo12.4安装及匹配SDK，真实接口release_numeric=44。开发者通过已验证的Explorer桌面路径启动真实stdio；Codex直接子进程仍曾-4，不宣称BUG-005修复。
- SDK构建通过，worker SHA256=`02e31b21f3b019b8eef2bc89114302429df931af0cb28b74819f2e7434aff2cc`；回调SHA256=`c92da41e2868c47233156e53a04acd99e6222331bc389f34accee315d88c075e`；seed测试公开构建指纹=`a644b967f5f5d3fcfff8e328be40655ca6de6efd6849d143c357f00eb07ee87d`。
- `tools/dev_check.py --work-item P1-MODELING-REPAIR`：191项通过，无新增语言问题，基线未重建。记录受测HEAD779187e、dirty=true及源码SHA，不用之后的文档提交替换。
- 整个迭代146个独立实机作业：125成功、21预期失败，无unknown_outcome。最初31个位于最后孔校验改动之前，独立标为阶段证据；最终原生源码对应115个作业。后续23个最终源码编辑/引用对照重复取得当次证据。
- 成功修改保存重载均true；readonly refresh不要求保存。关系控制、平行孔参考、闭合/不相交筋、断言失败回滚均核对恢复；新件无检查点失败的inspection=null，compact计数全null，未伪装回滚成功。
- 现有直接Blend全套43作业（含三轮串行、两/三截面straight/smooth、已有底座、独立种子、失败回滚/refresh/后续小件）通过。两截面straight种子8作业、三截面straight种子7作业通过，含原生编辑、几何、重载、错误拒绝，原种子文件SHA未变。
- 真实stdio查询默认摘要及页重建通过；单元覆盖大快照预算、游标失效、未知值、单条超预算错误和大工程图字段不丢失。不是原生工程图建模回归。

## 重跑与最终验收

```powershell
.\.venv\Scripts\python.exe tools\dev_check.py --work-item P1-MODELING-REPAIR
.\.venv\Scripts\python.exe bridge.py build
# 需要实际Toolkit连接和当前会话已初始化回调；未知结果停止新增写操作
.\.venv\Scripts\python.exe tools\test_p1_modeling.py
.\.venv\Scripts\python.exe tools\test_direct_loft.py --suite
.\.venv\Scripts\python.exe tools\test_loft_seed.py --seed-file seed_library/seeds/two_straight/mechdog_loft_reference.prt.5 --feature-id 60 --interpolation straight
.\.venv\Scripts\python.exe tools\test_multisection_blend.py --seed-file seed_library/seeds/three_straight/db_a11bae1ccb.prt.2 --feature-id 71 --sections 3 --interpolation straight
```

本次原生通过是桌面路径的当次开发者证据，不能据此保证直接Codex子进程连接。WorkBuddy按[最终验收提示词](P1-MODELING-REPAIR-WorkBuddy-test.md)只用MCP测试；部署需重启开发连接器，新tool参数可见且source_changed_since_startup=false。Creo10由协助者独立验证，原始完整复杂失败模型、并发、外部模态/策略、强制回滚失败/未知结果恢复均未测。
