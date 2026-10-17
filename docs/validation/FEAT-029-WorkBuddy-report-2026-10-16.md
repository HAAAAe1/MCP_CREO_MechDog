# FEAT-029 WorkBuddy 独立验收报告（test 版部署 / 0.3.2 · 回调就绪后补跑）

- **验收对象**：**test 版部署** —— MCP 连接为 `MCP_CREO_MechDog_test`，`resource_root / code_root / data_root = E:\Projects\MCP_CREO_MechDog_Test`
- **提示词**：`E:/Projects/MCP_CREO_MechDog_Test/docs/validation/FEAT-029-WorkBuddy-test.md`
- **执行方式**：黑盒。只通过公开 MCP 工具驱动真实 Creo 会话；不读源码 / Git / 配置文件 / 日志，不跑本地脚本，不代办部署或安全确认
- **执行时间**：
  - 首轮（回调 `not_loaded`）：2026-10-16 15:51–15:56 (GMT+8)
  - **补跑（回调 `ready`）：2026-10-16 16:07–16:13 (GMT+8) / 08:07–08:13 (UTC)**
- **上位环境**：Windows x64 · Creo Parametric **12.4.0.0**（`release_numeric = 44`）· 单位 mm
- **范围**：第 1、3～8 项。第 2 项（升级/重启/回退/并存）未由发起者准备 → **未验证**
- **历史留档**：`FEAT-029_独立验收报告_dev版.md`（首轮 dev 版，不作为本轮结论）

---

## 0. 结论速览

| 项 | 场景 | 判定 | 依据 |
|---|---|---|---|
| 前置 A | 公开工具含 `creo_callback_status` | ✅ **满足** | 工具存在且可用，实测调用成功 |
| 前置 B | `resource_root == E:\Projects\MCP_CREO_MechDog_Test` | ✅ **满足** | `resource_root / code_root / data_root` 三者一致 |
| 前置 C | 注册路径 `…\MCP_CREO_MechDog_Test\build\blend_callback_protk.dat` | ✅ **满足** | `registry_file` / `registry_shortcut` 均指向该文件 |
| 1 | 身份 / 就绪 / 加载身份 | ✅ **通过** | `readiness=ready`，`reason=live_identity_verified`，加载身份与部署逐项一致 |
| 4-① | `creo_loft` 直建（已有件） | ✅ **通过** | 体积 `5131.268000863329`；rev 只推进一次；原生「混合」；重载已验证 |
| 4-② | 一次计划内 `op=loft`（新件） | ✅ **通过** | 同一目标值；3 个 op 全成功；rev 只推进一次 |
| 5-a | 2/3 截面 straight/smooth | ✅ **通过** | 2 截面 straight=smooth=5131.26800086；3 截面 straight=5131.26800086、smooth=5130.64936565（不同） |
| 5-b | 已有底座追加放样 | ✅ **通过** | 总 `11121.237993707866` = 底座 4523.89342117 + 锥台 6597.34457254；底座特征与几何未变 |
| 5-c | 种子工具对照 | ✅ **通过** | `native_multisection_blend_seed_rebinding`；公开返回 `seed_sha256`；体积与直建一致 |
| 6-a | 重复截面 / 非法模式 / stale revision 拒绝 | ✅ **通过** | 三者均在模型变更前被拒，`revision` 保持 |
| 6-b | 断言失败触发真实回滚 | ✅ **通过** | `rollback_succeeded=true`，`inspection_source=rollback_verified` |
| 6-c | 回滚后后续独立小件 | ✅ **通过** | `create_plate` 40×30×10 = 12000 mm³，重载已验证 |
| 7 | 单次提交 + 轮询终态 | ✅ **通过** | 12 个作业全部单次提交、达终态，无 `unknown_outcome`、无重提 |
| 3-并发 | 真实并行提交 | **并发未验证** | 未做真实并行会话调用（按要求如实报告） |

**总体判定：本轮 test 版部署的核心门槛已全部通过。** FEAT-029 要求的关键成功断言全部达成：`creo_loft` 直建原生 Blend、体积 ≈ 5131.26800086 mm³（容差 `max(0.01, 预期×1e-6) = 0.01`）、`revision` 只推进一次、`saved_file_reloaded_and_verified=true`，且回调加载身份与当前部署逐项一致。

