# 巴西 Keeta 结算页抓取小结

日期：2026-10-20
范围：巴西站 Keeta App 结算页（P3 页面 ETA），一条可核对的中文样例

## 一、结论

巴西消费端 App 已核验；但当前环境无法直连 Keeta 网页/App，实时抓取未打通。本次交付的是一条**基于参考截图转录并翻译**的完整样例，用于确认字段口径和中文命名，不代表当前线上报价。

## 二、App 核验

| 项目 | 内容 |
| --- | --- |
| 应用名称 | Keeta - Food Delivery（葡语区显示 Keeta - Delivery de comida） |
| Android 包名 | com.sankuai.sailor.afooddelivery |
| 开发者 | KANGAROO LIMITED（美团关联主体） |
| 参考版本 | 3.12.501（2026-10 查询，实际以商店为准） |
| Android 入口 | https://play.google.com/store/apps/details?hl=pt-BR&id=com.sankuai.sailor.afooddelivery |
| iOS 入口 | https://apps.apple.com/br/app/keeta-delivery-de-comida/id1662451643 |
| 业务城市 | 圣保罗（São Paulo）及大圣保罗；试点含桑托斯、圣维森特 |

用户提供的商户分享链接为 App 唤起页（`shopId=159559935`、`region=BR`）。`m.keeta-global.com`、`m.mykeeta.com`、`url-eu.mykeeta.com` 在当前沙箱均被网络策略拦截，无法打开，也未核实该店与截图是否为同一家。

## 三、样例数据（截图转录）

配送地址：Rua Marcílio de Sá, 231 - Jardim das Vertentes, São Paulo - SP
店铺：Açaí tapioca WRK

| 中文列名 | 葡语原文 | 数值 |
| --- | --- | --- |
| 店铺名称 | Açaí tapioca WRK | 3 itens（3 件） |
| 商品明细 | 3 × Tapioca Com Nutella | 3 份 Nutella 榛子可可酱木薯饼 |
| 商品金额 | — | R$ 45,00（单价 R$ 15,00，推算） |
| 预计送达时段 | Previsão | 07:12–07:27（时刻区间，不是时长） |
| 商品小计（原价） | Subtotal | R$ 45,00 |
| 配送费原价 | Taxa de entrega（划线） | R$ 12,99 |
| 配送费折后价 | Taxa de entrega | R$ 2,99 |
| 服务费 | Taxa de serviço | R$ 0,99 |
| 订单总额 | Total | R$ 48,98 |
| 已应用优惠 | Desconto de R$ 10,00 aplicado | R$ 10,00 |

金额核对：45.00 + 2.99 + 0.99 = 48.98；12.99 − 2.99 = 10.00。原价总额 58.98 为分项推算，页面未单列。页面另有「Cupom 1 disponível – até R$ 15,75 OFF」「Ganhe 35% de desconto」，本单未使用，不能与已减的 10.00 混算。

## 四、字段口径

需求表共 30 个字段，已在 Excel 中逐条给出中英文对照，金额统一按「分」存储（R$ 45.00 = 4500 分）。取值要点：

- 已有值：batch_no、country、platform、city_name、shop_name、crawl_address、ceta_min/ceta_max、product_info、product_original/final、delivery_original/final、service_original/final、total_original/final、shop_status。
- 截图中缺失、未编造：account_id、user_completed_orders_count、account_type、is_member、shop_id、shop_address、crawl_lat/lng、shop_lat/lng、distance。
- `ceta_min/ceta_max` 在图中是送达时刻（07:12/07:27），不是配送分钟数；若要时长，需同时记录采集时刻、日期和时区。
- 服务费只有一个价格，无法区分原价与折后价，两者均填 99 分。

## 五、下一步

1. 在巴西网络环境用真实账号打开分享链接，确认游客能否浏览，记录登录态、GPS 与收货地址。
2. 先跑通单店单账号链路（店铺页 → 加购 → 结算页），确认 30 个字段是否都能取到，再评估每次 15000 条、每周两次的批量方案。
3. 批量采集需解决账号池、点位池（距店 1–2/2–3/3–4/4–5/5–6 km 各 5 个点）、频控与店铺歇业回滚。
4. 每条记录保存采集时间、地址、账号类型和优惠信息，否则价格不可复现。

## 六、交付物

`keeta-br-结算页字段样例.xlsx`，含 5 个工作表：说明、字段中文对照、样例数据、红框原文对照、参考截图。金额校验公式全部通过。
