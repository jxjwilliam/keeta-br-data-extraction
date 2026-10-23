## 需求

- 巴西站点 app keeta
- 需要scrape途中红框内的数据
- 每次scrape的数据量一次15000，每周两次，共计30000/周
- 项目时长 一年 前期预算200w

Notes：提取解析红框内的数据

- BR; Sao Paulo + Santos / São Vicente, Greater São Paulo
- excel形式即可
- ETA: Estimated Time of Arrival
- R. Jandaia, 7550 - Bela Vista, São Paulo - SP, 01316-100, Brazil
- R. Floriano Peixoto, 1 - Centro, Salto - SP, 13328-300, Brazil
### Phones

| # | Phone |
| ---- | ---- |
| 1 | +55 28 96988-5772 |
| 2 | +55 91 97437-0892 |
| 3 | +55 65 94517-5954 |
| 4 | +55 53 97237-5239 |
| 5 | +55 55 97780-5292 |
| 6 | +55 35 96437-6217 |
| 7 | +55 81 91606-2392 |
| 8 | +55 71 94576-5060 |
| 9 | +55 46 95913-7499 |
| 10 | +55 33 91086-4373 |
| 11 | +55 41 96446-7862 |
| 12 | +55 54 90653-3150 |

### Addresses

| # | Address | 街区 | 城市 | 邮编 |
| ---- | ---- | ---- | ---- | ---- |
| 1 | Rua Augusta, 1508 - Consolação, São Paulo - SP, 01304-001, Brazil | Consolação | São Paulo | 01304-001 |
| 2 | Avenida Paulista, 1000 - Bela Vista, São Paulo - SP, 01310-100, Brazil | Bela Vista | São Paulo | 01310-100 |
| 3 | Rua Oscar Freire, 702 - Jardins, São Paulo - SP, 01426-000, Brazil | Jardins | São Paulo | 01426-000 |
| 4 | Rua da Consolação, 2391 - Consolação, São Paulo - SP, 01301-100, Brazil | Consolação | São Paulo | 01301-100 |
| 5 | Avenida Brigadeiro Luís Antônio, 2344 - Jardins, São Paulo - SP, 01402-000, Brazil | Jardins | São Paulo | 01402-000 |
| 6 | Rua Teodoro Sampaio, 1020 - Pinheiros, São Paulo - SP, 05406-000, Brazil | Pinheiros | São Paulo | 05406-000 |
| 7 | Rua dos Pinheiros, 555 - Pinheiros, São Paulo - SP, 05422-010, Brazil | Pinheiros | São Paulo | 05422-010 |
| 8 | Avenida Rebouças, 3970 - Pinheiros, São Paulo - SP, 05402-600, Brazil | Pinheiros | São Paulo | 05402-600 |
| 9 | Rua Harmonia, 123 - Vila Madalena, São Paulo - SP, 05435-000, Brazil | Vila Madalena | São Paulo | 05435-000 |
| 10 | Alameda dos Anapurus, 1450 - Moema, São Paulo - SP, 04087-004, Brazil | Moema | São Paulo | 04087-004 |


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

1. VPN 不是硬性要求
2. 美团风控（IP/账号/设备维度限流）
3. 关 WiFi 用移动数据打开 Keeta。

| 配置项 | 对你当前采集任务的判断 |
|---|---|
| **App 内市场选择巴西** | 应保持，确保访问巴西业务 |
| **配送地址选择圣保罗** | 关键。使用账户保存的地址，获取对应商户、配送费和 ETA |
| **VPN 切到巴西／圣保罗** | **未证实必须**。可以作为网络对照测试，不能保证解决问题 |
| **Android 系统 region 设为巴西** | **未证实必须**，暂不需要为了排错反复切换 |
| **系统时区改为圣保罗** | **未证实是访问条件**；对采集时间与 ETA 核算有帮助，也可以通过程序明确转换时区 |

## ipinfo.io/json

```json
{
  "ip": "184.65.89.63",
  "hostname": "s0106b3e07831be3.vs.shawcable.net",
  "city": "Surrey",
  "region": "British Columbia",
  "country": "CA",
  "loc": "49.1063,-122.8251",
  "org": "AS6327 Shaw Communications",
  "postal": "V3Z",
  "timezone": "America/Vancouver",
  "readme": "https://ipinfo.io/missingauth"
}
```

## WEditor

WEditor is a browser-based visual tool for inspecting Android app interfaces and creating UI automation scripts, commonly used with the OpenATX /  uiautomator2  ecosystem. It can show the Android UI hierarchy, element properties, selectors, and generate Python automation code.