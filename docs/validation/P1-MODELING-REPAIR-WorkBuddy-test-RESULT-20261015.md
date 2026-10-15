# P1 建模与修复验收报告（WorkBuddy 黑盒 MCP 测试，开发者复核修订）

- 测试日期：2026-10-15；复核修订日期：2026-10-15。
- 原测试方式：WorkBuddy 仅通过已连接 MCP 公开工具操作 Creo。未查看源码、运行本地脚本/单元测试或检查 Git/内部日志。
- 本次修订方式：开发者只读核对本机 `jobs/<job_id>/request.json`、`job.json` 和已保存结果，修正作业关联、输入、revision 和验收边界；没有重跑建模。此复核不计为 WorkBuddy 新增黑盒验收。
- 环境自检由 WorkBuddy 原报：`runtime.code_root=E:\Projects\MCP_CREO_MechDog`、`source_changed_since_startup=false`、Toolkit connected=true、版本 0.3.0，新参数 detail/cursor/section 可见。原生 Blend 的实际成功结果支持当前会话回调已可用，不能仅凭注册文件存在判断。
- WorkBuddy 公开接口未确认完整 Creo 版本、源码提交或构建指纹。开发者复核看到作业模板路径指向 Creo 12.4.0.0，但不将此补充写成 WorkBuddy 通过接口确认了版本，也不据此声称 Creo10 验收通过。
- 原报称串行提交、无 unknown_outcome、每次修改只提交一次并轮询同一 job_id。复核到的成功写作业均保存重载通过、revision +1；失败回滚不推进 revision，readonly refresh 不要求保存重载或推进 revision。

## 总体结论与范围

| 场景 | BUG | 修订后的结论 |
| --- | --- | --- |
| 放样 sections 引用 | BUG-028 | 独立工具标签/整数/数字字符串/混合输入通过；计划入口标签通过。计划入口整数、数字字符串和混合输入的本轮黑盒证据尚缺，不能整项关闭 |
| 尺寸及关系驱动 | BUG-021 | 本轮简单件及含放样件所测编辑链路通过；原始 Creo10 失败尚未复现，保持该来源待核实 |
| 孔参考定位 | BUG-022 | 基准面通孔、盲孔、零偏置及非法参考拒绝通过；实体边参考孔出现成功但不去料异常，验收不通过，根因待定位 |
| 原生筋 | BUG-017 | 本轮合法正例、方向/厚度侧及负例恢复通过；修正代表 job 和模型对应关系 |
| 真实结果/失败恢复 | BUG-014 | 本轮恢复快照、空件和 plate 场景通过；未强制触发恢复失败或 unknown_outcome，不扩大结论 |
| 查询摘要与分页 | BUG-013 | WorkBuddy 报告所测摘要/分页/旧游标拒绝通过；精确 32KiB 字节预算及单条超预算提示两项未验证 |

确认的建模异常是 BUG-022 的实体边参考孔。其余已通过场景不替代缺失分支或 Creo10 验收。原报告中的“5项全部通过、唯一缺陷”不能作为六项统一关闭依据。

## 场景 1：BUG-028 放样引用

几何：XY 圆 sk_a 半径10、Z=0；sk_b 半径6、Z=25。straight、add、new_body=false。理论体积 4900π/3 ≈ 5131.268000863329 mm³，bbox `[-10,-10,0]..[10,10,25]`。

| 模型 | model_id | sections 输入 | 实际放样 job_id | 结果 | revision |
| --- | --- | --- | --- | --- | --- |
| p1_test_loft_labels | a86276c2254a4894a6e67caa4c832767 | `["sk_a","sk_b"]` | 85d12aaf855e4a5aa918341c0a91c6e0 | succeeded，5131.268000863329 | 3→4 |
| p1_test_loft_ids | 4f0c4d86382f431aa7b0fdd7c36841bc | `[40,49]` | d6d5e79e1f7e4d2bb2f597c7d7968ea2 | succeeded，同体积 | 2→3 |
| p1_test_loft_digits | f75ae8319f6344efb2c6746c957a1f55 | `["40","49"]`（WorkBuddy 原报输入） | 35a97bef80e74a4ab26dffc26b42deee | succeeded，同体积 | 2→3 |
| p1_test_loft_mixed | cd088d8506004df889222c5413d17179 | `[40,"sk_b"]` | 30dc5b2fcd7f44bf9b69cdd3bda7223a | succeeded，同体积 | 2→3 |
| p1_test_loft_plan | 34ad5bf430dc4fd896d514ac7e5dc405 | execute_plan 的 `["sk_a","sk_b"]` | 93921b49d6f04e4cb6abf668ac393a83 | succeeded，同体积及体积断言通过 | 1→2 |