**与首轮的唯一差异是常驻回调状态**：首轮 `not_loaded`（`recorded_application_not_active`）导致放样被 `callback_preflight` 阻断；发起者在 Creo「辅助应用程序」中手动启动该条目后，`readiness` 转为 `ready`（`live_identity_verified`），本轮全部放样场景得以真实执行。**无需重新注册 dat**，与提示词「正常重启后主条目自动出现并已启动、勿要求再次注册」一致。

---

## 1. 环境与公开身份（第 1 项）

### 1.1 公开服务/部署身份

| 项 | 实际值 | 来源 |
|---|---|---|
| 连接 / 服务名 | `MCP_CREO_MechDog_test` / `MCP_CREO_MechDog` | 工具命名空间 / `creo_capabilities.name` |
| 版本 | **0.3.2** | `creo_capabilities.version` |
| 工具数 | **83 / 83 enabled**，`unavailable_tools = []` | `creo_capabilities` |
| 运行入口 | `E:\Projects\MCP_CREO_MechDog_Test\server.py` | `creo_capabilities.runtime.server_entry` |
| `code_root` / `resource_root` / `data_root` | **`E:\Projects\MCP_CREO_MechDog_Test`**（三者相同） | `creo_capabilities.runtime` |
| `source_changed_since_startup` | `false` | 同上 |
| 会话 | `connected=true`，`connection_state=connected`，`toolkit_code=0`，`disconnect_code=0` | `creo_callback_status.session` |
| 证据目录 | `E:\Projects\MCP_CREO_MechDog_Test\build` | `creo_capabilities.evidence_directory` |

### 1.2 加载身份（`creo_callback_status`，第 1 项核心）

**探针实测（`checked_at = 2026-10-16T08:07:58.680728+00:00`，串行调用）**

| 字段 | 值 | 判定 |
|---|---|---|
| **`readiness`** | **`ready`** | ✅ 就绪 |
| **`reason`** | **`live_identity_verified`** | 实时身份校验通过 |
| `instruction` | `Callback verified in the selected session; this is a point-in-time observation` | 时点观测 |
| `registration_status` | `unknown` | GUI 注册状态不可查询 → **无法确认**，如实保留 |
| `protocol` / `contract` | `3` / `blend-selection-v3-ordered-curves-mm` | 与部署一致 |
| `registry_file` | `E:\Projects\MCP_CREO_MechDog_Test\build\blend_callback_protk.dat` | 与提示词一致 |
| `persistent_registration_config` | `…\build\blend_callback.config.pro` | 持久注册配置 |
| `loader_abi` | `1` | — |

**加载实例（`loaded` 段，与部署逐项比对）**

| 字段 | 加载值 | 部署值 | 一致性 |
|---|---|---|---|
| `command` | `MechDogBlend_9346f9e0410a6b7f91b6c33d_7ffafcc9` | — | — |
| `dll_sha256` | `9346f9e0410a6b7f91b6c33db2b6be9b8e2f1e597e6d41c5fa0f774b6081e20e` | 同左 | ✅ |
| `loader_sha256` | `a4a75e71a47abd66e16cbd994e34e19ea67aba4abb7e7f3eccf2dd098e196fb9` | 同左 | ✅ |
| `protocol` | `3` | `3` | ✅ |
| `resource_root` | `E:\Projects\MCP_CREO_MechDog_Test` | 同左 | ✅ |
| `initialize_code` / `initialize_stage` | `0` / `after_command_register` | — | 初始化成功 |
| `terminated` / `active_request` | `false` / `false` | — | 存活、空闲 |
| `process_id` | `27104` | — | 宿主进程 |

> **结论**：`ready` 成立且**加载身份与当前部署一致**（dll/loader 哈希、协议、资源根全部对齐）。符合第 3 项「ready 要有实时加载身份并与当前部署一致」。
>
> **调用纪律**：该探针**必须串行调用**。首轮并行调用时返回 `readiness=unknown`、`reason=channel_busy`；串行复调即得确定性结果。按工具契约，繁忙/不可达/超时**不代表未注册**。

---

## 2. 两个放样入口（第 4 项，ready 后串行验证）

### 2.1 入口① —— 已有件上 `creo_loft` 直建

