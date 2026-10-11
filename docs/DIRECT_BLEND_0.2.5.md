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

同步 Toolkit 回调模块在建模期间临时加载，选择原生截面链并完成普通混合定义；成功或异常后按实际模块 ID 卸载。首次加载可能出现 Creo 安全警告，需使用者在 Creo 中自行决定并确认；MCP 不修改 Creo 的安全设置。构建器分别检查工作程序和回调模块的源/SDK 指纹及文件校验，工作程序修改不会重新生成未改变的回调 DLL。

当前限 **默认实体增材、平行 XY 截面**。切除、曲面、新实体、非平行截面、起点映射和端点相切/曲率控制未验收或未封装。原生报告识别支持中文和英文 Creo；其他语言需本机验证。任意截面数量的输入范围不代表每种数量与轮廓均已验证。完整证据见 [本轮验收](validation_increment_025.json)。

若只需创建新零件，可继续使用随包九种子的 `creo_new_loft_part`；该路径不需要每次直接创建混合。原始 PRT、MIT、SHA256 和逐项验收见 [种子库](SEED_LIBRARY.md)。
