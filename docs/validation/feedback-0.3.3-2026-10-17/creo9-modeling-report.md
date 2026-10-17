# 2026-10-17_CREO_0.3.3_Creo9编译修复已验收但种子筋放样三问题依旧

**测试日期**：2026-10-17（07:49 – 08:10，GMT+8）
**MCP 版本**：0.3.3（GitHub 最新，Pre-release；涵盖 0.3.1/0.3.2 全部改动）
**Creo 版本**：Creo Parametric 9.0.0.0（本机唯一安装，release_numeric=41）
**测试平台**：Windows 10，stdio，Toolkit 连接已验证；执行器为升级后今早重新构建（含 BUG-033）
**对照基线**：本人 2026-10-15（0.3.0）与 2026-10-16（0.3.2）两轮全量测试报告

---

## 一、本轮结论速览

| 项 | 状态 |
|---|---|
| 0.3.3 核心修复 BUG-033（Creo 9 旧 SDK 孔常量硬引用） | ✅ **本机实机验收通过**（作者本机无 Creo 9 SDK，本机为首次实机验证） |
| 叶片种子加载（0.3.0/0.3.2 两次反馈） | ❌ **仍失败**（种子库未重新生成，发布说明明确"九个种子 PRT 摘要保持不变"） |
| 筋特征（0.3.0/0.3.2 两次反馈） | ❌ **仍失败**（0.3.3 未涉及筋） |
| loft 回调人工注册要求（0.3.2 反馈） | ❌ **仍存在**（0.3.3 未涉及） |
| component_constraints 位置不求解（0.3.2 反馈） | ❌ **仍存在** |
| 其余全链路（草图/特征/钣金/装配/工程图/UDF/翼型/sweep/布尔/镜像/参数关系） | ✅ 全部通过，数值对账精确 |

## 二、0.3.3 修复验收（重点）

### ✅ BUG-033：Creo 9 旧 SDK 的孔常量硬引用——本机实机通过

0.3.3 发布说明称"依据本机 Toolkit SDK 生成两个孔常量的存在性探针；底板与通用孔路径在常量缺失时省略相应元数据节点，避免旧 SDK 对这两个常量的硬引用"，但作者本机无 Creo 9 SDK、未在 Creo 9 实机验收。**本机（Creo 9.0.0.0 + 今早重新构建的执行器）完成了这一验收**：

- 底座 100×60×20 → 120000 mm³ 精确 ✓
- 顶面（surface id 58）线性孔 Ø10 深 10，offset (30,30) → **成功**
- `HOLE_MATERIAL_REMOVED_MM3=785.398163397462`（= π×5²×10，解析值）✓
- 体积 119214.60183660254 = 120000 − 785.398 ✓

结论：BUG-033 在 Creo 9 上确实有效，孔功能开箱即用。👍

## 三、仍未修复的问题（第三轮反馈，按严重程度）

### P0-1 `creo_new_airfoil_blade`：种子库仍未适配 Creo 9

**复现**：`stations=[{chord:100,offset:0},{chord:80,offset:150,twist_deg:20}]`，smooth → 失败。
**现象**：`ProMdlFiletypeLoad ... code -16 during connect`（与 0.3.0/0.3.2 完全一致）。
**证据**：
- 种子文件时间戳仍为 Oct 14 18:54，UGC 头仍为 `PART 2128 1860 ... 2023073`（本机 Creo 9 生成文件为 `2023 1760`）。
- RELEASE_NOTES_0.3.3 明确"九个种子 PRT 摘要保持不变"——作者未重新生成种子。
- `validate_seed`/`list_seeds` 仍只校验哈希（检测盲区未变）。

**建议**（与前两轮相同，此处再次强调优先级）：
1. 用与目标 Creo 版本兼容的构建**重新生成种子库**并按大版本分发；
2. `validate_seed` 增加**原生加载探针**，把版本不兼容在建模前暴露；
3. 文档明确环境要求；Creo 9 用户引导改用 `creo_loft`（但见 P1-1，loft 当前也需人工回调）。

### P0-2 `creo_rib`：筋特征在 Creo 9 上仍失败

**复现**（与前两轮相同的教科书式轮廓）：底座 100×80×15（has_solid 确认）+ XZ 平面竖线 (0,15)→(0,45)（起点在底座顶面）+ `creo_rib(thickness=3, side=symmetric, flip=false)` → 失败："Rib regeneration failed on the requested material side; check profile/body intersection, flip and thickness side"。
**证据**：native.log 显示两阶段创建正常（create=0、MATRLSIDE 重定义成功），redefine 后特征 status ≠ ACTIVE。0.3.3 未涉及筋的任何改动。

**根因判断不变**：0.3.1 的 BUG-017 在 Creo 12.4 验证通过，Creo 9 上同样代码失败，疑为 `ProFeatureWithoptionsRedefine` 对 `PRO_E_STD_MATRLSIDE` 重定义的版本行为差异。

**建议**：与前两轮相同——发布说明为每个修复项标注已验证的 Creo 版本范围；CI 增加最旧支持版（Creo 9）的冒烟矩阵（筋/种子/loft 回调三项）。

### P1-1 `creo_loft`：仍要求人工在 Creo 中注册并启动回调 DLL

**复现**：两 XY 圆截面（Ø16@z25、Ø8@z45）→ `creo_loft(sections=[la,lb], interpolation="smooth")` → 失败：`BLEND_CALLBACK_SETUP_REQUIRED: ... The unsigned Toolkit callback is not initialized ... Register and start the callback using Creo Auxiliary Applications and ...blend_callback_setup.json (registry_file), review its DLL prompt yourself, then retry.`

