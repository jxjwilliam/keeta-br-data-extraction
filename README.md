## Info

- BRD 里那套：巴西本地账号、SP+Santos 每城 500 店、5 个距离段、按小时批次
- 对抓取最关键的一点：消费者端只有 App，没有网页版，也没有公开 API。
- 商家门户在 merchant.keeta-global.com。

## 当前状况

- 已在 POCO X3 安卓手机上安装 Keeta App，区域设为巴西。
- USB 调试 + adb（设备 `f753a0f3`）+ scrcpy 5.0.1 镜像已跑通。
- 已用 Gmail 账号登录（未绑定手机号），收货地址 `R. Floriano Peixoto, 1 - Sé, São Paulo - SP`。
- 2026-10-21 13:05 已真实走到 `Checkout` 结算页并留证（`assets/p3.png`），**未提交订单**。
- 店铺页、购物车页均为原生 TextView，可用 uiautomator XML 解析；列表页商家卡片不暴露文字，需“XML bounds + OCR”。
- 卡点：P3 的 `uiautomator dump` 报 `could not get idle state`（改用 uiautomator2）；`adb shell input tap` 被 MIUI `INJECT_EVENTS` 拦截。
- 相关调研资料在 `docs/`，截图与 dump 在 `assets/`，进度与待办统一维护在 `TODO.md`。
- 联系人及电话等个人信息不写入仓库文档。