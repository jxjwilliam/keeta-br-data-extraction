## TODO List

> 汇总自 `project.md`、`docs/keeta-debug-guide.md`、`docs/ac-br-抓取小结.md`、`docs/oc-scrape-findings.md`。
> 文档分工：需求与 30 字段 = `project.md`；怎么做 = `docs/keeta-debug-guide.md`；进度与待办 = 本文件；市场背景与抓取约束 = `docs/keeta-brazil-research.md`；网页侧调研 = `docs/oc-scrape-findings.md`；样例与金额核算 = `docs/ac-br-抓取小结.md`。
> 状态以仓库内可见证据为准（`assets/feed-pizza.xml`、`assets/shop.xml`、`assets/p3.xml`、`assets/p3.png`；录像不入库）。
> 图例：`[x]` 已完成 · `[ ]` 待办 · **阻塞** = 等外部输入（账号 / 网络 / 需求方决策）。

### 立刻下一步（按依赖顺序）

1. **用 uiautomator2 抓 P3 XML**：`d.settings["waitForIdleTimeout"]=0` + `d.dump_hierarchy()`，绕过 `could not get idle state`；确认 `Subtotal / Delivery fee / Service fee / Total` 是否可读。
2. **解决输入注入**：开启 MIUI「USB 调试（安全设置）」；或验证 uiautomator2 的无障碍点击（`d(text="...").click()`）是否可用。
3. **统一时区**：手机改为 `America/Sao_Paulo`，或在 `crawl_time` 记录 UTC 偏移；当前状态栏 13:05 与 ETA 17:25–17:40 差 4 小时。
4. **展开结算页费用行**（Total 行或下滑），截 `assets/p3-fees.png`（尚未生成），补齐配送费/服务费原始值。
5. 拿到 P3 文本后落一条完整实时样例，跑金额 QA，再谈 15,000/次的批量与设备池规模。

### A. 环境与工具链（`docs/keeta-debug-guide.md` §1 / §4 / §5）

- [x] POCO X3 NFC（M2007J20CG, Android 12）USB 已连，`adb` 识别设备 `f753a0f3`。
- [x] scrcpy 5.0.1 镜像正常（MacBook）。
- [x] Keeta 已安装、可启动；收货地址已设为 `R. Floriano Peixoto, 1 - Sé, São Paulo - SP, 01016-050`（`assets/feed-pizza.xml` 列表页文本节点已见）。
- [x] `uiautomator dump` 跑通：`assets/feed-pizza.xml`（搜索结果列表）、`assets/shop.xml`（店铺页）、`assets/p3.xml`（购物车抽屉）都不是空 WebView/Flutter 容器。但**商家卡片的店名/评分/配送费/ETA/距离不在无障碍树里**（卡片只有 `content-desc="feed shopcard"` 和促销标签），纯 XML 拿不到列表字段，需 XML 取 bounds + 卡片区域 OCR（见 C2、C6）。**注意：这三个 dump 都不是 P3 结算页**。
- [x] 留证手段就绪：scrcpy `--record` 录像（示例录像因体积已删除，`*.mp4` 不入库）、`assets/p3.png` 截图。
- [ ] **App 语言仍是英文**（dump 出来的字符串是 `Free delivery` / `Trackable delivery` / `On-time Promise`）。下一步：改系统与 App 语言为 Português (Brasil) / `pt-BR`，或写双语解析器；整轮采集必须统一一种语言。
- [ ] **BR 网络环境**：BR 出口 IP（测试用 VPN，生产用住宅/移动代理，一账号一固定 IP）、mock GPS 定位到圣保罗/桑托斯点位、SIM 换巴西 eSIM 或纯 Wi-Fi、系统区域设为巴西、时区 `America/Sao_Paulo`（UTC-3）。
- [ ] **设备时区仍非圣保罗**：状态栏显示 13:05（温哥华），P3 的 `Est. arrival 17:25-17:40` 是圣保罗时间，两者差 4 小时。采集前把手机时区改为 `America/Sao_Paulo`，或在 `crawl_time` 中显式记录 UTC 偏移，否则 ETA 与采集时间不可比。
- [ ] **Google Play Services / Google Maps 升级到最新版**（BRD 截图里的 `Google Play Services: atualizando` 会让定位不稳）。
- [ ] **账号池**：+55 手机号收短信、BR 收货地址、养出 0 单 / 1–4 单 / ≥5 单三档账号（账号类型口径见 B2）。
- [ ] **封号风险预案**：自动访问大概率违反 Keeta ToS，需预期设备指纹、mock GPS、频率风控，账号池要留损耗预算。
- [ ] 已解决的坑（备查）：`~/miniconda3/bin/adb`（pip 的 adb 包）遮蔽真 adb → `pip uninstall adb` + 删除；`scrcpy --stay-awake` 报 `WRITE_SECURE_SETTINGS` → 靠「USB 调试（安全设置）」或 MIUI「充电时屏幕不休眠」；MIUI 上 `uiautomator dump` 会打印 `/data/system/theme_config/theme_compatibility.xml` FileNotFoundException，属系统噪声，XML 仍会正常写出，可忽略。

