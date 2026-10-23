## 结果入口

只需查看 `outputs/final/`：新版有效结果按采集时间戳命名为 `latest_YYYYMMDD_HHMMSS.xlsx` 和 `latest_YYYYMMDD_HHMMSS.csv`，迁移前的旧样例在 `history/`；新结果逐轮保存在 final 根目录。截图、XML、JSON、日志和草稿均归入 `outputs/internal/`。当前旧样例标记 `needs-review`；完整新版实机验收前不生成正式时间戳结果。

执行、输出结构与依赖见 [重跑说明](docs/keeta-rerun-guide.md)。

## Info

- BRD 里那套：巴西本地账号、SP+Santos 每城 500 店、5 个距离段、按小时批次
- 对抓取最关键的一点：消费者报价目前只在 App 中实测取得；官方存在需商家授权的 API，尚未核验全市场消费者实时报价接口。见 [访问异常与规模化调查](docs/oc-keeta-access-and-scale-research.md)。
- 商家门户在 merchant.keeta-global.com。


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

## 当前状态

- USB 连接、投屏和实时截图已验证。
- uiautomator2 可读取结算页 XML；标准 adb dump 会遇到 idle 错误。
- 已导出一条实时记录：30 列，16 项有值，14 项未取得留空。计算值和默认上下文已标注来源。
- POCO X6 已验证自动点击和滑动；旧 X3 的 MIUI 输入限制见历史记录。完整跨页与批量采集尚未验收。

## 文件入口

- [需求与 30 字段定义](project.md)
- [进度、阻塞项与下一步](TODO.md)
- [设备与采集操作说明](docs/keeta-debug-guide.md)
- [巴西市场调研](docs/keeta-brazil-research.md)
- [网页入口调研](docs/oc-scrape-findings.md)
- [历史截图样例与金额核对](docs/ac-br-抓取小结.md)
- [界面文案中文对照](docs/keeta-checkout-fields-cn.md)
- [实时 Excel](outputs/final/history/20261021-16fields-needs-review.xlsx)
- [实时费用截图](outputs/internal/runs/keeta-live-20261021/fees.png)
- [实时读取证据](outputs/internal/runs/keeta-live-20261021/evidence.json)

`assets/` 保留原始参考图、字段样例工作簿及历史设备证据。`weixin-1.png` 与 `weixin-2.png` 内容相同，按原始材料保留。旧 `p3.xml` 是购物车抽屉，不能视为结算页 XML。

当前维护单条 PoC `scripts/keeta_scripe-v4.py`、XLSX 导出器 `scripts/export_keeta.mjs` 和离线测试；尚无生产批量采集程序。执行 `python3 -m unittest discover -s tests -v` 可验证字段规则与输出保护。旧 v1–v3 仅作历史参考，使用当前重跑说明中的命令。


##

1. 这批样本数据包含不同地址、商家、点餐内容、账号等维度；需求总量是 15000 条数据，先梳理清楚这个量级意味着什么。
2. 当前单组信息分散在 30 个不同页面：如果做自动抓取，代码该怎么跨页面提取信息，并把分散的数据合并组装成单条完整记录。
3. 对照目标需求，梳理当前实现还存在哪些问题、卡点与障碍，评估距离交付目标还有多大差距。

