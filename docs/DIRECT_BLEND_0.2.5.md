# 直接创建和追加原生 Blend

`creo_loft` 和计划中的 `loft` 从独立的 MCP 草图创建原生实体混合，可用于受管零件中的默认实体增材。普通 XY 草图和已有 NACA 翼型草图均可作引用；截面必须按实际 Z 严格递增，原点及主轴符合 MCP 的 XY 定义。

```json
{
  "model_id": "先查询受管模型 ID",
  "expected_revision": 2,
  "label": "blend",
  "sections": ["section_0", "section_1", "section_2"],
  "interpolation": "smooth"
}
```

这段参数调用 `creo_loft`；也可把 `op:"loft"` 放在 `creo_execute_plan` 中，用于先创建草图再创建混合。`interpolation` 支持 `straight` 和 `smooth`。原生 ID、模式和截面数在保存前、重载后及失败回滚后核对。已有底座追加三截面平滑混合已通过尺寸修改、实体截面、保存重载、失败追加回滚及恢复模型的实查；另有 3/4/6 截面直线和平滑工厂验收。

历史0.2.5实现在建模期间临时加载同步Toolkit回调；首次加载可能出现安全警告，等待会占用建模通道。BUG-007开发版改为支持事先授权的常驻回调，详见下方准备步骤。构建器仍独立检查worker与回调模块指纹，worker修改不会重建未改变的DLL。

所有环境在建模前必须完成一次回调初始化。当前 `open_protk_unsigned_apps=PROMPT` 下的安全确认在人工初始化阶段完成。`creo_capabilities.direct_blend_callback.registry_file` 提供本机生成的 `protk.dat`：由使用者在Creo“辅助应用程序 / Auxiliary Applications”注册并启动，核对对应DLL及安全提示。MCP不修改签名、信任或Creo安全设置。`NEVER`下不能强制加载；应由Creo管理员按既有策略处理。

初始化后，原生worker逐次核对真实DLL句柄和协议，并使用该回调完成截面选择；请求仅接受当前部署jobs目录中的私有输入。每个已确认结束的请求释放自身上下文，常驻模块保留供后续调用。未知请求不自动重置。回调未加载、已卸载或重建后尚未初始化时，PROMPT/NEVER策略在DLL加载前返回 `BLEND_CALLBACK_SETUP_REQUIRED`，保留模型检查点。建模请求在任何策略下均不调用DLL加载。DLL重建产生新的内容寻址目录，需要重新初始化对应版本；旧副本不会被覆盖。

BUG-007当前仍在开发验收：未初始化保护、回滚、revision和后续小件已实测；常驻回调的完整直接Blend正例须按 [任务卡](work-items/BUG-007.md) 和 [本次记录](validation/BUG-007.md) 验证。上文既有正例是历史实现的证据，不能替代本次验证。

当前限 **默认实体增材、平行 XY 截面**。切除、曲面、新实体、非平行截面、起点映射和端点相切/曲率控制未验收或未封装。原生报告识别支持中文和英文 Creo；其他语言需本机验证。任意截面数量的输入范围不代表每种数量与轮廓均已验证。完整证据见 [本轮验收](validation_increment_025.json)。

若只需创建新零件，可继续使用随包九种子的 `creo_new_loft_part`；该路径不需要每次直接创建混合。原始 PRT、MIT、SHA256 和逐项验收见 [种子库](SEED_LIBRARY.md)。
