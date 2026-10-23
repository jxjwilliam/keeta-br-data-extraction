# Keeta App 数据采集可行性分析

日期：2026-10-23
目标：采集 Keeta App（巴西，圣保罗 + 桑托斯）结算页（P3）红框内尽可能多的真实数据，用于 ETA gap 监控。

## 1. 结论摘要

- **官方 Open API 无法提供红框数据。** 它是商家侧接口（订单、菜单、门店），不含消费者结算页的个性化报价。
- **消费者端私有接口没有公开文档。** 其端点、鉴权和签名机制无法确认。逆向签名、绕过风控、伪装设备或定位的做法不在建议范围内，原因是违反平台条款、封禁风险高、长期不稳定。
- **数据采集本身是可做的。** 可行路径是：压缩请求量的 App 端采集、数据供应商、Keeta 商务授权、用户自愿面板。
- **被锁的主因很可能是请求密度。** 但风控阈值外部无从得知，需要用自己的日志验证。
- **做不到的是"零风险、全自动、全覆盖地稳定拿到"。** 想要稳定和合规，最终要靠商务授权或购买数据。

## 2. 官方 API 调研

入口：`open.mykeeta.com/api/open`，文档站 `api-docs.mykeeta.com`。开发者站 `developers.mykeeta.com` 是前端渲染的单页应用，正文未能抓取，以下基于文档站。

### 体系
- Open Delivery API（基于 Open Delivery v1.5.0）
- Standard Keeta API（Order / Menu / Product / Store）
- Grocery Keeta API

### 准入流程
1. 开发者站注册，约 5 个工作日审核
2. 签 NDA
3. 获得开发者账号和测试门店
4. 开发并做 SIT 联调
5. 品牌注册
6. 每个品牌做强制 UAT（需配合一家真实餐厅）
7. SIT 通过后分配生产环境 AppId 和 Secret

### 数据边界
- 调用需要门店 token 和门店 ID，门店 token 来自商家授权（商家登录 Keeta 商家后台确认）
- 只能读写已授权门店自己的菜单、商品、订单
- 限流按 appId 计 QPS，菜单类接口约 10–100 QPS

### 对红框字段的覆盖
| 字段类别 | 官方 API |
|---|---|
| 门店基础信息、菜单、商品原价（已授权门店） | 部分可得 |
| ETA 区间（ceta_min / ceta_max） | 无 |
| 配送费原价/折后价、服务费、总价（含用户侧优惠） | 无 |
| 任意未授权门店的任何数据 | 无 |

## 3. 路径对比

| 路径 | 能否拿到红框数据 | 风险 / 说明 |
|---|---|---|
| 官方 Open API | 否 | 仅商家侧，需授权 |
| 私有接口 + 绕过风控 | 技术上可能 | 违反条款，封禁风险高，不建议 |
| App 端采集（压缩请求量） | 是 | 现有路径，成本最低，仍有被锁风险 |
| 数据供应商 | 是（需确认巴西覆盖） | 供应商承担采集和风控；Actowiz 等公开宣传了沙特 Keeta 数据，巴西覆盖未查到证据 |
| Keeta 商务合作 | 是（需谈判） | 最稳定，周期和结果不确定 |
| 用户自愿面板 | 是（覆盖有限） | 合规性最高 |

## 4. BRD 核对与优化建议

### 4.1 工作量算术
- BRD 公式 `2城 × 500 × 1次 × 1账号 × 5距离 × 2轮 = 5,000`，实际乘积为 **10,000**。
- 三类账号全采约 30,000 次/周，与 project.md 一致。

### 4.2 单账号负载
- 若每轮 15,000 次在 12 小时内完成，约 1,250 次/小时。
- 按 2 城 × 3 类账号共 6 个账号估算，每账号约每 17 秒一次结算预览。
- 这很可能是被锁的主要诱因，也是单台手机吞吐不够的原因。

### 4.3 抽样设计
ETA gap 监控的目标是城市级聚合指标，不是全店覆盖。

- **固定面板**：约 100 家店 × 5 个距离段，用于趋势对比。
- **轮转面板**：其余店轮转，用于覆盖。
- 样本量参考（假设 ETA 标准差约 5 分钟，均值误差 ±1 分钟）：每个分层（城市 × 账号类型 × 时段）约 100 个样本。这是估算，需用首批数据校准。
- 预计请求量可降 3–5 倍。

### 4.4 字段口径
结算页价格受优惠券影响，截图中可见"可用优惠券 R$15,75 OFF"和"Horário Garantido"保证送达券。建议新增字段并避免自动叠加使用优惠：

- `coupon_available`
- `coupon_applied`
- `guaranteed_time_promo`
- `cart_spec`（购物车规格标识）

### 4.5 购物车标准化
服务费可能随小计变化。固定购物车规格（如起送价附近的单件商品），保证跨店可比。

## 5. 红框字段与采集来源

| 字段 | 来源 |
|---|---|
| ceta_min / ceta_max | 结算页"Previsão"时间区间 |
| shop_name, product_info | 结算页商户名与商品明细 |
| product_original / product_final | 商品小计 |
| delivery_original / delivery_final | 配送费（Taxa de entrega）原价与折后价 |
| service_original / service_final | 服务费（Taxa de serviço） |
| total_original / total_final | 总计（Total） |
| shop_id | 原始报文获取 |
| distance, shop_status | 采集时记录 |

## 6. 建议行动

1. 按第 4 节调整抽样与字段设计，降低请求量。
2. 记录每次被锁前的请求量、频率和操作路径，找出实际触发线。
3. 被锁时立即停止并退避，不要重试。
4. 并行向 Keeta 巴西商务团队询问数据合作授权，预算可作为谈判筹码。
5. 评估数据供应商，先确认巴西覆盖与合规，并在合同中写明风险归属。
6. 上量前做法务评估（平台条款、LGPD）。
7. 不用有业务价值的主账号做采集。

## 7. 待确认事项

- 红框数据是客户自有门店还是第三方门店（决定官方 API 能否覆盖）。
- Keeta 是否有面向第三方的只读市场数据授权。
- 目标数据时效性：周度趋势还是日内实时。
- 供应商在巴西的实际覆盖范围。

## 参考来源

- Keeta Open Delivery API: https://api-docs.mykeeta.com/apis/opendelivery/merchantendpoints/merchantupdate
- Keeta Order Management API: https://api-docs.mykeeta.com/apis/standard/order.md
- 接入流程: https://api-docs.mykeeta.com/apis/standard/docs/intro.md
- Development Resources: https://api-docs.mykeeta.com/apis/standard/docs/developresource.md
- Open Delivery How to Start: https://api-docs.mykeeta.com/apis/opendelivery/how-to-start.md
- 商家自助授权指南: https://api-docs.mykeeta.com/apis/standard/docs/selfauthor.md
- Menu API 限流: https://api-docs.mykeeta.com/apis/standard/menu/keetaid-based/queryproductslist
- Actowiz Keeta 数据抓取: https://www.actowizsolutions.com/scrape-keeta-saudi-arabia-riyadh-data.php