### B. 业务口径待确认（`project.md` §采集字段口径说明 + 需求表原文）

- [ ] **B1 采集量级三套数字要对齐（阻塞）**。需求表写 `2 城 × 500 店/城 × 1 次/店 × 1 类账号 × 5 类距离段 × 2 轮/周 = 5,000 次/周`，但按此式相乘是 10,000；`project.md` 需求段又写 15000/次、2 次/周 = 30,000/周。**下一步**：找需求方确认以哪套为准，并明确「次」的单位（采集店铺数 / 点位采样数 / 字段行数）。定了才能测算设备池（15,000/12h ≈ 1,250/h，30s/样本/设备 → 约 10–12 台）。
- [ ] **B2 账号类型口径**。`account_type` 枚举 0 新客 / 1 中客 / 2 老客，与需求表 Green 账号（0 单 / 1–4 单 / ≥5 单）的对应关系；需求表方案一（三类全采、按 DiDi 用户分布加权）vs 方案二（只采新客的代表性采集）选哪个 —— 直接决定账号池规模。**下一步**：同 B1 一起找需求方定。
- [ ] **B3 ETA 字段口径**。`ceta_min` / `ceta_max` 需求表写「最小/最大配送时长」，但 P3 给的是送达时刻区间（`Previsão 07:12-07:27`），首页商家列表给的又是时长（`10–25 min`）。2026-10-21 的列表 dump 再次确认：列表卡片是分钟区间，P3 是钟点区间。**下一步**：确认最终交付是时刻还是分钟数；若用列表时长，可直接填 `ceta_min/ceta_max`，另存 P3 时刻作为辅助列；若要换算，需定 `crawl_time`、采集日期与 `America/Sao_Paulo` 时区。
- [ ] **B4 结算页取不到的 9 个字段**。`account_id`、`user_completed_orders_count`、`account_type`、`is_member`、`crawl_lat/lng`、`shop_lat/lng`、`shop_address`、`distance` 结算页不展示。**下一步**：定各自补齐来源（登录后个人中心/订单页、店铺页、地理编码、mock GPS 点位），以及取不到时留空还是用别的方案。
- [ ] **B5 店铺 ID 来源**。需求表对 `shop_id` 标注「原始报文中获取」。**下一步**：确认走哪个报文/接口；已知分享链接带 `shopId=159559935`，但未核实与截图同一店铺。
- [ ] **B6 点位池**。每店 5 个点位，距店 1–2 / 2–3 / 3–4 / 4–5 / 5–6 km，且点位须可配送（不在海里/森林/湖泊/机场）。**下一步**：确认点位由谁选、由谁做可配送性校验。
- [ ] **B7 采集节奏**。local 11:00–22:59 共 12 小时，每小时一批、批次内店铺不重复；下一时段先回滚上时段未采成功的店铺再向下采集。**下一步**：确认是否照此执行（会决定调度器设计）。
- [ ] **B8 歇业回滚**。店铺歇业则该店不采，`shop_status` 置 `close`、其余字段置空、仍要反馈一条记录；需求表要求 vendor 有反馈机制、由业务同步增补店铺 list。**下一步**：定流程与责任人。
- [ ] **B9 固定菜品与起送门槛**。每天采固定店铺与固定菜品（菜品下架才更换），店铺有起送门槛时加购至门槛以上。**下一步**：定加购规则由谁定、是否每次固定。
- [ ] **B10 数据核验方式**。需求表要求「页面截图或视频与结果报表一致」。**下一步**：定是否每条留证、留证存储位置与回收方式（scrcpy `--record` 已验证可行；录像文件体积大，不入库）。
- [ ] **B11 每条记录的留存口径**。采集时间、收货地址、账号类型、优惠信息必须随记录一起存，否则价格不可复现（`AGENTS.md` §Extraction Rules）。**下一步**：定这四项是并进 30 个字段的列，还是作为独立的采集上下文列。

### C. 采集链路与管线（`docs/keeta-debug-guide.md` §6 / §7 / §9）