成功放样均 `saved_file_reloaded_and_verified=true`；保存前/重载后原生检查为两截面、straight。原草图 ID 为40/49。数字字符串的服务作业请求已经归一化为 `[40,49]`；客户端原始字符串类型来自 WorkBuddy 测试陈述，不能仅凭归一化请求反推。

WorkBuddy 原报负例 `[40,"40"]` 在提交前被拒绝：`Loft sections must be distinct`，无 job，模型不变。该前置调用没有对应作业文件，本次保留为黑盒陈述。

回调未初始化的 job `b32aaaac6dcc4e42811745094f6e3f81` 明确 failed，`BLEND_CALLBACK_SETUP_REQUIRED`；初始化后用新的请求成功。此失败不属于 unknown_outcome，不是重复提交未知结果。

待补：execute_plan 内整数、数字字符串、混合引用。开发者历史测试单独记录于联合证据，不替代本轮 WorkBuddy 覆盖。

## 场景 2：BUG-021 尺寸及关系驱动

模型 `p1_test_edit_1015a`，model_id `72a1797e1cbd4b7f887e4706c8115695`。基线为60×40×10，体积24000；不是30×20×40。

| 操作 | job_id | 终态及体积 mm³ | revision |
| --- | --- | --- | --- |
| 草图及深度10拉伸 | 49a7b579c527420d9c8b077ec7c889e8 | succeeded，24000 | 1→2 |
| set_dimensions，id=9，value=12 | 9532a123ef874b579eaae1a940b628ed | succeeded，28800 | 2→3 |
| set_parameters，SIZE=14（关系尚未建立） | 68f10bb8ca7a4088a2c30072731020f7 | succeeded，仍28800 | 3→4 |
| set_relations，`d9 = SIZE` | 0547e1f8fae249d9b1a0a8bfbd656f90 | succeeded，33600 | 4→5 |
| set_parameters，SIZE=15 | 5adfa2eac1264e0db99e34f61e385f5c | succeeded，36000 | 5→6 |
| set_dimensions，id=9，value=20 | 34f57a1deb0345c78b5e992bddfff8ef | failed，恢复后36000 | 保持6 |
| set_parameters，SIZE=16 | 855ccd4f287e41faa6769e3164e32015 | succeeded，38400 | 6→7 |

失败原文：`Dimension 9 is controlled by relations; edit its driving parameter or relation instead`。`rollback_succeeded=true`、`inspection_source=rollback_verified`。失败 job 本身无 revision 字段；后续请求的输入 revision 仍是6，成功后才变7，因此不能写“回滚推进 revision”。

含放样对照采用上一节的 `p1_test_loft_plan`：

| 操作 | job_id | 体积 mm³ | revision |
| --- | --- | --- | --- |
| 自由尺寸 d2：20→16 | 47f74901c8aa49f6b0e2f844943eb021 | 3874.6309394274112 | 2→3 |
| 参数 RAD_A=16 | 05109f45be094c739ffe7de0ae2b3c37 | 同上 | 3→4 |
| 关系 `d2 = RAD_A` | fe4d432c96c1473eb95de3e6f3a4d02f | 同上 | 4→5 |
| 参数 RAD_A=20 | 4483edb142f54408a340306aa27cf01c | 5131.268000863329 | 5→6 |

d2 是查询取得的原生尺寸，初始值20对应直径，不能写成草图半径20。上述成功写作业保存重载均 true。本轮所测编辑链路通过，不等于原 Creo10 复杂模型来源已修复。

## 场景 3：BUG-022 孔参考定位

原生通/盲孔直径均为8；放置面实际为 `{kind:"surface",id:58}`，基准面参考为 x/y。

| 模型 / model_id | 输入 | 实际孔 job_id | 结果及 revision |
| --- | --- | --- | --- |
| p1_test_hole_1015a / f5661d15fac94330b1f4c2831ea4fbe4 | 60×40×10，offset1=30、offset2=20，通孔 | f6a57d616caa4675b369f337c4616bd1 | 24000→23497.345175425635 = 24000−160π，2→3 |
| p1_test_hole_1015b / 49e8c84ae9cb4ccab8d3fdf5933c973c | 同尺寸独立件，偏置30/20，depth=5 | 9e342432f9a24b3ebcff1f84d663e6f9 | 24000→23748.672587712816 = 24000−80π，2→3 |
| p1_test_hole_1015c / 4bb1fde0b0f643538299f2ab38c50ff4 | min[-30,-20]、max[30,20]、厚10，偏置0/0，通孔 | 2099275c0fa34a56a383f1dc3546ed3d | 24000→23497.345175425635，2→3 |

