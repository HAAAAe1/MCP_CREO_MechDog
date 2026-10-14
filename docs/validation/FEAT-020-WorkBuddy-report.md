# MCP_CREO_MechDog FEAT-020 验收报告 —— 版本检查与提醒

- 验收方式：仅通过已连接 MCP 的公开工具调用验收；未查看/分析/修改源码，未运行本地脚本、单元测试或开发检查。
- 验收时间（UTC）：2026-10-14 03:27–03:30（本地 GMT+8 11:27–11:30）
- 验收机：Windows（win32），Creo 12 本机执行；Creo 10 由协助者在其他机器执行（本机无法核验，单独保留范围）。
- 结论口径：`通过` / `失败` / `未验证` / `无法确认` 四种，逐项给出，不做推断。

## 0. 结论汇总

| # | 验收项 | 结论 |
|---|--------|------|
| 0 | 服务版本、可见工具、Creo 环境 | **通过**（构建身份**无法确认**） |
| 1 | `creo_check_update(force=true)` 字段完整性；默认/能力/启动同缓存时刻一致性 | **通过** |
| 2 | 公开发布数据场景（更高版本 / 相同或更高不降级 / 预发布标识） | **部分通过、部分未验证** |
| 3 | GitHub 网络不可用 / 超时 / 限流 | **未验证**（场景未实施） |
| 4 | 网络失败期间更新检查与建模不受阻 | **未验证**（网络失败前提缺失）；建模路径单独观测=**成功** |
| 5 | 并发调用更新检查 + 能力/启动状态 | **通过**（有并发证据） |
| 6 | `update_available && stale=false` 时向用户转述 | **未触发**（未出现 update_available） |

## 1. 第 0 项：服务版本、可见工具与 Creo 环境（通过）

工具名：`creo_check_environment`、`creo_capabilities`、`creo_startup_status`、`creo_session_status`。

- `creo_check_update` **存在**；`creo_capabilities` 返回 `tool_count: 82`、`enabled_tool_count: 82`、`disabled_tools_hidden: true`、`unavailable_tools: []`。可见工具列表实际计数为 **82**，与要求一致。
- 服务身份：`name = "MCP_CREO_MechDog"`，`version = "0.2.6"`。
- 公开 runtime（来自 `creo_capabilities.runtime`，非源码查看）：
  - `code_root = E:\Projects\MCP_CREO_MechDog`
  - `server_entry = E:\Projects\MCP_CREO_MechDog\server.py`
  - `python_executable = E:\Projects\MCP_CREO_MechDog\.venv\Scripts\python.exe`
  - `source_changed_since_startup = false`（含 `server.py`/`bridge.py`/`update_check.py`/`version.py` 等启动指纹）
- 环境（`creo_check_environment`）：`platform=win32`，`creo_root = C:\Program Files\PTC\Creo 12.4.0.0`，`transport=stdio`，`ready_to_build=true`，`license_setting_present=true`，`license_diagnostics.source=environment / fallback_used=false / warnings=[]`，`license_usable=unverified_here`。**本机 Creo 实际版本：12.4.0.0**（`creo_session_status.native.release_numeric=44`）。
- `creo_capabilities` 与 `creo_startup_status` 均包含 `update` 字段（见第 1 项）。
- **构建身份（git commit/sha/build id）：无法确认。** 公开接口只提供 `version=0.2.6` 与源码指纹，未提供 git 提交/构建号；按要求记为「无法确认」，不读取配置/Git/仓库补齐。
- 「已部署」判定依据：并非仅凭版本号，而是 `creo_check_update` 工具存在 + `capabilities.update` / `startup_status.update` 字段存在且有实际检查结果。
- Creo 10 范围：本机无 Creo 10 实例，**本机无法核验**；如协助者已在其机器执行，应另行记录其实际版本。

## 2. 第 1 项：强制检查与字段一致性（通过）

### 2.1 `creo_check_update(force=true)` 原始返回（保留完整）