| 步骤 | 工具 | job_id | 结果 |
|---|---|---|---|
| 建两张独立 XY 圆草图 | `creo_execute_plan` | `06fbbbd215644d009c160f8f51495795` | ✅ `sk_a`(feat 40, Z=0, R=10)、`sk_b`(feat 49, Z=25, R=6)；rev 0→1；`saved_file_reloaded_and_verified=true` |
| 直建放样 | `creo_loft` | `0a1ea1a752d241d9b88ca70a59acc665` | ✅ 见下表 |

- `model_id`：`5fe0e8d008b945c88059786a1b90600b`（`feat29v_e1`）
- 入参：`sections=["sk_a","sk_b"]`、`label="blend_probe"`、`interpolation="straight"`、`expected_revision=1`

| 断言 | 要求 | 实际 | 判定 |
|---|---|---|---|
| 原生 Blend | 应为原生 Blend | `construction = native_blend_synchronous_selection`；`loft_checks` 源为 Creo native `PRO_FEAT_INFO`，`native_subtype = 混合`（行 `混合曲面 直`） | ✅ |
| 截面数 | 2 | `section_count = 2` | ✅ |
| 体积 | ≈ 5131.26800086（容差 0.01） | **`5131.268000863329`** | ✅ |
| revision | 只推进一次 | 1 → **2** | ✅ |
| 保存重载 | `true` | `saved_file_reloaded_and_verified = true` | ✅ |
| 特征 | — | `BLEND_PROBE`，feature_id **56**，type 917（protrusion） | ✅ |

> 体积解析核对：π·h/3·(R₁²+R₁R₂+R₂²) = π·25/3·(100+60+36) = **5131.268000863** ✓

### 2.2 入口② —— 新件、一次计划内完成草图 + `op=loft`

- 单次调用 `creo_execute_plan`，`model_name = feat29v_e2`，一次计划含 3 个 op
- job_id：`437bf40953ad42e09e60eacacfa1a3f2`；`model_id`：`56aeed3701294d3abaafaaa7e67dbab8`
- 结果：3 个 op 全部 `succeeded`（sketch sk_a、sketch sk_b、loft blend_probe）

| 断言 | 要求 | 实际 | 判定 |
|---|---|---|---|
| 原生 Blend | 原生 | `native_blend_synchronous_selection`；`native_subtype = 混合`（直） | ✅ |
| 体积 | ≈ 5131.26800086 | **`5131.268000863329`** | ✅ |
| revision | 只推进一次 | 0 → **1**（整个计划仅一次） | ✅ |
| 保存重载 | `true` | `true` | ✅ |

> **两个入口均通过。** 两者得到同一体积与同一原生特征语义（`BLEND_PROBE` / feature_id 56 / type 917）。

---

## 3. 多截面 / 追加 / 种子对照（第 5 项）

### 3.1 2 / 3 截面 straight 与 smooth

| 场景 | model_name | job_id | 截面 | 插值 | 体积 (mm³) | 特征 | 侧面类型 |
|---|---|---|---|---|---|---|---|
| 2 截面 straight | `feat29v_e2` | `437bf409…` | 2 | straight | 5131.268000863329 | 混合/直 | ruled (37) |
| 2 截面 smooth | `feat29v_2m` | `b4caae6163a145529d000234a132eb64` | 2 | smooth | **5131.268000863329** | 混合/平滑 | ruled (37) |
| 3 截面 straight | `feat29v_3s` | `dc0da0326af24dfcaeefd0286cb5a030` | 3 | straight | **5131.268000863329** | 混合/直 | ruled (37) |
| 3 截面 smooth | `feat29v_3m` | `4d8864042614404986a2de12b9a21c55` | 3 | smooth | **5130.649365654384** | 混合/平滑 | spline (40) |

- 三截面几何：Z=0/12.5/25，R=10/8/6。
- **smooth 不沿用 straight 的体积公式** → ✅ 3 截面下两者体积不同（5131.26800086 vs 5130.64936565），且侧面几何类型不同（直纹面 37 vs 样条面 40），3 截面 smooth 的包围盒还略微外凸（Z 由 −0.12 到 25.12）。
- **2 截面下 smooth 与 straight 数值相同**（均 5131.26800086，侧面均为直纹面）：仅有两个截面时无中间约束，smooth 退化为同一形状。这是正常几何结论，非公式复用缺陷。
- 四个场景 `revision` 均为 0→1（只推进一次），`saved_file_reloaded_and_verified=true`。

