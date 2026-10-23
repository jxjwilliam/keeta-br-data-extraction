# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概况

Keeta（美团外卖巴西站）App 报价采集项目：驱动已登录的 Android 手机，从店铺详情页和 Checkout（P3）页读取 30 个字段，导出 XLSX/CSV。需求量级 15000 条/次、2 次/周，但当前只完成单条 PoC 与连续采集试运行，尚未做批量生产。

核心是「Python 采集/解析脚本 + 原始证据 + Markdown 文档」，没有 Web 服务、依赖清单或前端。先读 `TODO.md`（当前状态、B1–B11 待确认项、下一步），再读 `project.md`（30 字段定义、账号/地址池、工具链）。

## 常用命令

运行时依赖：`python3`、`uiautomator2`、`Pillow`、系统 `adb`；XLSX 导出还需要 Node 与 `@oai/artifact-tool`（默认位于 `~/.cache/codex-runtimes/codex-primary-runtime/dependencies`，可用 `KEETA_RUNTIME` 指向包含 `node/bin/node` 和 `node/node_modules` 的目录）。运行时缺失时只保留内部 CSV/账本草稿，不发布半套结果。

```bash
python3 -m pip install uiautomator2 Pillow
```

### 测试（全部离线，不需要手机）

```bash
python3 -m unittest discover -s tests -v
```

单条测试（两种写法都可用）：

```bash
python3 -m unittest tests.test_keeta_fields.FieldTests.test_eta_ceil -v
```

```bash
python3 -m unittest tests.test_keeta_stream.LedgerTests.test_resume_and_no_duplicate -v
```

测试 fixture 在 `tests/fixtures/`，覆盖金额核对、ETA 取整/跨日、账号类型、免费配送记 0、地址气泡不算已选地址、账本恢复与不覆盖快照。

### 单条采集（`scripts/keeta_scripe-v4.py`）

```bash
python3 scripts/keeta_scripe-v4.py --serial 979f0245
```

当前已在 Checkout 页时：自动滚动 → 捕获 → 解析 → 校验 → 导出。

```bash
python3 scripts/keeta_scripe-v4.py --serial 979f0245 --item '商品完整名称'
```

从当前店铺加购一份简单商品并进入 Checkout；不选必选规格、不清理购物车。

```bash
python3 scripts/keeta_scripe-v4.py --parse-dir outputs/internal/runs/<轮次>
```

```bash
python3 scripts/keeta_scripe-v4.py --export-run outputs/internal/runs/<轮次>
```

```bash
python3 scripts/keeta_scripe-v4.py --inspect-context-dir outputs/internal/runs/<轮次>
```

离线重解析 / 重新导出 / 只读上下文；都不访问手机。

### 连续采集（`scripts/keeta_stream.py`）

```bash
python3 scripts/keeta_stream.py --serial 979f0245 --interval 30
```

```bash
python3 scripts/keeta_stream.py --serial 979f0245 --interval 30 --resume outputs/internal/streams/continuous_YYYYMMDD_HHMMSS
```

逐店采集并逐条提交；Ctrl+C 或异常停止后已提交记录保留。

设备侧操作（adb、scrcpy、uiautomator dump、区域设置）见 `docs/keeta-debug-guide.md`。POCO X6 当前序列号 `979f0245`；旧 X3 的 `f753a0f3` 只出现在历史脚本里。

## 架构：一条记录如何产生

### 单条管线（`scripts/keeta_scripe-v4.py`）