```json
{
  "status": "up_to_date",
  "current_version": "0.2.6",
  "latest_version": "0.2.6",
  "is_prerelease": true,
  "release_url": "https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.2.6",
  "download_url": "https://github.com/wudahua/MCP_CREO_MechDog/releases/download/v0.2.6/MCP_CREO_MechDog-0.2.6-source.zip",
  "checked_at": "2026-10-14T03:28:05.870189+00:00",
  "last_success_at": "2026-10-14T03:28:05.870189+00:00",
  "message": "当前版本已是最高可比较的公开版本。",
  "error": null,
  "from_cache": false,
  "stale": false
}
```

字段核对：

| 字段 | 值 |
|------|-----|
| current_version | 0.2.6 |
| latest_version | 0.2.6 |
| is_prerelease（预发布标记） | true |
| release_url（官方入口 1） | https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.2.6 |
| download_url（官方入口 2） | https://github.com/wudahua/MCP_CREO_MechDog/releases/download/v0.2.6/MCP_CREO_MechDog-0.2.6-source.zip |
| 时间 | checked_at = last_success_at = 2026-10-14T03:28:05.870189+00:00 |
| 缓存来源 | from_cache = false（本次为真实刷新） |
| 过期标记 | stale = false |
| 错误信息 | error = null |

### 2.2 默认检查 / 能力 / 启动在**同一缓存时刻**的一致性

在刷新完成后的同一缓存时刻并发调用三条默认检查 + `creo_startup_status` + `creo_capabilities`，`update` 字段完全一致：

- 三条 `creo_check_update`（默认，无 force）与 `creo_startup_status.update`、`creo_capabilities.update` 均为：
  `status=up_to_date`，`checked_at=last_success_at=2026-10-14T03:28:05.870189+00:00`，`from_cache=true`，`stale=false`，`error=null`，`message="当前版本已是最高可比较的公开版本。"`，版本/入口字段同 2.1。

### 2.3 正在刷新时（status=checking）启动/能力查询及时返回

在一次强制刷新在途时调用 `creo_startup_status`，其 `update` 返回：

```json
{
  "status": "checking",
  "current_version": "0.2.6",
  "latest_version": "0.2.6",
  "is_prerelease": true,
  "release_url": "https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.2.6",
  "download_url": "https://github.com/wudahua/MCP_CREO_MechDog/releases/download/v0.2.6/MCP_CREO_MechDog-0.2.6-source.zip",
  "checked_at": "2026-10-14T03:28:05.870189+00:00",
  "last_success_at": "2026-10-14T03:28:05.870189+00:00",
  "message": "正在检查更新；已有版本信息来自缓存。",
  "error": null,
  "from_cache": true,
  "stale": false
}
```

即 `status=checking`（允许），且 `creo_startup_status` 未等待刷新完成即返回；同批的其它工具亦及时返回。符合要求。

### 2.4 启动状态说明

首次读取 `creo_startup_status` 时返回 `state="configuration_error"`（`message="Startup preparation failed (TimeoutExpired)"`，`launch_attempt=5`，`retry_allowed=true`，`updated_at=03:27:45`）；随后读取即变为 `state="ready"`、`connected=true`、`message="Toolkit connection verified"`、`updated_at=03:27:56`。`creo_session_status` 同步显示 `connected=true`、`startup.state=ready`。最终启动状态为 **ready**。（首次的 configuration_error 为启动过程瞬态，未影响后续工具返回。）

## 3. 第 2 项：公开发布数据场景（部分通过 / 部分未验证）

- **相同或更高版本不建议降级：通过（仅观测到「相同」子情形）**。当前 `current_version == latest_version == 0.2.6`，返回 `status=up_to_date`，`message="当前版本已是最高可比较的公开版本。"`，未建议降级。**「本地版本更高」子情形未观测**。
- **最高公开版本为预发布时仍能发现并标识：通过**。`latest_version=0.2.6` 且 `is_prerelease=true`，即最高公开版本被识别并标记为预发布。
- **公开版本高于当前版本 → update_available + 两个官方入口 + 手动升级说明：未验证**。发起者未提供「公开版本高于当前」的发布数据，WorkBuddy 不修改版本或发布数据，故该场景**未验证**；不能宣称已通过。
- 无更高可比较候选时返回 `up_to_date`；本环境**未出现**可返回 `unknown` 的候选缺失情形，故 `unknown` 分支**未验证**。

