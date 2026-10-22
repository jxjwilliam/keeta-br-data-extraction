## Info

- BRD 里那套：巴西本地账号、SP+Santos 每城 500 店、5 个距离段、按小时批次
- 对抓取最关键的一点：消费者端只有 App，没有网页版，也没有公开 API。
- 商家门户在 merchant.keeta-global.com。

## 当前状态

- USB 连接、投屏和实时截图已验证。
- uiautomator2 可读取结算页 XML；标准 adb dump 会遇到 idle 错误。
- 已导出一条实时记录：30 列，16 项有值，14 项未取得留空。计算值和默认上下文已标注来源。
- MIUI 阻止自动点击/滑动，需要提醒操作者手动滚动。批量采集尚未实现。

## 文件入口

- [需求与 30 字段定义](project.md)
- [进度、阻塞项与下一步](TODO.md)
- [设备与采集操作说明](docs/keeta-debug-guide.md)
- [巴西市场调研](docs/keeta-brazil-research.md)
- [网页入口调研](docs/oc-scrape-findings.md)
- [历史截图样例与金额核对](docs/ac-br-抓取小结.md)
- [界面文案中文对照](docs/keeta-checkout-fields-cn.md)
- [实时 Excel](outputs/keeta-live-20261021/keeta-实时30字段.xlsx)
- [实时费用截图](outputs/keeta-live-20261021/fees.png)
- [实时读取证据](outputs/keeta-live-20261021/evidence.json)

`assets/` 保留原始参考图、字段样例工作簿及历史设备证据。`weixin-1.png` 与 `weixin-2.png` 内容相同，按原始材料保留。旧 `p3.xml` 是购物车抽屉，不能视为结算页 XML。

没有维护中的应用源码、批量抓取程序或测试套件。已移除临时探针及依赖 `/tmp` 固定样例的导出脚本。不要将旧样例导出器当作实时采集程序。


##

1. 这批样本数据包含不同地址、商家、点餐内容、账号等维度；需求总量是 15000 条数据，先梳理清楚这个量级意味着什么。
2. 当前单组信息分散在 30 个不同页面：如果做自动抓取，代码该怎么跨页面提取信息，并把分散的数据合并组装成单条完整记录。
3. 对照目标需求，梳理当前实现还存在哪些问题、卡点与障碍，评估距离交付目标还有多大差距。

