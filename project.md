## 需求

- 巴西站点 app keeta
- 需要scrape途中红框内的数据
- 每次scrape的数据量一次15000，每周两次，共计30000/周
- 项目时长 一年 前期预算200w

Notes：提取解析红框内的数据

- BR; Sao Paulo + Santos / São Vicente, Greater São Paulo
- excel形式即可
- ETA: Estimated Time of Arrival

## Info

| 项目 | 内容 |
| ---- | ---- |
| 应用名称 | Keeta - Food Delivery（葡语区显示 Keeta - Delivery de comida） |
| Android 包名 | com.sankuai.sailor.afooddelivery |
| 开发者 | KANGAROO LIMITED（美团关联主体） |
| 参考版本 | 3.12.501（2026-10 查询到的版本，实际以商店为准） |
| Android 入口 | https://play.google.com/store/apps/details?hl=pt-BR&id=com.sankuai.sailor.afooddelivery |
| iOS 入口 | https://apps.apple.com/br/app/keeta-delivery-de-comida/id1662451643 |
| 业务城市 | 圣保罗（São Paulo）及大圣保罗；试点含桑托斯、圣维森特 |
| 用户提供分享链接 | https://m.keeta-global.com/marketing/applaunch/index.html?...&shopId=159559935&region=BR |


## 采集字段

需求表共 30 个字段。字段代码与描述沿用需求表英文口径（`assets/weixin-1.png` 与 `assets/weixin-2.png` 内容相同），红框取值示意见 `assets/weixin-3.png`，中文列名沿用 `assets/keeta-br-结算页字段样例.xlsx` 的「字段中文对照」表。

| 序号 | 字段代码 | 中文列名 | 描述 |
| ---- | -------- | -------- | ---- |
| 1 | batch_no | 批次号 | 批次，年月日命名即可，YYYYMMDD |
| 2 | country | 国家 | 国家 |
| 3 | platform | 平台 | 平台 |
| 4 | city_name | 城市名称 | 城市名称 |
| 5 | crawl_time | 采集时间 | 数据采集时间（local 时间），时间戳格式，要精确到秒 |
| 6 | account_id | 用户 ID | 用户的账号 ID |
| 7 | user_completed_orders_count | 历史完成订单数 | 该用户历史累计完单个数 |
| 8 | account_type | 账号类型 | 账号类型，0：新客，1：中客，2：老客 |
| 9 | is_member | 是否会员 | 1：会员；0：非会员 |
| 10 | shop_id | 店铺 ID | 店铺 ID（需求表标注：原始报文中获取） |
| 11 | shop_name | 店铺名称 | 店铺名称 |
| 12 | crawl_lat | 采集点纬度 | 采集经纬度（纬度） |
| 13 | crawl_lng | 采集点经度 | 采集经纬度（经度） |
| 14 | crawl_address | 采集点地址 | 采集的定位地址 |
| 15 | shop_lat | 店铺纬度 | 店铺经纬度（纬度） |
| 16 | shop_lng | 店铺经度 | 店铺经纬度（经度） |
| 17 | shop_address | 店铺地址 | 店铺地址 |
| 18 | ceta_min | 最小配送时长 | 最小配送时长 |
| 19 | ceta_max | 最大配送时长 | 最大配送时长 |
| 20 | product_info | 商品信息 | 结算页商品展示信息 |
| 21 | product_original | 商品原价 | 商品原价，仅保留数字，单位：分 |
| 22 | product_final | 商品折后价 | 商品券后价，仅保留数字，单位：分 |
| 23 | delivery_original | 配送费原价 | 配送费原价，仅保留数字，单位：分 |
| 24 | delivery_final | 配送费折后价 | 配送费券后价，仅保留数字，单位：分 |
| 25 | service_original | 服务费原价 | 服务费原价，仅保留数字，单位：分 |
| 26 | service_final | 服务费折后价 | 服务费券后价，仅保留数字，单位：分 |
| 27 | total_original | 订单原价总额 | 仅保留数字，单位：分 |
| 28 | total_final | 订单折后总额 | 仅保留数字，单位：分 |
| 29 | distance | 配送距离 | 配送距离 |
| 30 | shop_status | 店铺状态 | 店铺状态，枚举值：open/close 等 |

口径说明（需求表之外的实现约束，来自参考图核对）：

- 金额字段一律只保留数字、单位为分，币种 BRL 不做汇率换算（R$ 45.00 = 4500 分）。
- `ceta_min` / `ceta_max` 在需求表写作「最小/最大配送时长」，但结算页给的是预计送达时刻区间（Previsão 07:12–07:27）。要得到分钟数，需同时记录 `crawl_time`、采集日期与当地时区后再换算，不能把时刻当时长。
- 结算页不展示的字段不要补造：`account_id`、`user_completed_orders_count`、`account_type`、`is_member`、`crawl_lat/lng`、`shop_lat/lng`、`shop_address`、`distance` 需登录账号或从店铺页/地理编码补齐。
- `shop_status` 为 open/close 枚举；需求表要求无论是否采集到信息都反馈一条记录，此时店铺状态置 close、其余字段置空。
- 样例数据与红框原文对照见 `assets/keeta-br-结算页字段样例.xlsx`（5 个工作表）与 `docs/ac-br-抓取小结.md`。

## 待确认（TODO）

采集量级、账号类型、ETA 口径、结算页取不到的 9 个字段、店铺 ID 来源、点位池、采集节奏、歇业回滚、固定菜品与起送门槛、数据核验方式等 11 项，统一维护在 `notes-todos.md`（B1–B11），本文件不重复。

## 工具

- POCO X3 NFC
- Android Keeta App
- Android Developer Debugging Mode
- Macbook Pro scrcpy
- 阿里网盘
- 微信
- uiautomator2 或 Appium

## Naming Convention

| abbr | mean                 |
| ---- | -------------------- |
| p1   | perplexity ask first |
| oc   | openai codex         |
| ac   | anthropic claud      |
| mm   | meta muse            |


## VPN