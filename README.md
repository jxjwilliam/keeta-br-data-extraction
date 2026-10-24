# Keeta BR 数据采集

通过已登录的 Android Keeta App 读取店铺及结算报价，逐条保存 CSV/XLSX。当前为实机试运行，尚未验证 15,000 条/次的生产能力。无法取得的字段留空，完整、部分及失败尝试均留存。

## 安装与运行

Python 3.12 实测；USB 手机需已解锁、允许调试，并登录 Keeta。依赖和 XLSX 运行时要求见 [运行资源](docs/resources.md)。

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
adb devices
```

在项目根目录执行。**恢复当前 X3 会话：**

```bash
python3 scripts/keeta_stream.py \
  --serial f753a0f3 \
  --interval 180 \
  --max-attempts 20 \
  --resume outputs/internal/streams/continuous_20261023_174448
```

**新建会话：**

```bash
python3 scripts/keeta_stream.py \
  --serial f753a0f3 \
  --interval 180 \
  --max-attempts 20
```

- 当前 X3 为 `f753a0f3`；以 `adb devices` 实际结果为准。换手机/账号用新会话。
- 店间至少 180 秒；20 是尝试上限，异常和导航预算可能使其提前结束。未指定参数时默认最多3次。
- Ctrl+C 停止，已写记录保留；同一手机/会话只运行一个采集进程。
- 默认选择用户已指定的 Rua Jandaia, 7550, São Paulo, SP 保存地址。保留当前账号和优惠设置，不提交订单或支付。
- 访问限制/验证时暂停；只有人工确认恢复后才额外使用 `--access-restored`。VPN 不能保证避免限制。

### 持续追加

```bash
python3 scripts/keeta_stream.py \
  --serial f753a0f3 --interval 180 --continuous --keep-screenshots 5 \
  --resume outputs/internal/streams/continuous_20261023_191140
```

`--continuous`不受max-attempts限制；可与stop-at合用。单窗口无新店时冷却至少180秒后从下一窗口继续，游标保存到内部feed-cursor.json；连续三个窗口无新增或达到12页深度预算仍停止，避免无界刷新。限制/验证/连续失败等安全停止保持。Ctrl+C结束。

### 指定当天截止时间

例如，按温哥华当天15:57停止手机采集，记录开始/结束及停止原因：

```bash
python3 scripts/keeta_stream.py \
  --serial f753a0f3 \
  --interval 180 \
  --max-attempts 1000 \
  --stop-at 15:57 \
  --run-timezone America/Vancouver
```

`--stop-at`只接受当天尚未到达的HH:MM；截止时中断等待/采集，保留当前已读字段，再完成本地文件保存（导出可能晚几秒结束）。安全停止条件仍优先，1000不是访问配额。运行时间在内部executions/run_*.json及run-status.json留存，Excel“成功率”页附开始/结束/截止时间和时区。文件名及业务采集时间仍使用圣保罗时间。

## 结果

只查看 `outputs/final/`：每会话一组 `continuous_YYYYMMDD_HHMMSS.csv/xlsx`，按圣保罗启动时间命名，同会话逐条更新；历史结果不覆盖。

当前 X3：[CSV](outputs/final/continuous_20261023_174448.csv) · [Excel](outputs/final/continuous_20261023_174448.xlsx)。X6 的独立8条历史会话仍保留在 final；更早截图转录样例在 `history/`。

前30列为业务字段，另附 `attempt_id`、`collection_status`、`filled_fields`、`error_reason`、`amounts_validated`。

- `complete`：地址及金额校验通过，**不表示30字段满值**。当前完整记录通常为22/30。
- `partial` / `failed`：保留能核实的字段及失败原因，不补零、不伪装关店。
- `navigation`：误入非店铺页面的事件，不计入店铺成功率分母。

Excel 的“成功率”页提供完整/部分/失败数量及字段覆盖率。内部 SQLite、XML/截图、来源与日志统一在 `outputs/internal/`。历史探针和旧生成文件已归档，见 [清理记录](docs/cleanup-notes.md)。

## 脚本与文档

| 入口 | 用途 |
| --- | --- |
| [keeta_stream.py](scripts/keeta_stream.py) | 当前主程序：导航/恢复、每次尝试、账本及CSV |
| [keeta_scripe-v4.py](scripts/keeta_scripe-v4.py) | 主程序复用的页面捕获、字段解析及金额校验；保留现有文件名以兼容调用 |
| [export_keeta_stream.mjs](scripts/export_keeta_stream.mjs) | 连续会话Excel及成功率工作表 |
| [export_keeta.mjs](scripts/export_keeta.mjs) | 单条诊断导出，由v4辅助命令使用 |
| [运行与恢复指南](docs/keeta-continuous-guide.md) | 参数、成功率口径、证据及异常恢复 |
| [设备排错](docs/keeta-debug-guide.md) | ADB、scrcpy、锁屏与连接问题 |
| [研究/规划索引](docs/README.md) | 保留的调查证据和业务待确认项 |
| [TODO](TODO.md) / [项目需求](project.md) | 当前进度与交付范围 |

`scripts/muse_keeta_scrape.py` 是独立实验方案，未作为当前运行入口；未合并其行为到主程序。旧v1–v3、capture和test1探针已退出活动目录。

## 校验

```bash
python3 -m unittest discover -s tests -v
```

离线测试不连接手机，覆盖金额与跨页一致性、ETA、缺失值/0、快照恢复、完整/部分尝试、页面恢复和禁止下单。实际长期吞吐量和防限流效果仍待验证。

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

口径：金额为BRL整数分；ETA为同页送达时刻减采集时间后向上取整分钟，保留原始时间窗；账号0单→0、1–4单→1、≥5单→2；只将明确Open/Closed映射营业状态。失败不等于close。可见未使用券不参与金额核算，未知ID/坐标/会员等不推测。