## 4. 第 3 项：GitHub 网络不可用 / 超时 / 限流（未验证）

- 发起者未准备 GitHub 网络不可用 / 超时 / 限流条件；本环境 GitHub 可达（多次 `force=true` 均 `from_cache=false` 成功刷新，见 2.1、6.1）。
- 因此**未能观测** `failed`/`unknown` 终态，也未能观测「保留上次成功目标 + `stale=true` + 本次 `error`」的表现，亦无法记录失败冷却期内 `force=true` 返回缓存失败结果的实际情形。
- 结论：**未验证**。未推断内部重试次数或缓存时长。

## 5. 第 4 项：网络失败期间的状态查询与建模（未验证；建模路径单独观测成功）

- 前提条件（网络失败）**未实施**，故本项**未验证**。
- 网络失败期间查询能力与启动状态：**未实施**（无网络失败条件）。
- 作为补充证据（**非在断网条件下执行**），在启动 `state=ready` 后调用了 `creo_create_plate(length=20, width=10, thickness=2)`，**仅提交一次**，未指定已有名称，随后轮询同一 `job_id`（未重复提交）：

  - 提交返回：`job_id=563ee955f3e7454eae708824dc8aed0b`，`status=queued`，`model_name=ai_plate_563ee955f3e7`，`created_at=2026-10-14T03:29:09.780347+00:00`
  - 轮询过程：`running / creating_native_features` → `running / verify_saved_file` → `succeeded / verified`
  - 终态（`creo_get_job`，`detail=compact`）：

```json
{
  "job_id": "563ee955f3e7454eae708824dc8aed0b",
  "status": "succeeded",
  "stage": "verified",
  "created_at": "2026-10-14T03:29:09.780347+00:00",
  "started_at": "2026-10-14T03:29:09.938372+00:00",
  "finished_at": "2026-10-14T03:29:18.308843+00:00",
  "message": "Native PRT saved, reloaded and verified; sketch/extrude/round/hole features are editable",
  "result": {
    "success": true,
    "toolkit_code": 0,
    "part_file": "E:\\Projects\\MCP_CREO_MechDog\\jobs\\563ee955f3e7454eae708824dc8aed0b\\output\\ai_plate_563ee955f3e7.prt.2",
    "sha256": "4fa89be3a95e4b0a159777dc9571c94615f9a272742c71f540771eb1e52384ad",
    "saved_file_reloaded_and_verified": true,
    "preview_file": "E:\\Projects\\MCP_CREO_MechDog\\jobs\\563ee955f3e7454eae708824dc8aed0b\\output\\preview.jpg",
    "connected": true,
    "volume_mm3": 400,
    "expected_volume_mm3": 400,
    "extrude_count": 1,
    "round_count": 0,
    "hole_count": 0
  }
}
```

  - 核对：`status=succeeded` ✔；体积 `volume_mm3=400`、`expected_volume_mm3=400` ✔（约 400 mm³）；`saved_file_reloaded_and_verified=true` ✔。
  - 几何/特征：拉伸 1（extrude_count=1）、圆角 0、孔 0。
  - 保存文件信息：`ai_plate_563ee955f3e7.prt.2`（文件版本后缀 `.prt.2`），sha256 见上，另有 `preview.jpg`。
  - 会话：`connected=true`，`current_model=▩AI_PLATE_563EE955F0001`，`current_model_code=0`。
  - **model_id：无法确认**。`creo_get_job` 未返回 `model_id`；`creo_list_models`（多次查询）8 条记录均为 2026-10-13 及更早、**未包含**本新零件；`creo_inspect_model` 以名称与 `job_id` 查询均被拒（`Invalid model_id` / `Unknown model_id`）。
  - **revision：无法确认**（注册表 revision 不可得）；仅保存文件版本后缀为 `.prt.2`。