以上均 succeeded、保存重载 true。非法参考负例实际位于 `p1_test_hole_1015a`：job `78212cb2bb194b4badbb9d2c7516683d`，reference2=z，偏置0/0。failed：`Hole reference2 is parallel to placement; choose a plane crossing the placement plane`；回滚验证体积23497.345175425635、面8/边18，revision保持5。

### 边参考孔异常（验收不通过）

异常同样位于 `p1_test_hole_1015a`，不是 `p1_test_ref_a`。放置面58，reference1为edge59、reference2为edge62，均来自板件顶面的直边，直径8、flip=false。

| 操作 | job_id | 偏置 | 终态 | revision | 前后几何 |
| --- | --- | --- | --- | --- | --- |
| hole_edges | ea0825a4e3da46e597ba17064dce94d5 | 20/30 | succeeded，保存重载true | 3→4 | 体积始终23497.345175425635；面8、边18不变 |
| hole_edges2 | c21ea0922d474fadb1267d6eef3cd9ef | 10/10 | succeeded，保存重载true | 4→5 | 同上 |

两孔均出现原生type=911特征，且尺寸记录分别包含20/30与10/10。两个孔生成的辅助基准面原点重复出现 x≈14.256 / y≈30.496；这些是辅助面的原点，不等同于已经测得孔轴位置。

确认现象：两次成功作业未减少材料；第二次改变偏置后仍无额外切除。根因尚未确认，不能仅凭体积或辅助面原点就认定“offset未解析”。后续需核对最终孔轴位置、方向、参考对象及原生元素树，并用无既有孔的独立板件排除重合切除等因素。

## 场景 4：BUG-017 原生筋

L型基线：60×40×15底板；XZ矩形[0,15]..[60,45]，沿negative拉伸10形成竖壁，体积54000。YZ@x30开放线[10,40]→[40,10]，筋厚4。

| 模型 / model_id | 场景 | 实际 rib job_id | 结果 | revision |
| --- | --- | --- | --- | --- |
| p1_test_rib_1015a / 2bf79ded5b3c455eae26275880c39dfa | symmetric，flip=false | d107f0b434ec43e0bacdecb83a7a0cd4 | succeeded，55250.00000000001 | 4→5 |
| p1_test_rib_1015b / 888fc7040f1347b389cfce916e226d82 | 反向端点，symmetric，flip=true | 0c9b2d94646047f7b824aa68540f7209 | succeeded，55250.00000000001 | 2→3 |
| p1_test_rib_1015c / ff3e73b7a9184b7988f29e9b0dfc41b0 | positive，flip=false | 70543ff057be475eac9125d7b13d6fd0 | succeeded，55250 | 2→3 |
| p1_test_rib_1015d / 465b194eebc64572b9eed1ad3b35120b | negative，flip=false | 0c033b811b6e42f6a4c89dda91a2049d | succeeded，55250 | 2→3 |
| p1_test_rib_1015a | 闭合sk_base作筋 | e1d0cb91eaf841e5917daee638ae4ec9 | failed，`Rib requires an open profile; closed sketch contours are not accepted`；回滚成功 | 保持5 |
| p1_test_rib_1015a | z=60的不相交开放线 | ba6169a095864bb7b1065793c3bb501a | failed，`Rib regeneration failed on the requested material side; check profile/body intersection, flip and thickness side`；回滚成功 | 保持6 |

成功筋原生type=920、健康，保存重载true。闭合负例恢复体积55250、特征17；随后新建不相交测试草图的成功作业 `82ab387207f04d32bf011da089235ce6` 将revision从5推进至6、特征增至20。后续失败保持该检查点，不能把新增草图造成的变化归到失败回滚。

## 场景 5：BUG-014 真实结果及恢复

