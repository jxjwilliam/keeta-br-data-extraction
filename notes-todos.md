## NOTE

- 对抓取最关键的一点：消费者端只有 App，没有网页版，也没有公开 API。
- 商家门户在 merchant.keeta-global.com。

## TODO

> 汇总自 `project.md`、`docs/keeta-debug-guide.md`、`docs/ac-br-抓取小结.md`、`docs/oc-scrape-findings.md`。
> 文档分工：需求与 30 字段 = `project.md`；怎么做 = `docs/keeta-debug-guide.md`；进度与待办 = 本文件；市场背景与抓取约束 = `docs/keeta-brazil-research.md`；网页侧调研 = `docs/oc-scrape-findings.md`；样例与金额核算 = `docs/ac-br-抓取小结.md`。
> 状态以仓库内可见证据为准（`assets/p3.xml`、`assets/p3.png`、`keeta_test.mp4`）。
> 图例：`[x]` 已完成 · `[ ]` 待办 · **阻塞** = 等外部输入（账号 / 网络 / 需求方决策）。

### 立刻下一步（按依赖顺序）

1. **App / 系统语言切到 pt-BR**，或决定做双语解析器 —— 解析关键词是葡语（`Previsão`、`Subtotal`、`Taxa de entrega`），当前 App 是英文。
2. **用 BR 账号登录并走到 P3**（`Pedir agora`），全程不要点 `Fazer pedido`。
3. **在 P3 上重跑 `uiautomator dump`**，留下 `assets/p3.xml` + `assets/p3.png` 作为基线 fixture —— 这一步决定走 UI-XML 还是 OCR 路线。
4. 拿到 P3 文本后字段口径才能落地，再谈 15,000/次的批量与设备池规模。

### A. 环境与工具链（`docs/keeta-debug-guide.md` §1 / §4 / §5）

- [x] POCO X3 NFC（M2007J20CG, Android 12）USB 已连，`adb` 识别设备 `f753a0f3`。
- [x] scrcpy 5.0.1 镜像正常（MacBook）。
- [x] Keeta 已安装、可启动；收货地址已设为 `R. Floriano Peixoto, 1 - Sé, São Paulo - SP, 01016-050`（`assets/p3.xml` 首页文本节点已见）。
- [x] `uiautomator dump` 跑通且**文本可读**：`assets/p3.xml` 有 40 个非空 text 节点，不是空 WebView/Flutter 容器 → UI-XML 路线可行。**注意：该 dump 是首页/商家列表，不是 P3**（见 C2）。
- [x] 留证手段就绪：`keeta_test.mp4`（scrcpy `--record`）、`assets/p3.png`。
- [ ] **App 语言仍是英文**（dump 出来的字符串是 `Free delivery` / `Trackable delivery` / `On-time Promise`）。下一步：改系统与 App 语言为 Português (Brasil) / `pt-BR`，或写双语解析器；整轮采集必须统一一种语言。
- [ ] **BR 网络环境**：BR 出口 IP（测试用 VPN，生产用住宅/移动代理，一账号一固定 IP）、mock GPS 定位到圣保罗/桑托斯点位、SIM 换巴西 eSIM 或纯 Wi-Fi、系统区域设为巴西、时区 `America/Sao_Paulo`（UTC-3）。
- [ ] **Google Play Services / Google Maps 升级到最新版**（BRD 截图里的 `Google Play Services: atualizando` 会让定位不稳）。
- [ ] **账号池**：+55 手机号收短信、BR 收货地址、养出 0 单 / 1–4 单 / ≥5 单三档账号（账号类型口径见 B2）。
- [ ] **封号风险预案**：自动访问大概率违反 Keeta ToS，需预期设备指纹、mock GPS、频率风控，账号池要留损耗预算。
- [ ] 已解决的坑（备查）：`~/miniconda3/bin/adb`（pip 的 adb 包）遮蔽真 adb → `pip uninstall adb` + 删除；`scrcpy --stay-awake` 报 `WRITE_SECURE_SETTINGS` → 靠「USB 调试（安全设置）」或 MIUI「充电时屏幕不休眠」。

### B. 业务口径待确认（`project.md` §采集字段口径说明 + 需求表原文）

