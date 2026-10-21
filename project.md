## 需求

- 巴西站点 app keeta
- 需要scrape途中红框内的数据
- 每次scrape的数据量一次15000，每周两次，共计30000/周
- 项目时长 一年 前期预算200w

Notes：提取解析红框内的数据

- BR; Sao Paulo + Santos, Greater São Paulo
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
- 样例数据与红框原文对照见 `assets/keeta-br-结算页字段样例.xlsx`（5 个工作表），转录说明见 `docs/oc-scrape-findings.md` 与 `docs/ac-br-抓取小结.md`。

## 待确认（TODO）

字段口径：

- [ ] **采集量级三套数字要对齐**。需求表「采集量级」写 `2 城 × 500 店/城 × 1 次/店 × 1 类账号 × 5 类距离段 × 2 轮/周 = 5,000 次/周`，但按此式相乘为 10,000（2×500×1×1×5×2）；本文件「需求」段又写 15000/次、2 次/周 = 30,000/周。需确认以哪套为准，并明确「次」的单位（采集店铺数 / 点位采样数 / 字段行数）。
- [ ] **账号类型口径**。`account_type` 枚举 0 新客 / 1 中客 / 2 老客，与需求表 Green 账号定义（0 单 / 1–4 单 / ≥5 单）的对应关系需确认；同时需求表有方案一（三类账号全采，按 DiDi 用户分布加权）与方案二（只采新客的代表性采集）两套，需定走哪套 —— 这直接决定账号池规模。
- [ ] **ETA 字段口径**。`ceta_min` / `ceta_max` 需求表写「最小/最大配送时长」，结算页给的却是送达时刻区间（Previsão 07:12–07:27）。需确认最终交付是时刻还是分钟数；若要分钟数，需定 `crawl_time`、采集日期与当地时区的采集及换算方式。
- [ ] **结算页取不到的 9 个字段**。`account_id`、`user_completed_orders_count`、`account_type`、`is_member`、`crawl_lat/lng`、`shop_lat/lng`、`shop_address`、`distance` 结算页不展示。需确认各自补齐来源（登录后个人中心/订单页、店铺页、地理编码、定位接口），以及取不到时留空还是用其他方案。
- [ ] **店铺 ID 来源**。需求表对 `shop_id` 标注「原始报文中获取」，需确认具体走哪个报文/接口。

采集执行：

- [ ] **采集环境未打通**。巴西网络环境与真实登录账号尚未落实，实时抓取仍只到截图转录阶段。需确认设备与账号方案（需求表：POCO X3 NFC + scrcpy + Android 调试模式）。
- [ ] **点位池**。每店 5 个点位，距离门店 1–2 / 2–3 / 3–4 / 4–5 / 5–6 km，且点位须可配送（不在海里/森林/湖泊/机场）。需确认点位由谁选取、由谁做可配送性校验。
- [ ] **采集节奏**。local 时间 11:00–22:59 共 12 小时，每小时一批、批次内店铺不重复；下一时段先回滚上时段未采成功的店铺再向下采集。需确认是否照此执行。
- [ ] **歇业回滚**。店铺歇业则该店不采，需求表要求 vendor 有反馈机制、由业务同步增补店铺 list。需确认流程与责任人。
- [ ] **固定菜品与起送门槛**。需求表要求每天采固定店铺与固定菜品（菜品下架才更换），店铺有起送门槛时加购至门槛以上。需确认加购规则由谁定、是否每次固定。
- [ ] **数据核验方式**。需求表要求「页面截图或视频与结果报表一致」。需确认是否每条记录都留证，以及留证的存储位置与回收方式。


## 工具

- POCO X3 NFC
- Android Keeta App
- Android Developer Debugging Mode
- Macbook Pro scrcpy
- 阿里网盘
- 微信

## Naming Convention

| abbr | mean                 |
| ---- | -------------------- |
| p1   | perplexity ask first |
| oc   | openai codex         |
| ac   | anthropic claud      |
| mm   | meta muse            |