**背景不变**：0.3.0 上此操作直接成功；0.3.1（BUG-007）起改为人工注册流程；0.3.3 未涉及。错误信息本身质量很好（给了 protk.dat 路径和操作步骤），但流程成本对无人值守自动化是持续损害。

**建议**（第三轮重申）：
1. 在 `creo_session_status`/`creo_startup_status` 中暴露 `blend_callback: registered/started/missing` 状态，调用方可建模前探询；
2. 对已签名 DLL 的支持评估（消除 prompt）；
3. 明确回调状态的生命周期（Creo 重启后是否需重新启动）——目前只能从错误信息推断。

### P1-2 `component_constraints`：应用约束后元件位置仍不重新求解

**复现**：装入 c1（fixed，平移 (-30,20,0)，绕 Z 30°）→ 应用 mate+align+align（三平面）→ 成功挂接（`underconstrained=false`），**但 transform 仍是 (-30,20,0)+30°**，该位置违反新约束（30° 旋转下两基准面不满足 mate/align）。
**状态**：0.3.2、0.3.3 两轮均复现，未修复。

**建议**：`ProAsmcompConstraintsSet` 后显式触发装配重求解；或至少在返回中提示"位置需再生后更新"。

## 四、本轮新发现（0.3.3 引入或首次触达）

### P2-1 `creo_round` 与 `execute_plan` 的 round op 参数名不一致

- 独立工具 `creo_round`：参数名 **`radius`**（required）
- `creo_execute_plan` 内的 `round` op：参数名 **`size`**（required），传 `radius` 报 "Extra inputs are not permitted"

同样问题存在于 `drawing_view` op（plan 内必填 `model`，独立工具有默认值 `"model"`）。同一功能两套参数名，客户端极易踩坑，且错误信息是 pydantic 校验层级、不易定位。

**建议**：统一两处参数名（或在 plan op 中同时接受别名并归一化）。

### P2-2 其他（沿用前两轮观察，仍存在）

- 失败的新模型（如断言失败）进入 `status=failed` 后无清理/重试接口；
- 实体引用错误的 pydantic 报错仍暴露 60+ op 类型名的大 union dump；
- stale surface id 报 `-23`（ProModelitemInit），提示不直观；
- `shell` 在含镜像特征的模型上失败（status 6，无具体原因）。

## 五、本轮通过项与数值对账（0.3.3）

| 项 | 对账 |
|---|---|
| 拉伸 100×60×20 | 120000.0 ✓ |
| 孔（BUG-033 场景） | 去料 785.398163397462 = π×5²×10 ✓ |
| 拔模 5° + 圆角 R5（plan 内） | 120633.60 ✓ |
| 独立圆角 R3（换边） | 120445.82 ✓ |
| 布尔参数 | `ACC_OK` type 53 (BOOLEAN)=True ✓（0.3.2 修复保持） |
| 关系 | `ACC_B`=30 = ACC_A×3 ✓ |
| 钣金第一壁 | 20000.0 = 100×100×2 ✓ |
| 钣金法兰 | 25428.318 = 20000+5428.318（解析值）✓ |
| 展开/平整/折回 | 25314.159 ✓ |
| 装配装入 | 30° 旋转矩阵 ✓ |
| 工程图全链路+PDF | 14802 字节有效 PDF-1.7 ✓ |
| UDF inspect+create | T/DM/REF_CSYS 读取+放置 ✓ |
| 翼型创建+参数更新 | NACA 0012 → 0.18+15° 扭转 ✓ |
| sweep | 成功（与实体部分重叠，增量合理）✓ |
| new_body + 镜像翻倍 | 121429.227×2 = 242858.451 ✓ |

## 六、给作者的建议（第三轮，按优先级）

1. **重新生成种子库 + validate_seed 加载探针**（P0-1，第三轮反馈，仍未动）。
2. **筋特征 Creo 9 兼容排查**（P0-2，第三轮反馈）；至少在产品文档中为 BUG-017 标注"仅 Creo 12.4 验证"。
3. **loft 回调状态化/自动化**（P1-1，第二轮反馈）：session_status 暴露回调状态是低成本高收益项。
4. **component_constraints 触发重求解**（P1-2，第二轮反馈）。
5. **统一 round/drawing_view 等 op 在独立工具与 execute_plan 中的参数名**（P2-1，本轮新发现，低成本）。
6. 小项：失败模型清理接口、pydantic 报错精简、stale id 友好提示。

## 七、总体评价

0.3.3 是一次**定向修复旧 SDK 编译兼容性**的补丁，其核心目标（BUG-033）在本机 Creo 9 上实机验收通过，且修复真实有效——这说明作者对旧版环境的兼容意图是明确的，问题在于**验收环境与用户环境不一致**（作者只有 Creo 12.4）。

三个跨版本 P0/P1（种子、筋、loft 回调）已连续三轮反馈未动，其共同根因都是"修复/验证在 Creo 12.4 完成，未覆盖 Creo 9"。**最迫切的建议不是单个 bug 的修复，而是建立最低支持版本的冒烟矩阵**（种子加载、筋、loft 三项即可覆盖大部分风险）。

---

*测试留痕：本轮约 25 个作业的 request.json / native.log / job.json 全部保留于 `F:\WorkBuddy CREO Space\MCP_CREO_MechDog\jobs\`，模型位于 `models\`。前两轮报告见工作区 `2026-10-15_CREO_0.3.0_...md` 与 `2026-10-16_CREO_0.3.2_...md`。*
