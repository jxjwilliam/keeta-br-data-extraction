## 结果入口

只需查看 `outputs/final/`：新版有效结果按采集时间戳命名为 `latest_YYYYMMDD_HHMMSS.xlsx` 和 `latest_YYYYMMDD_HHMMSS.csv`，迁移前的旧样例在 `history/`；新结果逐轮保存在 final 根目录。截图、XML、JSON、日志和草稿均归入 `outputs/internal/`。当前旧样例标记 `needs-review`；完整新版实机验收前不生成正式时间戳结果。

执行、输出结构与依赖见 [重跑说明](docs/keeta-rerun-guide.md)。

## Info

- BRD 里那套：巴西本地账号、SP+Santos 每城 500 店、5 个距离段、按小时批次
- 对抓取最关键的一点：消费者端只有 App，没有网页版，也没有公开 API。
- 商家门户在 merchant.keeta-global.com。


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

