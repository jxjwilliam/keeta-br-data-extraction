# Repository Guidelines

## Project Structure

Docs-only repo for a Keeta (美团外卖巴西站) data-extraction project. There is no application source code, dependency manifest, or test suite.

- `requirements.md`: extraction scope, volume (15000/次, 2 次/周), duration, budget. Root-level and canonical — keep it there.
- `keeta-br-抓取小结.md`: root-level session summary — app verification, the 30-field spec pointer, sample checkout data, and next steps. Read this first for current project state.
- `docs/keeta-scrape-findings.md`: verified scraping research: working URLs, share-link parameters (`shopId`, `region=BR`), checkout-field samples transcribed from screenshots, and data-quality caveats. Read this before any extraction work.
- `docs/keeta-1.md`: background on Keeta in Brazil.
- `docs/keeta-br-结算页字段样例.xlsx`: checkout-page field sample table.
- `assets/weixin-1.png` … `weixin-3.png`: requirement screenshots; red boxes mark the fields to extract. Image details live in `docs/keeta-scrape-findings.md` (third image is authoritative).

## Build, Test, and Development Commands

None exist. Do not guess commands like `npm test` or `make build`. Use `rg --files` to list files. When adding executable code, document exact setup/run/test commands next to its manifest.

## Extraction Rules (from `docs/keeta-scrape-findings.md`)

These constraints are easy to violate — check them before writing extraction logic or filling sample data:

- Never fabricate values. If a field is not visible in a source page or screenshot (e.g. service-fee original price, discounted subtotal), leave it empty and say so.
- `07:12–07:27` is a delivery *time window*, not a duration in minutes. `eta_min`/`eta_max` need collection time, date, and local timezone before any duration calculation.
- Verify checkout arithmetic before using a sample: subtotal + delivery fee + service fee = total; original − discounted = discount amount. Do not double-count discounts.
- Amounts are BRL (`R$`); do not convert currencies — but store them as integer *cents* per the spec (R$ 45.00 = 4500 分).
- The full spec is 30 fields defined in `docs/keeta-br-结算页字段样例.xlsx` (5 sheets: 说明 / 字段中文对照 / 样例数据 / 红框原文对照 / 参考截图). Fields absent from screenshots stay empty (e.g. `account_id`, `shop_id`, `distance`, `crawl_lat/lng`) — never fill them in.
- Service fee has a single price: fill both `service_original` and `service_final` with 99 分 rather than leaving one blank or inventing a discount.
- Distinguish *applied* discounts from visible-but-unused promotions (e.g. "Cupom 1 disponível"); never combine them in arithmetic.
- Record collection conditions (address, quantity, account, promotion, timestamp) with each live sample.
- Batch planning context: per-store point pool at 1–2/2–3/3–4/4–5/5–6 km (5 points each), plus account pool, rate limits, and closed-shop rollback — see section 五 of `keeta-br-抓取小结.md`.

## Coding Style & Naming Conventions

Markdown with headings, short paragraphs, hyphenated lists. Content is Chinese — preserve existing Chinese terminology unless a translation is explicitly requested. New reference images follow the numbered pattern: `weixin-4.png`. No formatter is configured; no indentation rules exist yet — set them with the first implementation.

## Testing Guidelines

No test framework. For documentation changes, verify file paths, image references, and consistency with the extraction scope (the paths above have moved before — check references resolve). Future extraction tests should cover field parsing, missing values, duplicate records, and batch sizes with reproducible fixtures.

## Commits

Git is initialized; use concise, imperative subjects with conventional prefixes (`docs:`, `chore:`, `feat:`). Example: `docs: clarify extraction fields`. Pull requests should state validation performed. Include annotated screenshots when changing field-selection behavior.

## Configuration & Data Handling

Keep credentials, session cookies, OTPs, and collected personal data out of documents, screenshots, and commits. Document required configuration without embedding secret values. Never save passwords or cookies in `docs/`.
