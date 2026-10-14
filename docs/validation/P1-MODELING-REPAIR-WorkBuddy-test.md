# P1联合修复：最终公开MCP验收提示词

只使用已连接MCP公开工具和Creo实际结果。不查看、分析或修改源码，不执行本地脚本/单元测试，不检查Git、本机配置或内部日志。先由测试发起者部署本次E盘分支、重启开发连接器；回调在当前Creo会话已注册启动。版本仍0.3.0，版本号不能单独证明本次修复部署。

## 环境与保护

通过公开接口确认runtime.code_root=E:/Projects/MCP_CREO_MechDog、source_changed_since_startup=false、Toolkit connected=true。确认list_models/inspect_model有detail、cursor、section等新参数；缺少新参数时报告未部署，不执行建模。Creo完整版本/构建身份等接口未提供的信息记无法确认。注册文件存在不代表回调已加载，以实际原生放样结果判断。

全部新建独立p1_test_*模型。每次修改只提交一次，轮询同一job_id到终态；成功检查saved_file_reloaded_and_verified=true和revision仅推进一次。遇unknown_outcome、提交/轮询响应丢失停止新写操作，不重交、不清pending_job、不终止进程。全部串行，不声称并发通过。

## 六项场景

1. **BUG-028引用**：XY圆sk_a(R10,Z0)、sk_b(R6,Z25)。各用独立模型测试标签、inspect实际整数ID、纯数字字符串、整数/标签混合；分别用creo_loft与execute_plan的loft步骤。模式straight、add、new_body=false。体积4900π/3≈5131.26800086，bbox[-10,-10,0]..[10,10,25]，原草图ID保留，原生Blend两截面straight及重载通过。整数与同值字符串重复时应拒绝且不改变模型。
2. **BUG-021编辑**：矩形min[0,0]/max[60,40]，depth=10，体积24000。查询实际深度尺寸，改为12→28800。设置参数SIZE=14并关系“实际尺寸符号=SIZE”→33600；SIZE=15→36000。直接改关系控制尺寸应明确提示改驱动参数/关系，回滚、revision和实时模型不变；随后SIZE=16→38400。含放样模型另做自由尺寸与关系驱动对照，查询其实际维度并记录几何；不要使用无放样模型的解析体积套用联合实体。
3. **BUG-022孔**：同60×40×10矩形件，顶面Z10，X/Y基准面线性参考、offset1=30/offset2=20、直径8。通孔体积24000−160π；独立盲孔depth=5，体积24000−80π。再用实际查询的两条顶面直边作参考。中心对称底板min[-30,-20]/max[30,20]验证零偏置通孔。把reference2设为Z基准面时应明确拒绝与放置面平行的定位约束，并恢复模型。
4. **BUG-017筋**：XY底板min[0,0]/max[60,40]、depth15；XZ竖壁矩形min[0,15]/max[60,45]、depth10、direction=negative；YZ@x30开放线[10,40]→[40,10]。thickness4、symmetric、flip=false，体积54000→55250。反向端点并flip=true应形成同一合法筋；positive/negative厚度侧另测。验证原生rib类型、特征健康、重载。闭合底板草图作rib应明确拒绝open profile；不相交剖面失败后核对回滚。
5. **BUG-014真实结果**：上述失败后同时查询get_job compact/full、inspect摘要/详情与refresh实况，核对恢复后体积、特征ID、revision和计数。缺失数据为未知/null，不能全0冒充成功恢复。另建空件及create_plate检查实际可核实计数；plate不要求模型注册，未取得的面/边/总特征数应明确未知。
6. **BUG-013分页**：list_models默认摘要；inspect默认摘要不附完整几何。detail=full支持section筛选；返回next_cursor时保持原查询继续读取，记录complete/unavailable_sections。检查摘要计数、体积与详情一致。分页期间修改模型后旧cursor应拒绝，要求重新查询。对足够大的独立测试模型验证预算导致分页；客户端无法测量字节时只报告实际可读和分页行为，32KiB内部预算记未验证。单条超预算应明确提示，不能静默声称完整。

## 报告要求

按BUG编号分别给通过/失败/未验证；记录工具、原始输入、job_id/model_id、终态/耗时、几何/参数、保存重载、revision、回滚与原始错误。报告只写实际做过的分支，不用开发者报告代替本次调用。

Creo10原报告的完整原始失败模型未在本机复现；在Creo10协助环境补测基准面孔、d13孔位30→40、独立关系D13=40及原复杂模型依赖链。ID/符号从实际模型读取，不能凭示例猜测；失败保留最早原生调用/特征诊断，不将日志出现Blend检查直接判为错误分派。
