# 巴西 Keeta 抓取初查与中文字段样例

查询日期：2026-10-20。

## 当前结果

- 已找到巴西官网：https://www.keeta-global.com/BR/pt-BR
- 已核验 Android 应用：https://play.google.com/store/apps/details?hl=pt-BR&id=com.sankuai.sailor.afooddelivery
- iOS 入口：https://apps.apple.com/br/app/keeta-delivery-de-comida/id1662451643
- 官网当前可见页面是品牌介绍、商户入驻和 App 下载入口，未在该页面找到消费者商户列表、菜单或结算数据。这不等于已证明没有其他网页入口。
- 尚未进入巴西 App 的实时商户或结算页，尚未完成在线价格/结算样例抓取。用户已确认沿用圣保罗，且目前没有可用的巴西 App 登录环境或商户分享链接。

## 公开商户分享入口验证

从商户公开页面 https://linktr.ee/gogreenbr 找到标题为「Keeta, entregas mais rápidas!」（Keeta，配送更快！）的链接：https://url-eu.mykeeta.com/aGhi7dWz 。

| 中文列名 | 原始数据 | 中文数据 | 来源及限制 |
| --- | --- | --- | --- |
| 商户名称 | go green | go green（保留品牌名） | 商户公开 Linktree 页面，尚未在 Keeta 店内核验 |
| 商户地址 | R. Flórida, 1970 - loja 3 - Brooklin, São Paulo - SP, 04565-001, Brazil | 巴西圣保罗州圣保罗市 Brooklin 区 Flórida 街 1970 号 3 号店，邮编 04565-001 | 商户自述地址，不是消费者收货地址 |
| Keeta 分享链接 | https://url-eu.mykeeta.com/aGhi7dWz | Keeta 商户入口 | 链接存在，店铺在 App 内的状态未核验 |

在当前桌面内置浏览器中实际打开该短链，最终跳转至 `https://m.mykeeta.com/marketing/applaunch/index.html?locale=en`，页面标题为 Keeta，仅显示「Download Keeta」「Already installed. Open it now」等 App 唤起文字，没有菜单、价格、ETA 或费用字段。跳转页语言为英文；不能据此将这家圣保罗商户判断为其他地区商户，也不能将跳转页当作巴西店铺详情页。

网页读取工具无法获取短链中间的 share-content 响应；这只说明当前工具未能访问，并不证明该接口本身不存在或必须登录。未使用猜测的店铺 ID、接口参数或价格填充样例。

当前结论：已取得公开在线商户线索与分享入口，未打通实时结算抓取。下一项有价值的验证是通过官方巴西 App 打开此链接，先检查游客是否可浏览，再确定是否需要登录。当前没有可操作的手机/App 环境，因此尚不能验证游客访问和手机号要求；也尚无依据判定必须使用巴西手机号、当地 IP 或 GPS。

## 参考图中文样例

### 用户提供的 Android 商户分享链接

用户已安装 Android Keeta，并提供了带有下列参数的商户分享链接。已在浏览器打开验证，页面仅显示「Baixe agora」（立即下载）和「Ir para o app」（前往 App），未返回可见商户名称、菜单或费用数据。

| 中文列名 | 链接参数 | 提取值 | 含义 |
| --- | --- | --- | --- |
| 店铺标识 | inner_url 内的 shopId | 159559935 | 分享链接指向的店铺 ID；尚未与 App 页面核对 |
| 市场代码 | region | BR | 巴西；不能仅凭此参数确定店铺位于圣保罗 |
| 链接语言参数 | locale | en | 英语；实际落地页显示葡萄牙语 |
| 入口类型 | url_id | shop_share_link | 商户分享链接 |

解码后的 App 内部链接为 `sailorc://keeta.com/marketTransfer/machpro?mach_bundle_name=mach_pro_sailor_c_shop&shopId=159559935`。这是 App 深链接，并非已验证可返回店铺 JSON 的 HTTP API。

可复用落地链接（保留店铺标识，省略推广参数；尚未单独验证此简化链接）：

`https://m.keeta-global.com/marketing/applaunch/index.html?inner_url=sailorc%3A%2F%2Fkeeta.com%2FmarketTransfer%2Fmachpro%3Fmach_bundle_name%3Dmach_pro_sailor_c_shop%26shopId%3D159559935&region=BR&locale=en&openType=appLaunch`

当前桌面工具不能直接查看用户 Android 手机上的 App 内容。下一步需该店铺在手机中的商户/商品页及付款前结算页截图，用于核验店铺名、商品、金额和预计送达区间；无需付款。

下列内容仅转录自 `weixin-3.png`，不是本次在线抓取的新数据。`weixin-1.png` 和 `weixin-2.png` 为长图需求参考，红框细节以第三张图核对。币种为巴西雷亚尔（BRL），没有换算成人民币。

| 中文列名 | 葡语原文/标识 | 图片中的值 | 中文数据 |
| --- | --- | --- | --- |
| 商户名称 | 商户标题 | Açaí tapioca WRK | Açaí tapioca WRK（巴西莓·木薯饼 WRK，保留原店名） |
| 商品明细 | 商品行 | 3 × Tapioca Com Nutella | 3 份 Nutella 榛子可可酱木薯饼 |
| 商品金额 | 商品行金额 | R$ 45,00 | 45.00 巴西雷亚尔，3 份商品行合计，非单价 |
| 预计最早送达时间 | Previsão 左端 | 07:12 | 当地时间 07:12，日期及具体时区未提供 |
| 预计最晚送达时间 | Previsão 右端 | 07:27 | 当地时间 07:27，日期及具体时区未提供 |
| 商品小计（原价） | Subtotal | R$ 45,00 | 45.00 巴西雷亚尔 |
| 配送费原价 | Taxa de entrega 划线价 | R$ 12,99 | 12.99 巴西雷亚尔 |
| 配送费优惠价 | Taxa de entrega 当前价 | R$ 2,99 | 2.99 巴西雷亚尔 |
| 服务费 | Taxa de serviço | R$ 0,99 | 0.99 巴西雷亚尔 |
| 订单应付总额 | Total | R$ 48,98 | 48.98 巴西雷亚尔 |
| 已显示优惠金额 | Desconto de R$ 10,00 aplicado | R$ 10,00 | 已应用 10.00 巴西雷亚尔优惠 |

核算：45.00 + 2.99 + 0.99 = 48.98；12.99 − 2.99 = 10.00。该样例的优惠可由配送费差额解释，不应再从 48.98 中重复扣除 10.00。

## 抓取字段注意事项

- `07:12–07:27` 是预计送达的钟点区间，不能直接作为最短/最长配送耗时（分钟）。图中需求表的 `ceta_min` / `ceta_max` 若要求耗时，需要同时保存采集时间、日期和当地时区，再确认计算口径。
- 结算金额受收货地点、商品数量、账号、优惠、采集时间影响。首条在线样例应保存这些条件和对应页面证据。
- 服务费这里只显示一个价格，无法由该图确认服务费原价与优惠价是否相同；不能补造。
- 图中没有独立给出优惠后的商品小计，不能将订单总额填入商品折后价。
- 本次只验证能否取得少量样例，不执行原需求的每次 15000 条批量采集。

## 下一步所需信息

- 城市已确认使用圣保罗；实时配送报价仍需确定一个采集地址。
- 已找到上述公开分享链接；仍缺可操作的巴西 Keeta App 环境。不要在文档里保存密码、验证码或 Cookie。
- 获得入口后，选择一家可配送商户，核对商品页和付款前的结算页字段，保存一条实时中文样例及其来源；不需要提交订单。
