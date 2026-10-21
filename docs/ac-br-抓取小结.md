# 巴西 Keeta 结算页抓取小结

日期：2026-10-20  
范围：巴西站 Keeta App 结算页（P3 页面 ETA），一条可核对的中文样例

> 本文件只保留 **样例数据与金额核算**。字段清单见 `project.md` §采集字段，字段级取值说明见 `assets/keeta-br-结算页字段样例.xlsx`，进度与待办见 `TODO.md`。

## 一、结论

巴西消费端 App 已核验。桌面沙箱无法直连 Keeta 网页/App，但手机侧链路已在 2026-10-21 打通（adb / scrcpy / uiautomator dump），并已真实走到 P3 结算页。本文的 30 字段样例仍基于参考截图转录；实时 P3 只拿到截图与金额，XML 受 idle 报错阻塞，见第四节。

> 手机侧步骤与排错见 `docs/keeta-debug-guide.md`。

## 二、App 核验

应用信息（名称、包名、开发者、版本、商店入口、业务城市、分享链接）统一维护在 `project.md` §Info，此处不重复。

## 三、样例数据（截图转录）

配送地址：Rua Marcílio de Sá, 231 - Jardim das Vertentes, São Paulo - SP  
店铺：Açaí tapioca WRK

| 中文列名     | 葡语原文                          | 数值                       |
| -------- | ----------------------------- | ------------------------ |
| 店铺名称     | Açaí tapioca WRK              | 3 itens（3 件）             |
| 商品明细     | 3 × Tapioca Com Nutella       | 3 份 Nutella 榛子可可酱木薯饼     |
| 商品金额     | —                             | R$ 45,00（单价 R$ 15,00，推算） |
| 预计送达时段   | Previsão                      | 07:12–07:27（时刻区间，不是时长）   |
| 商品小计（原价） | Subtotal                      | R$ 45,00                 |
| 配送费原价    | Taxa de entrega（划线）           | R$ 12,99                 |
| 配送费折后价   | Taxa de entrega               | R$ 2,99                  |
| 服务费      | Taxa de serviço               | R$ 0,99                  |
| 订单总额     | Total                         | R$ 48,98                 |
| 已应用优惠    | Desconto de R$ 10,00 aplicado | R$ 10,00                 |

金额核对：45.00 + 2.99 + 0.99 = 48.98；12.99 − 2.99 = 10.00。原价总额 58.98 为分项推算，页面未单列。页面另有「Cupom 1 disponível – até R$ 15,75 OFF」「Ganhe 35% de desconto」，本单未使用，不能与已减的 10.00 混算。

## 四、实时 P3 验证（2026-10-21 13:05，圣保罗）

设备 POCO X3 NFC，Gmail 账号（未绑手机号），收货地址 `Work — Rua Floriano Peixoto, 1, São Paulo, SP, Sé`，页面 `Checkout`，**未提交订单**。截图证据：`assets/p3.png`。

| 页面字段 | 英文原文 | 数值 |
| --- | --- | --- |
| 店铺 | Massa do wild | — |
| 商品 | 1 × Espaguete à Bolonhesa | R$ 40.76（原价 R$ 42.90） |
| 预计送达 | Est. arrival | 17:25–17:40（圣保罗时间） |
| 商品原价 | Subtotal（购物车） | R$ 42.90 |
| 商品折后价 | — | R$ 40.76（5% off，减 2.14） |
| 配送费原价 | — | R$ 7.99 |
| 配送费折后价 | — | R$ 0.00（免配送，减 7.99） |
| 服务费 | — | R$ 0.99 |
| 已应用优惠 | R$10.13 off applied | R$ 10.13（商品 2.14 + 配送 7.99） |
| 订单总额 | Total | R$ 41.75 |

核对：42.90 + 7.99 + 0.99 − 10.13 = 41.75，等价于 40.76 + 0 + 0.99 = 41.75。

三点注意：

- 购物车阶段曾显示 Voucher −10.19、Total R$30.57；结算页未选用该券（`Select at checkout`），两组金额不能混算。
- 手机状态栏 13:05 是温哥华时间，ETA 17:25–17:40 是圣保罗时间（UTC-3），相差 4 小时；采集前要统一时区，或在 `crawl_time` 记录偏移。
- 该页 XML 因 `ERROR: could not get idle state` 未取到，以上数值来自截图；配送费/服务费行尚未在页面上展开核对。

## 五、字段口径

30 个字段的逐条中文对照、样例取值与取值说明在 `assets/keeta-br-结算页字段样例.xlsx` 的「字段中文对照」表；实现口径见 `project.md`。两条最容易踩的：

- `ceta_min` / `ceta_max` 是送达时刻（07:12 / 07:27），不是配送分钟数。
- 服务费页面只显示一个价格，原价与折后价均填 99 分，不留空也不编造折扣。

## 六、下一步

统一见 `TODO.md`：用 uiautomator2 抓 P3 XML、解决 `INJECT_EVENTS`、统一时区，然后建 PoC 管线。

## 七、交付物

- `assets/keeta-br-结算页字段样例.xlsx` —— 5 个工作表：说明、字段中文对照、样例数据、红框原文对照、参考截图。金额校验公式全部通过。
- `docs/keeta-checkout-fields-cn.md` —— 提单页可见文案的中葡对照。
- `TODO.md` —— 进度、阻塞项与下一步。