1. `capture(d, out, label)` — 用 uiautomator2 `dump_hierarchy()` 取 XML、`screenshot()` 取图，脱敏后写入 `outputs/internal/runs/<轮次>/`：`<label>.xml`、`<label>.png`、`<label>.json`（含 `captured_at`，America/Sao_Paulo）。
2. `parse(out, context)` — 只解析 `package == com.sankuai.sailor.afooddelivery` 且有 text 的节点，按 `bounds` 坐标把「左侧标签—右侧金额」配对，产出 30 字段 `record`、逐字段 `field_sources`、`conditions`、`qa` 到 `evidence.json`，并写 `draft.csv`。金额全部转整数「分」。
3. `parse()` 内的断言是硬门槛：商品原价 = Subtotal；商品折后 + 配送折后 + 服务费 = Total；原价总额 − 折后总额 = 页面 `off applied` 优惠；顶部 `Total R$` 与费用页一致；商品行必须读到「原价/折后价」两个金额。任一不符立即抛错，不生成正常结果。
4. `export_bundle(run)` — 调 Node 脚本 `scripts/export_keeta.mjs` 生成 XLSX（两个工作表：30 字段数据 + 字段核对/来源）。
5. `publish_files(run, final, captured_at)` — 仅当地址已确认、`crawl_address`/`city_name` 有值、`qa.amounts_reconciled` 与 `same_item_and_total_across_pages` 均为真时，成对发布 `outputs/final/latest_YYYYMMDD_HHMMSS.xlsx/.csv`。时间戳排他创建，绝不覆盖；复制失败会回滚已建文件。

### 连续管线（`scripts/keeta_stream.py`）

- 通过 `importlib` 把 v4 作为模块加载，复用 `capture`、`parse`、`context_fields`、`nodes`、`FIELDS`。
- `Ledger`：内部 SQLite（`records.sqlite`，`PRAGMA synchronous=FULL`）是提交账本；每条记录以 JSON 的 SHA-256 去重，提交后重写 CSV，并在有记录时重跑 Node 导出器生成 XLSX。快照先写临时文件再原子替换，中断不会破坏旧快照。
- `Collector`：滚动首页 feed（`content-desc='feed shopcard'`）→ 进店读详情（营业状态、地址）→ 处理明确标记 `Required` / `Select 1` 的单选必选组 → 加购 → Checkout → 取顶部与费用页 XML → 合并为一条记录。已有可结算购物车时优先读取，不重复加购。
- 停止条件：页面出现限流/验证文案、购物车冲突、地址无法确认、连续三店失败、页面树为空（锁屏）。停止时原因写入会话目录，已提交记录保留。
- 证据保留：最近 `--keep-screenshots`（默认 10）次尝试的 PNG；更早的 XML 转 gzip；已提交记录永久保留。

### 输出与目录

- `outputs/final/` — 用户只看这里：`latest_*.xlsx/.csv`（单条轮次）或 `continuous_<会话时间戳>.xlsx/.csv`（连续会话）；`history/` 为迁移前旧样例。
- `outputs/internal/runs/<轮次>/` — 原始 XML/PNG/JSON、`evidence.json`、`draft.*`、日志、`publication.json`。
- `outputs/internal/streams/<会话>/` — 账本、逐次尝试证据、失败日志。
- `outputs/` **整个目录被 `.gitignore` 忽略**，是本地交付物，不要试图提交；文档里链接到 `outputs/...` 的路径只在本机有效。

## 数据口径（违反会污染结果）

- 30 字段顺序以 `keeta_scripe-v4.py` 的 `FIELDS` 为准，中文列名来自 `assets/keeta-br-结算页字段样例.xlsx` 与 README 表格。
- 金额一律整数「分」，BRL 不做汇率换算（R$ 45.00 = 4500）。CSV 用 ISO 时间；XLSX 的采集时间按圣保罗本地时间显示（导出脚本手工做 UTC 换算，不要改成 `new Date(iso)`）。
- `crawl_time` 用带 `-03:00` 偏移的 ISO 时间；`batch_no` = 采集日期 `YYYYMMDD`。
- ETA：页面给的是预计送达时刻区间（`Est. arrival 14:09-14:24`），`ceta_min/max` = 区间减同页捕获时间后向上取整的分钟数。过期窗口、非午夜附近却出现负时差、超过 6 小时一律留空，不要截断为 0。
- `account_type`：0 单 → 0，1–4 单 → 1，≥5 单 → 2。只有订单页明确显示 `No orders yet` 才算 0；不能数可见订单卡。
- 服务费页面只有单一价格时，`service_original` 与 `service_final` 都填该值。
- 免费配送：页面显示 `Free` 时 `delivery_final = 0`，`delivery_original` 仍取划线价。
- `shop_status` 只在页面明确出现 `Open` / `Closed` 时填 open/close；`Closes at 22:30` 不代表当前 close。
- 不可见/未读取的字段保持 `None`（CSV 为空），并在 `field_sources` 写明原因；不要用地理解码、推测或旧轮次数据补齐冒充本轮结果。当前常态是 22/30 左右，缺失项包括坐标、`shop_id`、`distance`、`account_id`、`is_member` 等。
- 地址栏仍显示 `Select a delivery address` 时，提示气泡不是已选地址：不填 `crawl_address`/`city_name`，也不发布到 final。

