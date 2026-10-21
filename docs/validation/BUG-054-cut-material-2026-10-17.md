# BUG-054 / DEV-033 切除材料变化核实、修复与实机验收记录

日期：2026-10-17（Asia/Shanghai）。执行分支 `codex/bug-054-feedback033`，基线提交 `7662f7e3c9bc11331fa32ed4bad8cf12a0d80212`（0.3.4 主干），本轮变更 dirty，须结合下方源码指纹判断。工作目录 `E:\Projects\MCP_CREO_MechDog`。

## 环境

Windows 11 x64 / Python 3.12.14（`.venv`）/ Creo 12.4.0.0（会话探测 release_numeric=44）/ 本机匹配 Toolkit SDK / MSVC x64。MCP stdio 服务为 E 盘 `server.py`（本机开发联调约定 `MCP_CREO_MechDog_dev`）。会话恢复条件：BUG-001 根因核对材料（C 盘旧副本已禁用停服、仅剩 E 盘服务）+ 2026-10-17T08:35Z 实时只读探测 `connected=true, toolkit_code=0, 通道空闲` 后，按 DEV-033 约定恢复实机。

## 受测源码指纹（SHA256 前 16 位，dirty）

| 文件 | 指纹 |
| --- | --- |
| native/generic.cpp | 4dc5bcdaa713af45 |
| server.py | 94bd5104d27f11bc |
| bridge.py | ad32d68241f834ac |
| tools/test_cut_material.py | 570eea212f024b15 |
| tests/unit/test_cut_material.py | 3634c5338905fdf2 |

执行器由 `bridge.py build` 从上述 native 源编译（复用/重建均指向当前 build 产物）。

## G0 源码核对结论

`native/generic.cpp` 的 `extrude_or_revolve` 为 extrude/revolve 共享创建路径，创建特征后仅做 body 清理，无材料测量；孔类 `generic_hole`（BUG-022）已有 `material_removed_mm3` 与零去料拒绝先例。`v0.3.3..HEAD` 对该函数零改动，外部 0.3.3 报告行为预期在 0.3.4 重现。

## G1 当前版本复现（修复前）

模型 `bug054_g1_mcp`（8cc35bcba9024ce4b1464a47596f83d5）：60×40×10 板 + (−10,0) Ø8 通孔，基线 revision=5、体积 `23497.34517542563`（解析 24000−160π 一致）。提交 BUG-054 原样板外切除（圆心 (100,100)、R5、深 10、positive）：

- 草图作业 `106bf4ed4fef4b2389c02c240223357a` succeeded（revision 5→6）
- 切除作业 `7408f4629ae04a0fb178c00375ac8c4a` **succeeded**、`General feature plan completed`，体积不变，revision 6→7，操作明细无零去料提示

**复现成立**：与外部 0.3.3/Creo 10 报告现象一致。证据 [bug054_g1_repro.json](bug-054-cut-material-2026-10-17/bug054_g1_repro.json)、[bug054_g1_cut.json](bug-054-cut-material-2026-10-17/bug054_g1_cut.json)。

## G2 结果契约

与孔类（BUG-022）一致的可识别失败契约：

1. `mode="cut"` 的 extrude/revolve 在创建前后测量实体体积；`removed ≤ max(1e-9, |before|×1e-12)` 时抛 `Extrude/Revolve cut removes no material; check the sketch position, direction and depth against existing geometry`，走既有失败路径：回滚到作业前保存检查点、`rollback_succeeded=true`、模型保持 ready、**revision 不递增**、别名无残留。
2. 有效去料：作业 succeeded，操作明细含 `material_removed_mm3`，revision 按既有规则推进一次。
3. 体积测量不可取得（Toolkit 调用失败）：原生异常路径，不伪填 0，不清保护。
4. `add` / `surface` 语义不变；thin cut 同属 cut 守卫。
5. `creo_get_job detail=compact` 的操作白名单加入 `material_removed_mm3`（bridge.py），轮询即可观察去料量；孔类字段同步受益。

