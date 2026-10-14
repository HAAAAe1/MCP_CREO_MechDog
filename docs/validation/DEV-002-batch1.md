# DEV-002 第一批：包目录与路径入口

日期：2026-10-14。第一批已完成，DEV-002 整体继续开发中。版本保持 0.2.6，无新发布。当前分支 `codex/dev-002-python-layout` 基于 FEAT-020 实现提交 da57ab9；既有最终建模验收状态独立保留。

## 本批结果

更新检查实现从根目录迁入 `src/creo_mechdog/update_check.py`，对应测试迁入 `tests/unit/test_update_check.py`。实现规范化内容与 da57ab9 的原文件逐字节一致。根目录已没有 update_check.py 业务实现副本。

新增 `paths.py` 表达代码包、分发资源与运行数据根目录，并将位置提供到 MCP runtime。代码包为 src/creo_mechdog，资源和运行数据默认仍为原安装目录；旧 code_root 字段保留原源码根语义。路径类可独立传入 data_root，但本批没有开放生产运行的数据目录配置，桥接中的旧路径消费者分后续批次迁移。

通过 pyproject.toml 声明标准 editable 包安装，构建后端锁定 setuptools 80.9.0，版本读取根 version.py。setup.ps1 新增包安装和导入检查，requirements-dev.txt 安装同一包；没有新增业务 sys.path 补丁。服务拒绝混用其他源码目录的包，提示重新安装当前源码目录。根 server.py / bridge.py 的客户端和后台入口继续保留，模型、任务和构建仍在原目录。

## 验证

完整环境、命令结果、受测源指纹和原始报告摘要见 [结构化证据](DEV-002-batch1.json)。受测基点提交 `123c30818862d058a6d4d8309b664771217effe4`，dirty=true；统一检查源码 SHA256 为 `ddba31ba9c521fd196fb13e8201fca47d453408242db9f97ad6e0399f6b2cdbe`。环境为 Windows 11 x64 / Python 3.12.14。

| 命令 / 用例 | 实际结果 |
| --- | --- |
| `.venv/Scripts/python.exe -m pip install --no-deps --editable .` | 包构建与本地安装通过；从与源码无关的工作目录正常导入包及唯一 version.py |
| `-m unittest tests.unit.test_paths -v` | 7 项新布局回归通过：实际模块位置、原数据定位、无目录写入、工作目录独立导入、混用副本拒绝、runtime 与分发白名单 |
| `tools/dev_check.py --work-item DEV-002` | 149 项 Windows 单元与语言守卫通过；保留 68 条存量 Ruff / 51 个未格式化文件，不宣称全库严格通过 |
| 安装器受控原生失败回归 | 真实 setup.ps1 包安装、种子验证、根客户端入口及失败后配置保留通过；受控缺少编译器头文件仍在原生构建阶段报错，未被包装成安装成功 |
| `tools/test_update_check.py --network-failure --output build/dev002-mcp.json` | 新的根 server.py / stdio MCP 发现 82 个工具；源码/包/资源/数据身份正确，缓存更新契约和失败分支通过。为开发者注入，未实施真实 OS 断网 |
| `tools/test_update_check.py --output build/dev002-mcp-live.json` | 真实 GitHub 联网及同源缓存快照通过，识别公开 0.2.6 预发布与源码附件 |
| `bridge.py --help` 与后台队列单元 | 根 CLI 入口可用；原桥接后台提交、轮询和登记回归通过，任务及模型目录定位不变 |
| `tools/package.py --output build/DEV-002-batch1-source.zip` | 白名单包含 src 和 tests/unit，排除本机配置、运行数据与 egg-info；源码 ZIP 校验通过 |
| 从全新目录解压，创建全新 venv，安装 requirements-dev.txt，再运行 dev_check.py | 独立包安装、149 项单元与语言守卫通过；受测代码指纹与原目录相同，不借用原目录的 editable 包 |

路径测试首次遇到 Windows 短路径名与规范化长路径名差异，已规范化预期路径后重跑全部检查通过。安装回归文件先独立格式提交（123c308），再修改行为；删除已解决的 I001/F841 与未格式化基线项。基线只更新审查后的两个配置指纹，无新增容许项，没有执行自动重建。

## 后续范围

本批不迁移桥接、原生 C++ 或既有模型，未重跑 Creo 建模；当前 Toolkit 连接问题仍按 BUG-005 / FEAT-020 单独记录，不能由包安装通过推导原生成功。本机验收分工保持 Creo 12，Creo 10 由其他机器协助者负责。

下一批先处理依赖清晰的轮廓、翼型及输入校验模块；服务、启动和桥接实现随后迁移，每批核对兼容根入口、资源/数据消费者、后台子进程、安装和解压源码。剩余根单元及 tools 下实机测试再分别归档，不把第一批完成写成 DEV-002 全部完成。

标准安装方式依据 [setuptools editable 安装说明](https://setuptools.pypa.io/en/latest/userguide/development_mode.html)。完整源码目录仍是部署单位；本批没有提供包含种子、原生执行器与 SDK 的独立 wheel 部署。