## 安全与操作边界（必须保持）

- **绝不下单/支付**：stream 的 `click()` 直接拒绝 `place order` / `fazer pedido` / `pay now`；v4 不点 Place order。不要新增任何提交订单路径。
- 出现限流、验证码或 `Access error` 时暂停并保留已采结果，不换 IP/账号/设备去绕过。
- `capture()` 用 `SENSITIVE` 正则把含 `@`、用户名、电话号码的节点涂黑并写 `[redacted]`；文档、截图、提交里都不得出现密码、Cookie、验证码、联系电话或个人信息。
- 不修改账号、优惠、安全权限，不自动勾选可选规格，不清除未知购物车。

## 文档与代码索引

- `README.md` — 30 字段表、口径说明、用户入口、当前状态。
- `project.md` — 需求、账号/地址池、包名、工具链、文档命名规则。
- `TODO.md` — 唯一状态跟踪表（A 环境、B 业务待确认 B1–B11、C 管线、D 边界）。
- `docs/keeta-rerun-guide.md` — 单条重跑、导出与发布规则。
- `docs/keeta-continuous-guide.md` — 连续采集、恢复、证据保留。
- `docs/keeta-debug-guide.md` — 设备操作步骤（只有怎么做，没有状态）。
- `docs/oc-keeta-field-coverage.md` — 逐字段来源与 ETA/账号口径调查。
- `docs/oc-keeta-access-and-scale-research.md` — 官方 API、条款与规模化路线复核（2026-10-23）。
- `docs/keeta-checkout-fields-cn.md` — pt-BR 界面文案中文对照。
- `docs/ac-br-抓取小结.md` — 早期截图样例与金额核对。
- `docs/keeta-brazil-research.md` — 巴西市场背景。
- `assets/` — 需求截图、字段样例工作簿、历史设备 XML/PNG（受 `.gitignore` 白名单保护）。

`scripts/keeta_scripe-v1.py` … `v3.py`、`keeta_capture.py`、`test1.py` 是历史版本（流程已失效；`keeta_capture.py` 还硬编码旧序列号 `f753a0f3` 和绝对路径），只作参考，不要在其上继续开发。当前维护入口是 `keeta_scripe-v4.py` + `keeta_stream.py` + 两个 `.mjs` 导出器。

## 文档与提交约定

- 文档用中文、标题 + 短段落 + 连字符列表；保留现有中文术语，除非明确要求翻译。
- 按来源前缀命名研究文档：`p1`=Perplexity、`oc`=OpenAI Codex、`ac`=Anthropic Claude、`mm`=Meta Muse；操作类文档用普通描述名。新参考图沿用 `weixin-4.png` 序号。
- 提交用 `docs:` / `chore:` / `feat:` + 简洁祈使句。**显式 `git add <文件>`，不要 `git add -A`**：本目录曾有并发 agent 会话留下无关的暂存重命名。
- 修改文档后要复核引用的路径/图片仍然存在；文件在本项目里被多次改名和搬迁。

## 已知文档漂移

`AGENTS.md` 仍写着「没有脚本、没有测试、POCO X3」，与现状不符：已有维护中的 v4/stream 脚本、15 个离线测试和 POCO X6（`979f0245`）。发生冲突时以 `README.md`、`TODO.md`、操作指南和代码为准；若改动相关行为，顺手把 `AGENTS.md` 同步到当前状态。