## G3 实现与离线回归

- `native/generic.cpp` `extrude_or_revolve`：签名改为返回明细；cut 分支创建后再生、测量并执行守卫，成功写入 `material_removed_mm3`；日志行 `CUT_MATERIAL_REMOVED_MM3`。
- `server.py`：`creo_extrude` / `creo_revolve` 工具说明同步契约。
- `bridge.py`：compact 操作白名单补 `material_removed_mm3`。
- `tests/unit/test_cut_material.py`（新增 4 项）：零去料失败回滚且 revision/检查点保持、成功上报去料量、测量失败不伪填零且不保持 ready、add 不携带去料字段。
- `python tools/dev_check.py --work-item DEV-033`：全量单元通过、无新增风格回归（[development_check.json](bug-054-cut-material-2026-10-17/development_check.json)）。

## G4 实机验收（tools/test_cut_material.py，[cut_material_test.json](bug-054-cut-material-2026-10-17/cut_material_test.json)）

逐场景隔离模型，基准板 60×40×10（x=−30..30、y=−20..20、z=0..10）。体积断言独立解析计算，容差 0.01 mm³；Creo 数值积分偏差实测 ≤5×10⁻⁴ mm³。

| 场景 | 结果 |
| --- | --- |
| T01 有效切除 (15,0) Ø4 深 10 | succeeded；去料 `125.66370614359`（=40π）；终体积 `23371.68146928204`（=24000−200π）；保存重载 true；revision +1 |
| T02 板外 (100,100) R5 深 10（单计划） | failed，`Extrude cut removes no material…`；rollback_succeeded true；体积 `23497.34517542563` 不变；revision 2→2；别名无 sk_out/cut_out；失败后同模型有效切除仍成功 |
| T03 已去除区域重复切除 | failed 同一契约；revision 不变 |
| T04a 相切零交 (35,0) R5 | failed（零去料，契约内拒绝） |
| T04b 小量有效 (34,0) R5 | succeeded；去料 `40.87532603546`（解析 `10×(25·acos0.8−12)=40.87527720`）；终体积吻合，未被误拒 |
| T05 多操作计划（有效切除→板外切除） | 第 4 操作失败（index 3）；整计划回滚；体积回 24000、revision 恢复、无半成品别名；随后有效编辑成功 |
| T06 未知/拒绝边界 | 离线单元覆盖：测量失败、回滚、revision、add/surface 分支（见 G3） |
| T07 旧行为回归 | 有效孔 succeeded 去料 160π；板外孔 `Hole removes no material` failed（BUG-022 守卫不退化）；add succeeded 无去料字段、体积 +125；surface succeeded 体积不变 |
| T08a revolve 有效切除（XZ 草图 + 中心线，绕板底面轴线） | succeeded；去料 `94.24787972091`（轴在 z=0 板底面，仅上半环与板相交，解析 30π）；终体积 `23905.752120279092` 吻合 |
| T08b revolve 无交集对照 | failed，`Revolve cut removes no material…` 同一契约 |

原生日志证据：成功作业 `CUT_MATERIAL_REMOVED_MM3=125.663706143594 / 40.875326035461 / 94.247879720908`；零去料作业 `CUT_MATERIAL_REMOVED_MM3=0.000000000000` + `BUILD_FAILED=Extrude/Revolve cut removes no material…`。

## 未测范围

WorkBuddy 公开 MCP 黑盒验收未执行（交接见 [BUG-054-WorkBuddy-test.md](BUG-054-WorkBuddy-test.md)）。外部 Creo 10 / 0.3.3 环境未复测；本机无 Creo 9 SDK，Creo 9 编译与运行时未验收。thin cut、装配内 cut、钣金 cut 未单独实测（实现与实体 cut 同一守卫路径）。BUG-016（solidify side/引用）不因本轮关闭。