### 3.2 已有底座追加放样

模型 `feat29v_base`，`model_id = 766d6261d72b4bf58c6d85ccfb7133a2`。

| 步骤 | job_id | 结果 |
|---|---|---|
| 建底座（b0/b1 两圆 R=12，Z=0/10 + 放样） | `542af15f6a2743ff9991bffadfe4c5ae` | ✅ rev 0→1；体积 **4523.893421169301**；特征 `BASE_BLEND` (id 56)；侧面为圆柱面(type 36) |
| 追加两张草图（a2: Z=10,R=12；a3: Z=35,R=6） | `a1aa03c66bab420191d78af231d5f91e` | ✅ rev 1→2；底座特征与体积**未变** |
| 在已有件上 `creo_loft` 追加（`expected_revision=2`） | `de3dc8092d7045f09a60bc7c0cabb361` | ✅ rev 2→**3**；新特征 `BLEND_APP` (id 90) |

| 断言 | 要求 | 实际 | 判定 |
|---|---|---|---|
| 总体积 | 底座 + 新增 | **`11121.237993707866`** | ✅ |
| 新增体积 | π·25/3·(144+72+36) = 6597.344572538565 | `11121.237993707866 − 4523.893421169301 = 6597.344572538565` | ✅ 完全吻合 |
| 原有特征身份与几何 | 保持 | `BASE_BLEND` (id 56) 仍在，圆柱面 id 63/65 半径 12 未变 | ✅ |
| revision | 只推进一次 | 2 → **3** | ✅ |
| 保存重载 | `true` | `true` | ✅ |

### 3.3 种子工具对照（不虚填 seed ID）

调用 `creo_new_loft_part`，**只传 `sections` / `label` / `model_name` / `interpolation`**，不传 `seed_file`、不传 `seed_feature_id`，使用其**公开自动选择**能力。

| 项 | 实际值 |
|---|---|
| job_id / model_id | `5091f21ad0f04ecea03994a80c4efc8a` / `e6ad568c48ab48179d578f12ae8f15c8` |
| `construction` | **`native_multisection_blend_seed_rebinding`** |
| op | `loft_seed`，特征 `SEED_BLEND` (id 60) |
| **自动选中的种子** | **`seed_sha256 = 7d2dbeb4f3bea4839b6501e311105753bfc752a0033f72039f8230b6aa61f5f2`**（由工具公开返回，非人工填写） |
| 体积 | **`5131.268000863329`**（与直建一致） |
| 截面数 / 插值 | 2 / straight；`native_subtype = 混合`（直） |
| revision | 0 → 1 |
| 保存重载 | `true` |

> 结论：种子复用路径产生的几何结果与 `creo_loft` 直建**数值一致**，且工具自证了所用种子哈希。

---

## 4. 拒绝、回滚与后续小件（第 6 项，ready 后复验）

### 4.1 三类拒绝（均在模型变更前发生）

| 场景 | 输入 | 实际返回 | 判定 |
|---|---|---|---|
| 重复截面 | `sections=["sk_a","sk_a"]` | `Loft sections must be distinct`（输入校验层 `unique_sections()`） | ✅ 拒绝 |
| 非法模式 | `mode="cut"` | `Direct Blend supports solid add into the default body only; cut, surface and new_body are not accepted` | ✅ 拒绝 |
| 过期版本 | `expected_revision=99` | `Stale revision: current model revision is 2` | ✅ 拒绝 |

**模型与 revision 保持**：三类拒绝之后，用 `expected_revision=2` 的后续操作**被正常接受**（见 4.2），反证 `revision` 仍为 2、模型未被改动。

> 按第 6 项要求：这三处的拒绝发生在**模型变更之前**（输入校验 / 前置校验），因此记为**「模型未变（`model_unchanged`）」**，**不描述成「已执行回滚」**。

### 4.2 断言失败触发真实回滚

- 工具：`creo_execute_plan`，`model_id = 5fe0e8d008b945c88059786a1b90600b`，`expected_revision = 2`
- 入参：计划内新增草图 `rb_sk`（XY, Z=60, 矩形 10×10），`assertions = {"volume_mm3": 1.0}`（必然失败）
- job_id：`1905d097c81642f396b485d052e912ac`