- [ ] **B1 采集量级三套数字要对齐（阻塞）**。需求表写 `2 城 × 500 店/城 × 1 次/店 × 1 类账号 × 5 类距离段 × 2 轮/周 = 5,000 次/周`，但按此式相乘是 10,000；`project.md` 需求段又写 15000/次、2 次/周 = 30,000/周。**下一步**：找需求方确认以哪套为准，并明确「次」的单位（采集店铺数 / 点位采样数 / 字段行数）。定了才能测算设备池（15,000/12h ≈ 1,250/h，30s/样本/设备 → 约 10–12 台）。
- [ ] **B2 账号类型口径**。`account_type` 枚举 0 新客 / 1 中客 / 2 老客，与需求表 Green 账号（0 单 / 1–4 单 / ≥5 单）的对应关系；需求表方案一（三类全采、按 DiDi 用户分布加权）vs 方案二（只采新客的代表性采集）选哪个 —— 直接决定账号池规模。**下一步**：同 B1 一起找需求方定。
- [ ] **B3 ETA 字段口径**。`ceta_min` / `ceta_max` 需求表写「最小/最大配送时长」，但 P3 给的是送达时刻区间（`Previsão 07:12-07:27`），首页商家列表给的又是时长（`10–25 min`）。**下一步**：确认最终交付是时刻还是分钟数；若要分钟数，需定 `crawl_time`、采集日期与 `America/Sao_Paulo` 时区的换算方式。
- [ ] **B4 结算页取不到的 9 个字段**。`account_id`、`user_completed_orders_count`、`account_type`、`is_member`、`crawl_lat/lng`、`shop_lat/lng`、`shop_address`、`distance` 结算页不展示。**下一步**：定各自补齐来源（登录后个人中心/订单页、店铺页、地理编码、mock GPS 点位），以及取不到时留空还是用别的方案。
- [ ] **B5 店铺 ID 来源**。需求表对 `shop_id` 标注「原始报文中获取」。**下一步**：确认走哪个报文/接口；已知分享链接带 `shopId=159559935`，但未核实与截图同一店铺。
- [ ] **B6 点位池**。每店 5 个点位，距店 1–2 / 2–3 / 3–4 / 4–5 / 5–6 km，且点位须可配送（不在海里/森林/湖泊/机场）。**下一步**：确认点位由谁选、由谁做可配送性校验。
- [ ] **B7 采集节奏**。local 11:00–22:59 共 12 小时，每小时一批、批次内店铺不重复；下一时段先回滚上时段未采成功的店铺再向下采集。**下一步**：确认是否照此执行（会决定调度器设计）。
- [ ] **B8 歇业回滚**。店铺歇业则该店不采，`shop_status` 置 `close`、其余字段置空、仍要反馈一条记录；需求表要求 vendor 有反馈机制、由业务同步增补店铺 list。**下一步**：定流程与责任人。
- [ ] **B9 固定菜品与起送门槛**。每天采固定店铺与固定菜品（菜品下架才更换），店铺有起送门槛时加购至门槛以上。**下一步**：定加购规则由谁定、是否每次固定。
- [ ] **B10 数据核验方式**。需求表要求「页面截图或视频与结果报表一致」。**下一步**：定是否每条留证、留证存储位置与回收方式（`keeta_test.mp4` 已证明 scrcpy `--record` 可行）。
- [ ] **B11 每条记录的留存口径**。采集时间、收货地址、账号类型、优惠信息必须随记录一起存，否则价格不可复现（`AGENTS.md` §Extraction Rules）。**下一步**：定这四项是并进 30 个字段的列，还是作为独立的采集上下文列。

### C. 采集链路与管线（`docs/keeta-debug-guide.md` §6 / §7 / §9）

- [ ] **C1 登录 BR 账号并触达 P3**。当前 `Logged-in BR account, P3 reached` 仍是 Pending。**下一步**：登录 → 选一家可配送店 → 加购 → 进 `Pedir agora`（不点 `Fazer pedido`）。
- [ ] **C2 P3 的 uiautomator dump（关键分叉点）**。`assets/p3.xml` 现存的是首页/商家列表，**不是** P3。**下一步**：在 P3 重新 dump 并 grep `Previsão|Subtotal|Taxa de|Total`；有文本 → 直接解析 XML；只有空容器 → 退回 OCR（PaddleOCR / Tesseract `por`），吞吐下降。
- [ ] **C3 PoC 管线**。XML 解析 → 金额归一为整数分 → CSV/XLSX 导出（`batch_no = YYYYMMDD`），内置 QA 校验：`total_final == product_final + delivery_final + service_final`（45.00+2.99+0.99=48.98）、`delivery_original − delivery_final` 等于优惠行（12.99−2.99=10.00）、`ceta_min <= ceta_max`、截图与提取值逐条比对。
- [ ] **C4 店铺 list 来源**。需求表说采集范围是「指定店铺 list，见下方文件」，该文件尚未拿到。**下一步**：向需求方索取 list（含优先级排序、KA/SKA 分层）。
- [ ] **C5 API replay spike（可选，后置）**。mitmproxy + `adb reverse` + Frida 绕 SSL pinning（Android 7+ 默认不信任用户 CA）。成本约为 UI 方案的 1/100，但封号风险更高、需 root。**下一步**：先做完 C2 再评估是否值得做。

### D. 已覆盖 / 无需再跟踪

- `assets/keeta-br-结算页字段样例.xlsx` —— 30 字段中文对照 + 样例数据 + 红框原文对照 + 金额校验公式，已完成，且与 `project.md` 字段表逐行一致（已自动比对）。
- `docs/p1.md` —— 已并入 `docs/keeta-brazil-research.md`，现为历史索引，无待办。
- `docs/oc-scrape-findings.md` —— 只剩网页侧调研与分享链接参数。沙箱内 `m.keeta-global.com` / `m.mykeeta.com` / `url-eu.mykeeta.com` 被网络策略拦截，这**不是**项目阻塞项：真实抓取走手机 + BR 网络，web 侧只作参考。
- 凭据规范（`AGENTS.md`）—— 密码、验证码、Cookie 不进文档、截图和提交；采集证据里如需账号信息，只留脱敏标识。