- [x] **C1 登录 BR 账号并触达 P3**。2026-10-21 13:05 已进入 `Checkout` 页（未点 `Place order`），截图留证 `assets/p3.png`：地址 `Work - Rua Floriano Peixoto, 1, São Paulo, SP, Sé`、`Est. arrival 17:25-17:40`、`Massa do wild / 1 × Espaguete à Bolonhesa / R$40.76 (R$42.90)`、`Total R$41.75`、`R$10.13 off applied`。店铺页留证 `assets/shop.xml`，购物车抽屉留证 `assets/p3.xml`（13:04）。
- [ ] **C2 P3 的 uiautomator dump（关键分叉点）**。店铺页和购物车层已证明是原生 TextView，字段可直接解析。13:05 的 `assets/p3.png` 已是 `Checkout` 页，但 `assets/p3.xml` 仍是 13:04 的购物车内容——`uiautomator dump` 报 `could not get idle state`，**写文件失败后 pull 到了旧文件**。金额已用截图核对：`42.90 + 7.99 + 0.99 − 10.13 = 41.75`，即商品原价 42.90、配送费原价 7.99、服务费 0.99、优惠 10.13（商品 5% 折 2.14 + 免配送 7.99）。**下一步**：先 `adb shell rm -f /sdcard/p3.xml` 再 dump，确认 `ls -l` 时间戳更新后再 pull；若结算页费用行折叠，需展开或下滑后重 dump。2026-10-21 13:10 重试仍报 `could not get idle state` 且文件未生成，页面存在持续动画；改用 `uiautomator2` 的 `dump_hierarchy()`（`waitForIdleTimeout=0`）绕开 idle 等待。
- [ ] **C3 PoC 管线**。XML 解析 → 金额归一为整数分 → CSV/XLSX 导出（`batch_no = YYYYMMDD`），内置 QA 校验：`total_final == product_final + delivery_final + service_final`（45.00+2.99+0.99=48.98）、`delivery_original − delivery_final` 等于优惠行（12.99−2.99=10.00）、`ceta_min <= ceta_max`、截图与提取值逐条比对。
- [ ] **C4 店铺 list 来源**。需求表说采集范围是「指定店铺 list，见下方文件」，该文件尚未拿到。**下一步**：向需求方索取 list（含优先级排序、KA/SKA 分层）。
- [ ] **C5 API replay spike（可选，后置）**。mitmproxy + `adb reverse` + Frida 绕 SSL pinning（Android 7+ 默认不信任用户 CA）。成本约为 UI 方案的 1/100，但封号风险更高、需 root。**下一步**：先做完 C2 再评估是否值得做。
- [ ] **C6 列表页混合解析（已做小样验证）**。证据：`assets/feed-pizza.xml` + `assets/feed-pizza.png`。XML 只能取到 `feed shopcard` 的 bounds 和促销标签，店名/评分/配送费/ETA/距离要按 bounds 裁图后 OCR：沙箱用 Tesseract `eng` 实测读出 `Futuro Kereitorio / 5.0 (40+) / R$4.99 / 26–41 min / 5.2 km`。划线原价会因删除线误识别（`R$14.99` 读成 `2$44-99`），但折后配送费、ETA、距离可用。**下一步**：固定裁剪比例、2x 放大 + 二值化，并用正则校验（`R\$ ?\d+[.,]\d{2}`、`\d+[–-]\d+ min`、`\d+[.,]\d km`）。
- [ ] **C7 输入注入被 MIUI 拦截（自动化阻塞）**。`adb shell input tap` 报 `SecurityException: Injecting to another application requires INJECT_EVENTS permission`，当前只能手动点手机。**下一步**：开发者选项开启「USB 调试（安全设置）」（需小米账号/SIM），开启后 adb 与 scrcpy 控制才可用；若无法开启，改用自建 AccessibilityService 的 `dispatchGesture` 做点击与滑动。

### D. 已覆盖 / 无需再跟踪

- `assets/keeta-br-结算页字段样例.xlsx` —— 30 字段中文对照 + 样例数据 + 红框原文对照 + 金额校验公式，已完成，且与 `project.md` 字段表逐行一致（已自动比对）。
- `docs/p1.md` —— 已并入 `docs/keeta-brazil-research.md`，现为历史索引，无待办。
- `docs/oc-scrape-findings.md` —— 只剩网页侧调研与分享链接参数。沙箱内 `m.keeta-global.com` / `m.mykeeta.com` / `url-eu.mykeeta.com` 被网络策略拦截，这**不是**项目阻塞项：真实抓取走手机 + BR 网络，web 侧只作参考。
- 凭据规范（`AGENTS.md`）—— 密码、验证码、Cookie 不进文档、截图和提交；采集证据里如需账号信息，只留脱敏标识。