| 项 | 实际 |
|---|---|
| 终态 | `failed` |
| 原始错误 | `message = "Volume assertion failed"`；`failed_stage = verify_model`；`toolkit_code = -1` |
| **回滚** | **`rollback_succeeded = true`** |
| **证据来源** | **`inspection_source = "rollback_verified"`** |
| 回滚后模型 | `RB_SK` 及 `RB_SK_PLANE` 已消失；仅余 `BLEND_PROBE` (id 56)；体积复原为 `5131.268000863329`；`revision` 保持 2 |
| `loft_checks.rollback` | 存在（`blend_56_rollback.txt`，混合/直，2 截面） |

> 这是**真实回滚**（先创建后失败再回退），与 4.1 的「模型未变」是两种不同性质，分别报告。

### 4.3 回滚后后续独立小件

- 工具：`creo_create_plate`（`model_name = feat29v_small`），job_id `ef95a8e0350d4203be78640bfcf33fbf`
- 结果：40×30×10 → **`volume_mm3 = 12000`**（`expected_volume_mm3 = 12000`），`saved_file_reloaded_and_verified = true`
- 结论 ✅：回滚未污染后续作业面，独立新件正常工作。

### 4.4 失败分类（按要求分别报告）

| 类别 | 本轮情况 |
|---|---|
| 新件放样失败 | 本轮无（入口②/多截面均成功）。首轮的 `callback_preflight` 失败见 `…_dev版.md` |
| 已有件放样失败 | 本轮无（入口①/追加均成功） |
| 两个放样入口的失败 | 本轮无。首轮两入口均失败于 `callback_preflight` 且 `model_unchanged=true` |
| 受控拒绝 | 3 例（4.1），均在模型变更前 |
| 受控失败+回滚 | 1 例（4.2），真实回滚并留下 `rollback_verified` |

---

## 5. 作业索引（第 7 项：只提交一次 + 轮询终态）

本轮（ready 后补跑）共 **12 个作业**，全部**单次提交**、轮询 `creo_get_job` 至终态；**无 `unknown_outcome`、无重提、无中途清理**。

| # | 工具 | job_id | 终态 | rev | 体积 (mm³) |
|---|---|---|---|---|---|
| 1 | `creo_execute_plan` | `06fbbbd215644d009c160f8f51495795` | succeeded | 1 | null（纯草图） |
| 2 | `creo_loft` | `0a1ea1a752d241d9b88ca70a59acc665` | succeeded | 2 | 5131.268000863329 |
| 3 | `creo_execute_plan` | `437bf40953ad42e09e60eacacfa1a3f2` | succeeded | 1 | 5131.268000863329 |
| 4 | `creo_execute_plan` | `b4caae6163a145529d000234a132eb64` | succeeded | 1 | 5131.268000863329 |
| 5 | `creo_execute_plan` | `dc0da0326af24dfcaeefd0286cb5a030` | succeeded | 1 | 5131.268000863329 |
| 6 | `creo_execute_plan` | `4d8864042614404986a2de12b9a21c55` | succeeded | 1 | 5130.649365654384 |
| 7 | `creo_execute_plan` | `542af15f6a2743ff9991bffadfe4c5ae` | succeeded | 1 | 4523.893421169301 |
| 8 | `creo_execute_plan` | `a1aa03c66bab420191d78af231d5f91e` | succeeded | 2 | 4523.893421169301 |
| 9 | `creo_loft` | `de3dc8092d7045f09a60bc7c0cabb361` | succeeded | 3 | 11121.237993707866 |
| 10 | `creo_new_loft_part` | `5091f21ad0f04ecea03994a80c4efc8a` | succeeded | 1 | 5131.268000863329 |
| 11 | `creo_execute_plan` | `1905d097c81642f396b485d052e912ac` | **failed**（预期） | 2（保持） | 5131.268000863329（回滚后） |
| 12 | `creo_create_plate` | `ef95a8e0350d4203be78640bfcf33fbf` | succeeded | — | 12000 |

> 另有 3 次**同步拒绝**（4.1），不产生作业。

---

## 6. 并发语义（第 3 项）

**未做真实并行会话调用** → 按要求记为 **「并发未验证」**。首轮曾复现：一个 accepted、另一个 `toolkit_busy`，但仍 `owner_determined=false`、`blocking_job_id=null`（无法指明占用者）。本轮未重测该项。

---

## 7. 逐场景判定（第 8 项）