- 失败恢复证据：上述关系控制尺寸、平行孔参考和两个筋负例的保存结果包含 `rollback_succeeded=true`、`inspection_source=rollback_verified`、恢复inspection及原始错误。未强制触发恢复失败或 unknown_outcome，相关语义仍未验证。
- WorkBuddy 原报：inspect compact、full、refresh三路体积55250.00000000001、特征20/面11/边27、revision6一致。开发者核对到 readonly refresh job `aedeebe99d4646e9b70a04f695bfd8cc`（模型 `2bf79ded5b3c455eae26275880c39dfa`），实际计数、体积及revision6一致。该只读作业保存重载为false，符合只读操作语义，不应要求true。两个inspect调用未单独保存，本次不冒充逐次复核。
- 空件 `p1_test_empty_1015`，model_id `0963f5a67569461a9b8a859d817e6c43`，job `26d0ce215bc14b7cbcffac2caf94d89a`：succeeded、revision1、volume=null、has_solid=false，bodies列表有1项；体数量与实体存在性分别表达。components=null由WorkBuddy原报查询获得，原生inspection未直接提供该字段。
- create_plate真实job为 `29b5f8b03db647b3b56ddc4ed97c032a`，模型名 `p1_test_plate_1015`。80×60×10、R0，四个Ø8孔位于(±30,±20)，中心一个Ø10孔；体积45203.9825383051 = 48000−890π。succeeded、保存重载true；verified_feature_counts为extrude=1、hole=5、round=0；counts.bodies=1，features/surfaces/edges/components均null。该工具未注册模型，不为它编造model_id、revision或分页sections。

## 场景 6：BUG-013 查询分页

本节分页读取、游标错误及客户端输入来自 WorkBuddy 原报告。查询调用本身不生成作业文件，未取得逐页原始MCP响应留档，本次开发者复核不能独立确认每一页内容或字节数。

- list_models默认摘要，无完整几何字段；limit=5连续5页读到offset25。原报limit=50提前返回28条并给后续游标，支持分页行为可用；因无法测量原响应字节，不能断言本次已证明32KiB精确预算。列表变更后旧cursor被拒绝：`Model list changed; restart listing without cursor`。
- inspect默认compact；full支持section和游标。WorkBuddy原报模型变化使旧cursor失效、unavailable_sections=[]。
- 大快照：`p1_test_big_1015`，model_id `4555c7a4c48d4d669a6980165efcc373`、revision2，200点闭合多边形草图、coordinates模式。草图作业 `5015f4ae48974e0b86c5c2d188afa3c4` succeeded、保存重载true；这是草图快照，未建实体，volume=null。
- WorkBuddy原报该快照sketch_dimensions共800条（id2–801），7页条数50/50/50/50/200/200/200；offset依次50→100→150→200→400→600→null，最后complete=true，无缺失/重复，revision始终2。前4页limit=50、后3页limit=200。snapshot_hash原报仅留前缀 `11b5cb68…`，本报告不补造完整值。
- 未验证两项：①32KiB预算的精确字节数；②单条记录超预算时的明确提示。原文“1项未验证”修正为“两项”。单元测试或开发者历史证据不替代本轮黑盒结论。

## 勘误记录及后续验收

原文输入、ID和结论的主要修正保留如下，便于追溯：

| 原记录 | 核对结果 |
| --- | --- |
| 放样半径10、20 | 实际半径10、6；20为第一圆原生直径尺寸 |
| 放样代表jobs 38722…、ea7aa…、dc4df…、d17564… | 分别是创建草图或空件；实际放样jobs见场景1 |
| fe4d432…是计划建模 | 实际为建立关系；计划建模job为93921b… |
| 简单块30×20×40；回滚推进revision | 实际60×40×10；失败保持revision6，随后成功6→7 |
| 通孔Ø10、placement11、偏置0；对称板200×60×10 | 实际Ø8、placement58、非零偏置30/20；对称板60×40×10 |
| ea0825…是基准面孔通过证据 | 实际是边参考孔异常；基准面孔job为f6a57… |
| 31bb133…是零偏置孔 | 实际为空件创建；零偏置孔job为209927… |
| p1_test_ref_a的f20bfb…、6892a…、03985e…证明边孔缺陷 | 实际分别为圆草图、空件、回调未初始化的放样；边孔异常模型和jobs见场景3 |
| 063814…是rib；反向在a、厚度侧在b、负例在c/d | 063814…是竖壁拉伸；实际rib及模型分配见场景4 |
| ef905e…是plate、模型ai_part_70da99f0e55c | 该job实际为空件；plate为29b5f8…、p1_test_plate_1015 |
| BUG-013只有1项未验证；零去料根因确定为定位解析 | 实际2项未验证；零去料现象确认、根因未确认 |

后续：修复并复测BUG-022；补BUG-028计划入口的整数/数字字符串/混合分支；原Creo10尺寸及孔来源另行验收。其余条目只接受本报告明确覆盖的场景。新报告中的草图弧方向及静默失效场景未在本轮实施，另记测试范围。

修订前报告SHA256：`831a5bf15023abfc39a576d869176fb8c467f5aacccb56c4526e531063c5a7a6`。本次保留WorkBuddy原测试来源，以作业记录勘误，不添加未执行测试、不声称已修复孔缺陷，也不代替台账中的独立状态判定。
