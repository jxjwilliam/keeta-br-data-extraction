# 巴西 Keeta 抓取初查与中文字段样例

查询日期：2026-10-20。本文件是 **网页侧初查记录的唯一出处**（公开 URL、分享链接参数）；字段口径与进度见 `project.md`、`TODO.md`。

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

## 用户提供的 Android 商户分享链接

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

## 参考图样例的转录去向

`assets/weixin-3.png` 红框内容的逐项中文转录、样例数值与金额校验，已整理在：

- `assets/keeta-br-结算页字段样例.xlsx` —— 5 个工作表：说明、字段中文对照、样例数据、**红框原文对照**、参考截图
- `docs/ac-br-抓取小结.md` —— 人读的样例表格与金额核算

本文件不再重复该表。唯一需要在此强调的样例特例：该单的 R$ 10,00 优惠**就是**配送费差额（12.99 − 2.99 = 10.00），不得再从订单总额 48.98 中重复扣减。

## 抓取字段注意事项

字段口径与「不可补造」的约束统一写在 `project.md` §采集字段的口径说明，Agent 侧硬规则见 `AGENTS.md` §Extraction Rules。

## 下一步所需信息

进度、阻塞项与下一步统一维护在 `TODO.md`（C1 已登录并到 P3、C2 用 uiautomator2 抓 P3 XML、C7 解决 MIUI 输入注入）。


### 方案更正（2026-10-23）

已发现并核验官方商家 API。优先评估获授权数据接入与消费者报价范围；此前关于“25–40 秒/条”“接口成本为 1/100”“一定需要 root”的说法无本项目基准证据，不应用于生产设计或采购。详见 `docs/oc-keeta-access-and-scale-research.md`。以下原有估算已撤回。