| 项 | 判定 | 依据摘要 |
|---|---|---|
| 1 | **通过** | `readiness=ready`、`reason=live_identity_verified`，加载哈希/协议/资源根与部署一致 |
| 3 | **通过**（并发除外） | 就绪需实时加载身份且一致已满足；GUI 注册状态如实记 `unknown` |
| 4 | **通过** | 两入口均原生 Blend、体积 5131.26800086、rev 只推进一次、重载已验证 |
| 5 | **通过** | 2/3 截面 straight+smooth、底座追加、种子对照全部达标；smooth≠straight 公式得证 |
| 6 | **通过** | 3 类拒绝 + 真实回滚（`rollback_verified`）+ 后续小件 |
| 7 | **通过** | 12 作业单次提交、轮询终态、无 unknown_outcome |
| 8 | **通过** | 本报告即判定与依据，未验证项如实列出 |

---

## 8. 明确未验证 / 无法确认项（不作推测）

| 项 | 状态 | 说明 |
|---|---|---|
| **第 2 项** 未初始化 / 正式注册并手动启动 / DLL 未变升级 / 真实不同 DLL 升级但旧模块仍加载 / 正常重启并启动同一入口 / 明确不兼容部署 / 回退 / 两安装并存 | **未验证** | 未由发起者准备对应阶段状态，无法逐阶段记录「是否重选/修改注册、手动启动、重启次数及证据来源」 |
| **GUI 注册状态** | **无法确认** | 工具明确声明不可查询（`registration_status=unknown`），如实保留 |
| **真实并行提交 / 占用者识别** | **未验证** | 未做真实并行调用；`owner_determined=false` 限制未变 |
| **两安装并存 / 串用** | **未验证** | 本轮仅 `_Test` 一套连通；未做并存对照 |
| **文件占用 / 预算 / 清理等内部机制** | **不作推测** | 超出公开工具可观察范围 |
| **Creo 10 独立复测** | **未验证** | 非本次门槛 |

---

## 9. 附：本轮（ready 后补跑）新建模型索引

| 模型 | model_id | rev | 体积 (mm³) | 用途 |
|---|---|---|---|---|
| feat29v_e1 | `5fe0e8d008b945c88059786a1b90600b` | 2 | 5131.268000863329 | 入口①直建；拒绝/回滚试验载体 |
| feat29v_e2 | `56aeed3701294d3abaafaaa7e67dbab8` | 1 | 5131.268000863329 | 入口②一次计划内放样 |
| feat29v_2m | `b37a2e4c48684d3a831defc9bfa68da1` | 1 | 5131.268000863329 | 2 截面 smooth |
| feat29v_3s | `8623e853fadc4380acf82c3d9918518b` | 1 | 5131.268000863329 | 3 截面 straight |
| feat29v_3m | `87a83eade04644f69af1b86e74f8cbea` | 1 | 5130.649365654384 | 3 截面 smooth |
| feat29v_base | `766d6261d72b4bf58c6d85ccfb7133a2` | 3 | 11121.237993707866 | 已有底座 + 追加放样 |
| feat29v_seed2 | `e6ad568c48ab48179d578f12ae8f15c8` | 1 | 5131.268000863329 | 种子工具对照（`seed_sha256=7d2dbeb4…`） |
| feat29v_small | （`create_plate` 一次性作业） | — | 12000 | 回滚后独立小件 |

（模型与作业均落地在 `E:\Projects\MCP_CREO_MechDog_Test` 下。）

---

## 10. 结论

**test 版部署 FEAT-029 独立验收：核心门槛全部通过。**

- 前置（工具、路径、注册入口）**全部满足**；`creo_callback_status` 实测 **`ready`**，加载身份与部署**逐项一致**。
- 第 1、3、4、5、6、7、8 项均取得可观察结论并通过；**第 2 项（升级/重启/回退/并存）与真实并发未验证**，GUI 注册状态如实记「无法确认」。
- 首轮的唯一阻断点（常驻回调 `not_loaded`）已由发起者在 Creo「辅助应用程序」中手动启动解决；**无需重新注册 dat**，与提示词「勿要求再次注册」一致。

**本轮无需再向发起者索取额外状态即可结案。** 若后续要补第 2 项与真实并发，需发起者另行准备对应阶段，我可按同样黑盒口径补跑。
