# 巴西 Keeta 结算页抓取小结

日期：2026-10-20  
范围：巴西站 Keeta App 结算页（P3 页面 ETA），一条可核对的中文样例

> 本文件只保留 **样例数据与金额核算**。字段清单见 `project.md` §采集字段，字段级取值说明见 `assets/keeta-br-结算页字段样例.xlsx`，进度与待办见 `notes-todos.md`。

## 一、结论

巴西消费端 App 已核验；但当前环境无法直连 Keeta 网页/App，实时抓取未打通。本次交付的是一条**基于参考截图转录并翻译**的完整样例，用于确认字段口径和中文命名，不代表当前线上报价。

> 手机侧环境已在 2026-10-21 打通（adb/scrcpy/uiautomator dump），见 `docs/keeta-debug-guide.md`。

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

## 四、字段口径

30 个字段的逐条中文对照、样例取值与取值说明在 `assets/keeta-br-结算页字段样例.xlsx` 的「字段中文对照」表；实现口径见 `project.md`。两条最容易踩的：

- `ceta_min` / `ceta_max` 是送达时刻（07:12 / 07:27），不是配送分钟数。
- 服务费页面只显示一个价格，原价与折后价均填 99 分，不留空也不编造折扣。

## 五、下一步

统一见 `notes-todos.md`：C1 登录 BR 账号并触达 P3、C2 在 P3 重跑 uiautomator dump、C3 PoC 管线。

## 六、交付物

- `assets/keeta-br-结算页字段样例.xlsx` —— 5 个工作表：说明、字段中文对照、样例数据、红框原文对照、参考截图。金额校验公式全部通过。
- `keeta-checkout-fields-cn.md` —— 提单页可见文案的中葡对照。
- `notes-todos.md` —— 进度、阻塞项与下一步。