- 未关闭现有 Creo，未重复提交未知结果任务。

## 6. 第 5 项：并发（通过）

方法：在同一条消息中**真正并行**发出多次 `creo_check_update(force=true)` 及 `creo_startup_status`，保留每次输入与返回时间。

### 6.1 并行强制刷新（3 次，同一批）

三次 `creo_check_update(force=true)`（同批并行发出）返回：

```json
{"status":"up_to_date","current_version":"0.2.6","latest_version":"0.2.6","is_prerelease":true,
 "release_url":"https://github.com/wudahua/MCP_CREO_MechDog/releases/tag/v0.2.6",
 "download_url":"https://github.com/wudahua/MCP_CREO_MechDog/releases/download/v0.2.6/MCP_CREO_MechDog-0.2.6-source.zip",
 "checked_at":"2026-10-14T03:28:51.380380+00:00","last_success_at":"2026-10-14T03:28:51.380380+00:00",
 "message":"当前版本已是最高可比较的公开版本。","error":null,"from_cache":false,"stale":false}
```

- 三次返回的 `checked_at` 完全相同（均为 `03:28:51.380380`）且 `from_cache=false`。若为串行，每次 `force` 会各自刷新而产生不同 `checked_at`；三者一致表明**共享同一次刷新请求**，即并发被服务端合并处理。
- 同批并行的 `creo_startup_status` 在刷新在途时立即返回 `state=ready` 与 `update.status=checking`（未阻塞等待）。
- 结论：**并发通过**（有实际并行调用与共享请求的可观测证据，非由工具列表或串行结果推断）。

## 7. 第 6 项：用户提醒转述（未触发）

- 触发条件为 `update_available && stale=false`。本次全程 `status=up_to_date`，**未出现** `update_available`，故提醒**未触发**，也未向用户发送版本/下载链接/手动升级流程转述。
- 「同一会话对同一 `latest_version` 不重复提醒」本条在无触发前提下**无法验证**。
- 未执行下载、安装、关闭 Creo 或中断建模等动作。

## 8. 未实施 / 未验证场景清单（明确列出，不推断通过）

1. 公开版本**高于**当前版本（`update_available` + 两个官方入口 + 手动升级说明）——发起者未提供发布数据。
2. 本地版本**高于**公开版本（不建议降级）——仅观测到「相同」情形。
3. GitHub **网络不可用 / 超时 / 限流**：`failed`/`unknown` 终态、`stale=true` 保留上次目标、失败冷却期内 `force` 行为——场景未实施。
4. **网络失败期间**建模不受阻——网络失败前提缺失（建模已在联网条件下单独观测成功）。
5. 无更高可比较候选时返回 `unknown`——本环境存在可比较候选。
6. `update_available` 条件下的用户提醒转述——触发条件未满足。
7. Creo **10** 环境下的本项验收——由协助者在其他机器执行，本机无法核验。

## 9. 关键事实留存

- 服务：MCP_CREO_MechDog `0.2.6`，工具 82/82，`code_root=E:\Projects\MCP_CREO_MechDog`，`source_changed_since_startup=false`；构建身份**无法确认**。
- Creo（本机）：`12.4.0.0`，`release_numeric=44`，会话 `connected=true`，启动 `state=ready`。
- 更新检查：`current=latest=0.2.6`，`is_prerelease=true`，`status=up_to_date`，`stale=false`，官方入口见 2.1。
- 建模（联网条件下）：`job_id=563ee955f3e7454eae708824dc8aed0b`，`model_name=ai_plate_563ee955f3e7`，同批仅提交一次、轮询至 `succeeded/verified`，体积 400 mm³，`saved_file_reloaded_and_verified=true`，保存文件 `ai_plate_563ee955f3e7.prt.2`；`model_id`/`revision` 无法确认。
