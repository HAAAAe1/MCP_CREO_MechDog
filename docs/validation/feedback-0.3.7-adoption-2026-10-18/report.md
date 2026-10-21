# 反馈：现有模型无法纳管（2026-10-18 · creo · v0.3.7 · 现有模型无法纳管）

> 反馈对象：MCP_CREO_MechDog v0.3.7
> Creo 版本：Creo 13.4.1.0（release_numeric 45），Windows
> 场景：用户在 Creo 中手动新建 001.PRT 并拉伸一个长方体后，要求 AI 通过 MCP 对其执行壳（Shell）特征。

---

## 一、核心问题（一句话）

**插件只能操作"本服务创建并登记"的模型，没有提供任何接口把用户手动创建/打开的现有模型纳入管理，导致会话中已存在的模型对 Agent 完全不可见、不可操作。**

用户视角的表现：明明 Creo 连接正常（`creo_session_status` 能看到 current_model="001"），但 `creo_list_models` 只列出插件自己创建的模型，所有变更类工具都要求 model_id，而 001.PRT 没有对应的 model_id，于是：

```
Unknown model_id; use creo_new_part or creo_execute_plan
```

用户被迫选择"放弃现场模型、由 AI 重建一个新零件"——这违背了"接管用户当前工作"的核心使用预期，也是本次反馈希望作者优化的主要方向。

---

## 二、过程中发现的逐项问题

### 问题 1（核心）：缺少现有模型纳管（adopt）接口

- `README.md` 明确声明："持续修改只支持本服务创建、登记的零件……未提供直接接管用户现有模型的接口。"
- 全部 mutation 工具的入口校验在 `generic_bridge.model_info()`：`models/<model_id>/model.json` 不存在即拒绝；没有从会话模型反查/登记的路径。
- **影响**：用户手工建模的任何进度都无法被 AI 续作，只能推倒重建。

### 问题 2：会话内"未保存"模型无法走任何登记路径

- 001.PRT 是新建后从未存盘的模型，磁盘上没有 .prt 文件。
- 原生侧对已有模型有硬性前置：`if (checkpoint.empty() && !readonly) throw "model_reconciliation_required: refusing to adopt a checkpointless session model"`（`native/generic.cpp`）。
- 即使是只读作业（如 `creo_refresh_model`）也无法作用于未保存的会话模型：`ProMdlOriginGet` 对未保存模型返回空来源，随后的 output 目录前缀校验必然失败。
- **影响**：纳管必须以"用户先把文件保存到指定目录"为前提，Agent 无法主动落盘收编（其实原生侧已有 `ProMdlnameBackup(board, destination)` 能力，见第四节建议 2）。

### 问题 3：output 目录前缀校验对只读作业也无条件生效

`native/generic.cpp`（非新建模型分支）：

```cpp
CK(ProMdlOriginGet(board, origin));
std::wstring actual = origin, prefix = folder + L"\\";
if (_wcsnicmp(actual.c_str(), prefix.c_str(), prefix.size()))
    throw std::runtime_error("Loaded model origin does not match this MCP model's output directory");
```

- 该校验不区分 `request["readonly"]`，导致即使模型已通过复制方式登记，只要会话中存在同名模型且来源路径不同（比如用户自己的工作目录），**连只读的 inspect/refresh 都会失败**。
- **影响**：复制纳管模式（copy adopt）下，用户必须先在 Creo 中"拭除"会话模型才能进行任何操作，多一步纯手动的仪式性操作，且报错信息对最终用户不够可操作。

### 问题 4：MODEL_NAME 规则与 Creo 真实命名规则不一致

- `bridge.MODEL_NAME = re.compile(r"[a-z][a-z0-9_]{0,30}\Z")`，要求小写字母开头。
- Creo 本体允许数字开头的模型名（如 `001`、`2026_box`），中文用户大量使用纯数字命名。
- 本次 001.PRT 若直接套用新建模型的名称校验会被拒，纳管实现不得不另用 `[A-Za-z0-9_]{1,31}` 规则。
- **影响**：纳管/查询类功能若复用 MODEL_NAME 将系统性漏掉数字开头的模型名。

### 问题 5：缺少"会话模型枚举"能力

- 插件无法列出当前 Creo 会话中除纳管模型外的其他模型（名称、类型、来源路径、是否已保存）。
- Agent 只能靠用户截图（模型树/标题栏）或全盘搜索 `*.prt` 来确认"会话里有什么、文件在哪"。
- **影响**：发现能力缺失放大了问题 1——即使未来有 adopt 接口，没有会话枚举，Agent 也难以自动定位目标模型与文件。

### 问题 6（次要）：无热重载，新增工具需要重启连接器

- `server.py` 启动时固化源码指纹，改动后仅 `creo_callback_status` 提示 `source_changed_since_startup`，新工具不重启不生效。
- 属于合理的安全设计，但建议在文档中明示"修改/扩展插件后需重启 MCP 连接器"，本次实测首次会遇到困惑。

---

## 三、本次为解锁任务所做的临时改动（供参考/合并）

在 v0.3.7 源码上做了最小侵入式修改，未触碰原生 C++ 与作业管线：

1. **`generic_bridge.py` 新增 `adopt_model(model_name, source_file=None, model_id=None)`**：
   - 名称规则 `[A-Za-z0-9_]{1,31}`（与 Creo 一致），查重后生成/复用 model_id；
   - 原地纳管（`source_file` 省略）：要求 `<name>.prt.N` 已存在于纳管 output 目录（推荐：用户把会话模型直接保存到该目录，来源前缀天然匹配，后续作业无缝作用于会话内模型）；
   - 复制纳管（`source_file` 给定）：把用户文件**复制**为基线，源文件永不修改；
   - 写入标准 model.json（revision=0、part_sha256 基线、`adopted` 溯源字段），完全复用既有 `validate_baseline`/恢复机制。
2. **`server.py` 新增 `creo_adopt_model` MCP 工具**（CREATE 注解），并更新 README 对应声明。

实测：纳管后 `creo_refresh_model` / `creo_execute_plan`(shell) 与原生创建模型行为一致。

---

## 四、给作者的优化建议（按收益排序）

1. **官方化 adopt 接口**：把上述"原地纳管/复制纳管"收进官方 API，并在 `creo_list_models` 中以 `adopted: true` 标记来源。
2. **未保存模型的一键收编**：会话模型无落盘文件时，可在原生侧先 `ProMdlnameBackup(board, output_directory)` 落盘再登记（该 API 已在恢复路径中使用），把"用户手动保存"这一步也省掉；注意处理备份后 origin 变更与重名冲突。
3. **放宽 origin 前缀校验**：至少对 `readonly` 作业放行外源会话模型；mutation 场景可改为"发现外源同名模型 → 自动 Backup 进 output 目录 → 以备份件为 checkpoint 继续"，替代当前的硬失败。
4. **会话枚举工具**（如 `creo_list_session_models`）：返回会话内全部模型的 name/type/origin/saved 状态，作为 adopt 的发现前提。
5. **统一模型名规则**：纳管/查询路径采用 Creo 真实命名规则（数字开头合法），MODEL_NAME 仅约束"AI 新建"命名。
6. **文档补充**：说明扩展插件后需重启连接器生效，以及 adopt 模式各自的适用前提（原地 vs 复制+拭除）。

---

*以上问题均基于 2026-10-18 对 v0.3.7 源码（server.py / generic_bridge.py / native/generic.cpp）的实际走读与现场复现，可直接用于回归定位。*
