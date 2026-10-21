# Keeta 提单页红框数据定位 + 中文翻译（步骤②③，2026-10-20）

数据来源：William 上传的红框截图（`assets/weixin-3.png`）+ BRD 文档（`assets/weixin-1.png`，与 `assets/weixin-2.png` 同内容，《20260624 P3页面ETA BRD》）。
红框数据全部位于 Keeta App 的**提单页（P3）**：左图是提单页顶部的配送地址/预计时效区，右图是 **Resumo do pedido（订单摘要）**面板。与 BRD「采集模块」截图一致，也与步骤①调研的公开字段 schema 吻合。

> 红框逐项原文对照已整理进 `assets/keeta-br-结算页字段样例.xlsx` 的「红框原文对照」表；30 个 BRD 字段清单见 `project.md` §采集字段。本文件只补充该表未收录的界面文案。

## 红框字段对照表

8 项红框数据与 BRD 字段的对应关系（字段定义见 `project.md`，原文对照见 xlsx）：

| App 葡语原文 | 中文 | BRD 字段名 |
|---|---|---|
| Açaí tapioca WRK（商户名） | 商户名称 | shop_name |
| 3 × Tapioca Com Nutella | 购买商品明细 | product_info |
| Previsão 07:12-07:27 | 预计送达时间窗 | ceta_min / ceta_max |
| Subtotal | 商品原价（小计） | product_original |
| Taxa de entrega | 配送费（原价 → 券后价） | delivery_original / delivery_final |
| Taxa de serviço | 服务费 | service_original / service_final |
| Total | 总价（券后应付） | total_final |
| Desconto de R$ 10,00 aplicado | 已应用优惠 | 券额（对应 delivery 优惠） |

金额校验：45.00 + 2.99 + 0.99 = 48.98 ✓；配送费优惠 12.99 − 2.99 = 10.00 ✓，与「已应用优惠 R$ 10.00」一致。

## 提单页其他可见文案翻译（xlsx 未收录部分）

| 葡语原文 | 中文翻译 |
|---|---|
| Editar | 编辑 |
| o menu | 菜单 |
| O que fazer quando um item está fora de estoque? / Selecionar | 某商品缺货时如何处理？/ 选择 |
| Usar agora | 立即使用 |
| Use um cupom e ganhe 35% de desconto | 使用优惠券立享 35% 折扣 |
| Se o seu pedido chegar após 07:42, você ganha um cupom de R$ 10,00 ou mais, dependendo da espera. | 若订单在 07:42 之后送达，可获得 R$ 10.00 或更高面额优惠券（金额视等待时长而定）。 |

其余文案（`Pedir agora`、`Resumo do pedido`、`Desconto instantâneo`、`Cupom — 1 disponível, até R$ 15,75 OFF`、`Ganhe 35% de desconto`、`Horário Garantido`、`Fazer pedido`、收货地址两行）见 xlsx「红框原文对照」表。

## 说明
- 「找到」的口径：红框 7 类数据（商户名、商品明细、预计时效窗、商品原价、配送费原/券后、服务费、总价）已全部在提单页定位到，与 BRD 采集字段表一一对应；按 William 的要求未做全量提取。
- ETA 口径：页面展示的是时钟时间窗（07:12–07:27），BRD 字段 ceta_min/ceta_max 记录的是最小/最大配送时长，落库时需按下单时刻换算成分钟数。
