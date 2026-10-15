# BUG-022 WorkBuddy MCP 最终补测记录（2026-10-15）

依据：[BUG-022.md 最终 WorkBuddy 补测场景](BUG-022.md)。仅通过已连接 MCP 公开工具执行，未读取源码/Git/本机配置/日志、未执行本地脚本。每次操作只提交一次并轮询同一 job，无 unknown_outcome、无重交。

## 环境前置确认（公开接口）

| 项 | 结果 | 来源 |
| --- | --- | --- |
| 代码根 | `E:\Projects\MCP_CREO_MechDog` ✓ | capabilities.code_root |
| source_changed_since_startup | `false` ✓ | capabilities |
| Toolkit connected | `true`（release_numeric=44）✓ | session_status / startup_status |
| Creo 版本 | `C:\Program Files\PTC\Creo 12.4.0.0` | check_environment.creo_root |
| 构建/worker 指纹 | 接口未提供，**无法确认** | — |

## 场景1：实体边参考通孔 + 交换参考 + 平面查询对照 — 通过

三个独立板件（60×40×10，XY[0,0]..[60,40]，体积24000）。参考面/边均先 inspect 查询（顶面=面58，y=0顶边=边59，x=0顶边=边62），未猜ID。

| 子项 | job_id | model_id | 体积mm³ | 孔轴 | 去料mm³ | rev | 重载 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1a 边参考 12/8 | 24dfc5bcd48941b9a702142e55990acd | a906d41f7c454fc2a83df88d06b038f3 | 23497.344418537956 | (8,12,10)→(8,12,0) | 502.6556 | 3→4 | true |
| 1b 交换参考+偏置 8/12 | fadd922341554beebfbcb630864cf3a3 | fac0e2da36124fe78aad5a3423226900 | 23497.344418537956 | (8,12,10)→(8,12,0) | 502.6556 | 3→4 | true |
| 1c 平面查询放置 {normal:[0,0,1],offset:10} | 63adc4390453452788767f91f1686302 | c0046adc61a549f38b080c142eedb3bb | 23497.344418537956 | (8,12,10)→(8,12,0) | 502.6556 | 3→4 | true |

解析值 24000−160π=23497.3452，误差≤0.0008<0.01 ✓。孔心 (8,12)、半径4、type=911、健康、incomplete=false。三种子项同位置同体积。

## 场景2：顶面/底面盲孔 — 通过

| 子项 | job_id | model_id | 体积mm³ | 孔轴 | 去料mm³ | rev | 重载 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 顶面盲孔深5 | c41095d3ec564a7697b4854cfb39fb7e | b465b81869774e0d8d5476b765727f2e | 23748.672209268978 | (8,12,10)→(8,12,5) | 251.3278 | 3→4 | true |
| 底面盲孔深5 flip=false | 55d818ab38c94e0782d97e62cdc41d48 | 22cc0f700263436d863483ce299bf69e | 23748.67280797907 | (8,12,0)→(8,12,5) | 251.3272 | 3→4 | true |

解析值 24000−80π=23748.6726，误差<0.0005 ✓。底面参考为面53及其底边54/57，默认向材料内钻孔。type=911健康。

## 场景3：基准面孔后追加边参考孔 — 通过

model_id=`5d2964b4213745fd9675f7900d88a02b`，label 分别为 `hole_datum_base` / `hole_edge_append`。

| 步骤 | job_id | 体积mm³ | 孔轴 | 去料mm³ | rev |
| --- | --- | --- | --- | --- | --- |
| 基准面x/y参考 (30,20) Ø8通孔，feature_id 78 | d03483fc642645f9bb3601ede4e5617e | 23497.345175425635 | (30,20,10)→(30,20,0) | 502.6548（=160π精确） | 3→4 |
| 追加顶边59/62偏置10/10孔 (10,10)，feature_id 116 | c08955cce9044c139c5dbf3ad3707752 | 22994.69035085127 | (10,10,10)→(10,10,0) | 502.6548 | 4→5 |

最终体积精确等于 24000−320π ✓，两孔并存（圆柱面 94/95@ (30,20)、136/137@ (10,10)），重载true。

## 场景4：负例拒绝与恢复追加 — 通过（8项负例全部明确失败并回滚，随后成功恢复）

基线：revision=5、体积 22994.69035085127、features=12。

| 负例 | job_id | 失败消息 | 回滚 | 失败后核对 |
| --- | --- | --- | --- | --- |
| 完全重合孔 (10,10) | 5031b0140b68467f8d48b09a249715c3 | Hole removes no material; check reference offsets, placement, flip and overlap with existing holes | true | 体积/特征数不变 |
| 板外 80/80 | daee6c386ee842db99eb833d78b10ee7 | 同上 | true | 同上 |
| 非重合 (20,20) flip=true 反向 | 50426247d962488281c5054d1af1fec0 | 同上 | true | 同上 |
| 重复参考（ref1=ref2=边59） | ff9f7d475d68452b948db99726e9f8a2 | Hole secondary references do not provide independent location constraints | true | 同上 |
| 平行参考（Z向基准面+X基准面） | 1d8c26dcb26a43e8b30d2ca43fa74a16 | Plane reference must identify exactly one surface; inspect the model and use a surface ID | true | 同上 |
| 弯边（孔圆弧边146） | 8c1c158b0c6a47bd8e289af62c20dc05 | Linear hole requires straight edge references | true | 同上 |
| 法向边（竖直边64） | 8a0c50d4bff240e68396a4ba1a981ff6 | Hole edge references must lie in the placement plane | true | 同上 |
| 不共面边（顶边59+底边57） | c8faa35cdb6a483591547ae2ad3a4c2e | Hole edge references must lie in the placement plane | true | 同上 |

说明：平行参考负例在参考解析阶段即被拒绝，消息为"未能唯一定位一个面"而非字面"平行"；确属明确失败+回滚，记录措辞差异。所有失败作业公开返回中**未提供检查点/文件哈希字段 → 记未验证**；以 rollback_verified 实时检查（体积、features、surfaces、edges 全部不变）替代核对。

恢复步骤：在 (45,10) 追加合法孔（ref1=边59 offset10，ref2=边62 offset45），job_id=`cab0f6164c7a42c9b0e881b64c342f07`，feature_id=158，体积 **22492.035736766353**（精确=24000−480π ✓），revision 5→6，重载true —— 证明失败后可继续建模。

收尾只读 refresh（job `22d9fa7709394d7d83f601db4fbae513`）：inspection_source=live_query，体积一致，revision 保持6（只读不推进revision ✓）。

## 结论

| 场景 | 结论 |
| --- | --- |
| 前置确认 | 通过 |
| 1 边参考通孔/交换/平面查询对照 | 通过 |
| 2 顶/底面盲孔 | 通过 |
| 3 基准面孔+边参考追加 | 通过 |
| 4 负例拒绝+恢复追加 | 通过 |

**BUG-022 最终 WorkBuddy MCP 补测（2026-10-15）全部通过**，覆盖边参考修复的正例与拒绝路径；体积误差均<0.01mm³，所有成功写操作重载true、revision仅+1，失败均回滚且模型保持。

未测/无法确认（按补测场景范围）：构建与worker指纹（接口未提供）、Creo10原始场景、并发、强制恢复失败与未知结果恢复。
