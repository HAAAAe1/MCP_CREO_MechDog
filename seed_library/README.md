# MCP_CREO_MechDog 0.3.1 原生混合种子库

“种子”是带有完整原生 Blend 的简单 Creo PRT 模板。MCP 复制它，再改接到新建的参数草图，保留可编辑的混合特征。
本库现在包含 9 个种子：2、3、4、6 截面的直线和平滑，以及 5 截面的平滑。3/4/6 的六个新增种子已通过实际 MCP 重绑定、尺寸修改、实体截面核对、保存重载和回滚验收。配套源码/清单版本为0.3.1；下列原生实测保留原日期和范围。

| 名称 | 截面数 | 模式 | 原始文件内的混合 ID |
| --- | --- | --- | --- |
| two_straight | 2 | straight | 60 |
| two_smooth | 2 | smooth | 60 |
| five_smooth | 5 | smooth | 93 |
| three_straight | 3 | straight | 71 |
| three_smooth | 3 | smooth | 71 |
| four_straight | 4 | straight | 82 |
| four_smooth | 4 | smooth | 82 |
| six_straight | 6 | straight | 104 |
| six_smooth | 6 | smooth | 104 |

取得0.3.1完整源码即可取得本库；独立种子包适合单独迁移。先在目标 Windows 电脑按源码安装说明配置 Creo、Toolkit SDK、编译器、Python 及可用许可，
再将源码安装生成的 client-config.json 接入支持本地 stdio 的 AI 客户端。
种子文件可以复制到任意本机可读目录；清单中的 ID 只适用于本包原始文件。原文件复制到新路径后，ID 不必重新生成。

在本包目录运行：

```powershell
python .\resolve_seed.py five_smooth
```

程序核对文件 SHA256 并输出本机绝对路径、内部特征 ID、模式和所需截面数。
将 seed_file、seed_feature_id、interpolation 用于 creo_new_loft_part，另提供五张 Z 偏移严格递增的 XY 草图 sections。
required_section_count 仅是提示字段，不是 MCP 工具参数。
也可选择表中的其他名称，提供对应数量的截面。当前源码内附全部种子，`creo_new_loft_part` 省略文件与 ID 时自动匹配。实际创建和修改仍要在目标机验证成功和保存重载。

换同一电脑上的 Agent 时，可共用相同 MCP 安装目录和种子库，分别配置本地启动命令。
当前服务没有远程 HTTP 入口，纯云端 Agent 需要目标 Windows 电脑上的工具执行端。
种子截面数和模式须匹配；不是自动从两截面种子增加到五截面。其他数量与轮廓仍需单独验证。
详细迁移步骤见 [README_迁移说明.md](README_迁移说明.md)，实机摘要位于 validation/。

## 许可

本项目原创测试几何、辅助脚本、清单及说明采用 [MIT](LICENSE)，供其他人使用、修改和再分发。
该授权只适用于项目自身贡献，不赋予 Creo、Toolkit、第三方材料或其他 PTC 软件的授权。
本包没有 Creo 安装程序、SDK 头文件/库、可执行文件或许可证文件；使用者仍需满足自己的 PTC 运行条件。
这些模型是项目自行创建的测试参考件，非 PTC 官方样例库。

## GitHub 发布

此前的 MCP_CREO_MechDog-0.2.4-seed-library.zip 只含原来的 3 个种子，不能代替 v0.2.6 的完整九种子库。
历史发布将 MCP_CREO_MechDog-0.2.4-seed-library.zip 与同名 .zip.sha256 作为 v0.2.4 Release 的独立附件，
与源码 ZIP 同时提供。GitHub 自动生成的 Source code ZIP 不会包含仅作为附件上传的种子库；下载者需同时下载两个包。
v0.2.6 源码内附本库，setup.ps1 自动验证/注册；MCP 可用 creo_list_seeds 查询，creo_new_loft_part 省略 seed_file 和 seed_feature_id 时自动匹配。旧发布包仍按上面的显式参数方式使用。
也可将本目录的内容放到仓库 seed_library/ 下；仓库入口说明应链接到种子库和使用步骤。
