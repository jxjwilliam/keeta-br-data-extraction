# Keeta 单条重跑与输出

## 用户查看的文件

- `outputs/final/latest_YYYYMMDD_HHMMSS.xlsx`、`outputs/final/latest_YYYYMMDD_HHMMSS.csv`：按圣保罗采集时间命名，每轮独立保留。
- `outputs/final/history/`：迁移前的历史 XLSX/CSV。
- `outputs/internal/runs/<轮次>/`：原始证据、逐字段来源、日志、预览和草稿。实验、失败记录也留在这里。

不需要在内部目录寻找交付文件。旧样例标记 `needs-review`，不会自动成为 latest。当前尚无新版完整实机验收结果，正式时间戳结果暂不存在。

## 环境

- `python3` 需要 `uiautomator2`、`Pillow`；系统 `adb` 可访问手机。
- 安装 Python 依赖：`python3 -m pip install uiautomator2 Pillow`。
- XLSX 导出使用 Codex bundled Node 和 `@oai/artifact-tool`。默认运行时目录为 `~/.cache/codex-runtimes/codex-primary-runtime/dependencies`；若迁移环境，通过 `KEETA_RUNTIME` 指定包含 `node/bin/node` 和 `node/node_modules` 的目录。运行时缺失时只保留内部草稿，不发布半套结果。
- 查看设备：`adb devices -l`。POCO X6 当前序列号 `979f0245`。
- 手机已登录巴西 Keeta，保留用户指定的地址与账号。scrcpy 用于观看执行效果。

## 执行

当前为 Checkout 时，只读取并自动滚动：

```bash
python3 scripts/keeta_scripe-v4.py --serial 979f0245
```

当前店铺、购物车为空、指定商品名称已可见时，自动加一份简单商品并进入 Checkout：

```bash
python3 scripts/keeta_scripe-v4.py --serial 979f0245 --item 'Shoyu Lamen (6% Off) - Shoyu Kikkoman / Importado do Japão'
```

此模式未实现购物车清理或必选规格选择。缺少明确按钮则停止；不要对已有商品的购物车重复运行加购模式。程序不点击 Place order。需要人工协助时，提前说明并等待完成。

采集轮次使用圣保罗时间加微秒命名。自动捕获、解析、核对，再使用 `scripts/export_keeta.mjs` 生成 XLSX。只有地址确实选中、城市和地址有值、金额与跨页总额通过检查时，才发布 XLSX/CSV 并保存本轮时间戳文件，不覆盖旧结果。同一秒时间戳若已存在则拒绝发布；任一文件复制失败会撤回本次新建的另一文件。字段仍可部分留空，latest 不表示 30 项已全部取得。

XLSX 主表采集时间按圣保罗本地时间显示，来源说明保留带 UTC 偏移的原始 ISO 时间。CSV 使用 ISO 时间；金额均为整数分。中间文件不会混进 final。

## 上下文与重放

同一轮采集 `shop-info.xml/json`、`orders.xml/json`，再执行：

```bash
python3 scripts/keeta_scripe-v4.py --serial 979f0245 --context-dir outputs/internal/runs/本轮上下文目录
```

要求同店铺且上下文时间与结算相差不超过 5 分钟；还须确保同设备、同账号。完整自动采集这些前置页面的导航尚未串联验收。

只解析研究证据或旧报价，不访问手机，也不更新 latest：

```bash
python3 scripts/keeta_scripe-v4.py --inspect-context-dir outputs/internal/runs/keeta-field-research-20261022
python3 scripts/keeta_scripe-v4.py --parse-dir outputs/internal/runs/本轮证据目录
```

仅在内部目录写 `context-fields.json` 或 `evidence.json`、`draft.csv`。历史证据若需重新解析，应先复制到新的内部轮次，以免覆盖原摘要。

从已解析证据生成文件并执行同样的发布检查：

```bash
python3 scripts/keeta_scripe-v4.py --export-run outputs/internal/runs/本轮证据目录
```

## 校验

```bash
python3 -m unittest discover -s tests -v
```

离线测试使用 `tests/fixtures/`，不依赖输出目录。解析器核对商品原价与 Subtotal、分项折后合计与 Total、原价差额与已应用优惠、跨页总额一致。失败不写正常结果；地址未确认时只保留内部草稿。

ETA 按用户确认的向上取整分钟计算。详情见 `docs/oc-keeta-field-coverage.md`。完整首页选店、多商品、必选规格、账号一致性和批量异常恢复仍未验收。

示例：`latest_20261022_133317.xlsx` 与 `latest_20261022_133317.csv`。不创建或覆盖固定名称的 `latest.xlsx`、`latest.csv`；按文件名时间戳选择需要的轮次。
