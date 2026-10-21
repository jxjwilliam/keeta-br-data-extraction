# Repository Guidelines

## Project Structure

Docs-only repo for a Keeta (美团外卖巴西站) data-extraction project. There is no application source code, dependency manifest, or test suite.

- `project.md`: canonical requirements — extraction scope, volume (15000/次, 2 次/周), duration, budget, the 30-field spec with Chinese column names, and the toolchain (POCO X3 NFC + scrcpy + Android debug mode).
- `notes-todos.md`: **the tracker** — status, open decisions (B1–B11), next steps. Read this first for project state.
- `docs/keeta-debug-guide.md`: how to drive the phone (adb, scrcpy, uiautomator dump, BR env setup) — procedures only, no status.
- `docs/keeta-brazil-research.md`: market background and the "consumer app only, no public API" constraint.
- `docs/oc-scrape-findings.md`: web-side research transcript — working URLs, share-link parameters (`shopId`, `region=BR`), and what the sandbox could and could not open.
- `docs/ac-br-抓取小结.md`: the transcribed checkout sample and amount reconciliation.
- `keeta-checkout-fields-cn.md`: pt-BR checkout-page UI copy not covered by the workbook.
- `docs/p1.md`: stub — its content was merged into `docs/keeta-brazil-research.md`.
- `assets/keeta-br-结算页字段样例.xlsx`: the 30-field checkout-page spec (5 sheets) + sample data. Tracked in git.
- `assets/weixin-1.png` … `assets/weixin-3.png`: requirement screenshots; red boxes mark the fields to extract. `weixin-1` = BRD long image, `weixin-3` = checkout page with red boxes. `assets/p3.xml` / `assets/p3.png` = the home-screen uiautomator dump. All tracked; only `*.mp4` (e.g. `keeta_test.mp4`) is git-ignored.

**Naming convention (from `project.md`):** source-derived research docs are prefixed with the source that produced them — `p1` = Perplexity, `oc` = OpenAI Codex, `ac` = Anthropic Claude, `mm` = Meta Muse. When adding such a doc, prefix it accordingly rather than inventing a new scheme. Operational docs (tracker, setup guide, research digests) use plain descriptive names.

## Build, Test, and Development Commands

None exist. Do not guess commands like `npm test` or `make build`. Use `rg --files` to list files. When adding executable code, document exact setup/run/test commands next to its manifest.

## Extraction Rules (from `project.md` §采集字段, `docs/ac-br-抓取小结.md` and `docs/oc-scrape-findings.md`)

These constraints are easy to violate — check them before writing extraction logic or filling sample data:

- Never fabricate values. If a field is not visible in a source page or screenshot (e.g. service-fee original price, discounted subtotal), leave it empty and say so. Absent in the sample: `account_id`, `shop_id`, `shop_address`, `distance`, `crawl_lat/lng`, `shop_lat/lng`, `account_type`, `is_member`.
- `07:12–07:27` is a delivery *time window*, not a duration in minutes. `eta_min`/`eta_max` need collection time, date, and local timezone before any duration calculation.
- Verify checkout arithmetic before using a sample: subtotal + delivery fee + service fee = total; original − discounted = discount amount. Do not double-count discounts.
- Amounts are BRL (`R$`); do not convert currencies — store them as integer *cents* per the spec (R$ 45.00 = 4500 分).
- Service fee has a single price in the sample: fill both `service_original` and `service_final` with 99 分 rather than leaving one blank or inventing a discount.
- Distinguish *applied* discounts from visible-but-unused promotions (e.g. "Cupom 1 disponível – até R$ 15,75 OFF"); never combine them in arithmetic.
- Record collection conditions (address, quantity, account, promotion, timestamp) with each live sample.
- Batch planning context: per-store point pool at 1–2/2–3/3–4/4–5/5–6 km (5 points each), plus account pool, rate limits, and closed-store rollback — see B6–B8 in `notes-todos.md`.
- The delivered sample is still a screenshot transcription, not a live quote. The phone-side path (adb → uiautomator dump of P3) now works but has not yet produced a live checkout sample; see C1–C3 in `notes-todos.md`. Do not present sandbox web results as live data.

## Coding Style & Naming Conventions

Markdown with headings, short paragraphs, hyphenated lists. Content is Chinese — preserve existing Chinese terminology unless a translation is explicitly requested. New reference images follow the numbered pattern: `weixin-4.png`. No formatter is configured; no indentation rules exist yet — set them with the first implementation.

## Testing Guidelines

No test framework. For documentation changes, verify file paths, image references, and consistency with the extraction scope — **files have been renamed and relocated repeatedly mid-session, so re-check that referenced paths still resolve before committing.** Future extraction tests should cover field parsing, missing values, duplicate records, and batch sizes with reproducible fixtures.

## Commits

Git is initialized; use concise, imperative subjects with conventional prefixes (`docs:`, `chore:`, `feat:`). Example: `docs: clarify extraction fields`. Pull requests should state validation performed. Include annotated screenshots when changing field-selection behavior.

**Stage explicitly, not with `git add -A`.** Multiple agent sessions have worked in this directory concurrently and left unrelated staged renames; a blanket add sweeps them into your commit. Check `git status` before staging.

## Configuration & Data Handling

Keep credentials, session cookies, OTPs, and collected personal data out of documents, screenshots, and commits. Document required configuration without embedding secret values. Never save passwords or cookies in docs. The `.gitignore` covers `.env`/session/cookie files, `.DS_Store`, Excel lock files (`~$*.xlsx`), and future Python/Node artifacts — extend it rather than committing such files.
