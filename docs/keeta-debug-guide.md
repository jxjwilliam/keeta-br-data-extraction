# Keeta BR: P3 ETA Scraping, Setup & Debug Guide

Updated: 2026-10-21 | Scope: Keeta Brazil (São Paulo + Santos), Android app, P3 checkout page ETA/fee monitoring

---

## 1. Summary

- **Goal:** weekly city-level monitoring of the ETA and fees shown on Keeta's P3 page (`Pedir agora`, the checkout), to track ETA gap vs competitors.
- **Target app:** `com.sankuai.sailor.afooddelivery` (Keeta - Food Delivery, developer KANGAROO LIMITED / Meituan). Reference version 3.12.501. Pin the version and disable auto-update.
- **Market context:** pilot in Santos and São Vicente from 2025-10-30; Greater São Paulo (9 cities) from 2025-12-01. Late-delivery policy "Horário Garantido" gives coupons up to R$50; the guarantee threshold in the BRD screenshot is the ETA window end + 15 min.
- **Volume (project.md):** 15,000 samples per run, 2 runs/week, 30,000/week, 1 year, initial budget 200w.
- **Never place orders.** Stop at P3; do not tap `Fazer pedido`.

### Current status (from your screenshots)

| Item | Status |
|---|---|
| POCO X3 NFC (M2007J20CG, Android 12) connected via USB | Done |
| adb recognizes the device (`f753a0f3`) | Done |
| scrcpy 5.0.1 mirroring on MacBook | Done |
| Keeta installed, home screen visible | Done |
| Address shown: "R. Floriano Peixoto, 1 - Sé, São..." (São Paulo, Sé) | Done |
| App UI language | **English** (BRD screenshots are pt-BR); see section 4 |
| Feed-list dump (`assets/feed-pizza.xml` / `.png`) | Done — shop cards expose no text; OCR hybrid needed |
| Shop page + cart dumps (`assets/shop.xml`, `assets/p3.xml` @ 13:04) | Done — native TextViews, fields readable |
| Logged-in BR account, P3 checkout reached | Done 2026-10-21 13:05 — `assets/p3.png`; **no order placed** |
| P3 XML dump | **Blocked** — `could not get idle state`; use uiautomator2 with `waitForIdleTimeout=0` |
| adb input injection | **Blocked** — MIUI `INJECT_EVENTS`; enable *USB debugging (Security settings)* or use accessibility clicks |

> 进度、阻塞项与下一步统一维护在 `TODO.md`；本文件只讲**怎么做**。

---

## 2. Key Concepts

- **ETA:** the delivery-time window on P3, e.g. `Previsão 07:12-07:27` -> `ceta_min`, `ceta_max`.
- **ETA gap (interpretation, the BRD does not define it):** displayed ETA minus a benchmark (competitor or Keeta's earlier weeks), compared at the same shop/distance band/hour slot/account tier. It is displayed ETA, not actual delivery time, since no orders are placed.
- Store ETA as **minutes** (`window_start − crawl_time`), not clock times.
- Three account tiers: new (0 orders), mid (1-4), old (>=5); keep the delivery address and city consistent with the crawl city.

---

## 3. Technical Approach

**Recommendation:** UI automation on real devices as the baseline, plus a 1-2 week time-boxed spike on API replay. Scale via replay only if request signing is tractable.

| Approach | Pros | Cons |
|---|---|---|
| UI automation (uiautomator2/Appium) | Screenshot evidence matches the BRD; avoids request signing | ~25-40 s/sample; needs a device pool; breaks on UI changes |
| API replay (mitmproxy/Frida) | ~100x cheaper per sample; structured JSON | Needs root + SSL-pinning bypass + signature reversal; higher ban risk |

**Capacity:** 15,000 samples over a 12 h window is ~1,250/h. At ~30 s/sample/device that needs ~10-12 devices.

```
Scheduler (Wed/Sat, 11:00-22:59 BRT)
  -> Planner: shop_list x account tier x distance band (1-6 km) x hour slot, rolling backfill
  -> Queue (Redis/Celery)
  -> Device workers: 1 device = 1 account + 1 BR proxy + mock GPS
       deeplink(shopId) -> add item (meet minimum) -> Pedir agora
       -> XML dump + screenshot (evidence) -> clear cart (never place order)
  -> Raw store (JSONL + screenshots in S3/MinIO)
  -> Normalizer -> QA -> CSV/XLSX (batch_no = YYYYMMDD)
```

### Red-box field mapping (P3)

| On screen | Fields | Parsing |
|---|---|---|
| `Previsão 07:12-07:27` | `ceta_min`, `ceta_max` | regex window, subtract `crawl_time` |
| Address line | `crawl_address` | text node |
| Merchant name | `shop_name` | text node |
| `3 x Tapioca Com Nutella` | `product_info` | text node |
| Subtotal | `product_original`, `product_final` | `R$ 45,00` -> 4500 (cents, int) |
| Taxa de entrega (struck-through + final) | `delivery_original`, `delivery_final` | struck-through = original; if absent, original = final |
| Taxa de serviço | `service_original`, `service_final` | same rule |
| Total | `total_final`, `total_original` | original = sum of originals |

**Not on P3:** `shop_id`, `shop_lat/lng/address` (input shop list), `distance` (haversine or shop page), account fields (account registry), `crawl_lat/lng` (mock GPS point), `crawl_time` (worker timestamp), `shop_status` (`close` when closed; emit a row with other fields empty).

### QA rules

- `total_final == product_final + delivery_final + service_final` (BRD example: 45.00 + 2.99 + 0.99 = 48.98).
- `delivery_original − delivery_final` equals the discount line (12.99 − 2.99 = R$10.00).
- `ceta_min <= ceta_max`, durations within a sane range.
- Sample screenshots against extracted values.

### Open item: volume mismatch in the BRD

The BRD says 5,000/week, but its formula (2 cities x 500 shops x 1 x 1 account type x 5 distance bands x 2 rounds) gives 10,000. project.md says 30,000/week, which equals the formula with 3 account types. Confirm before sizing devices — tracked as **B1** in `TODO.md`.

---

## 4. Environment Setup (Brazil)

Use a consistent Brazil profile. Region alone is not enough: the server looks at IP, GPS, SIM/network country, and the account.

1. **Network:** BR IP via VPN (testing) or BR residential/mobile proxy, one sticky IP per account (production).
2. **Location:** enable Developer options -> Select mock location app; set coordinates to São Paulo/Santos points.
3. **SIM:** remove the Canadian SIM and use Wi-Fi, or use a Brazilian eSIM.
4. **Region and time zone:** Settings -> Additional settings -> Region -> Brazil; time zone `America/Sao_Paulo` (UTC-3).
5. **Language:** use **Português (Brasil) / `pt-BR`**, not `pt-PT`.
   - System: Settings -> Additional settings -> Languages & input -> Language -> add Português (Brasil), move to top.
   - Per-app (Android 13+ only): Settings -> Apps -> Manage apps -> Keeta -> Language.
   - **Your current Keeta UI is English.** Parsing keywords (`Previsão`, `Taxa de entrega`, `Subtotal`) are Portuguese. Fix the language, or make the parser bilingual. Keep one language for the whole run.
6. **Accounts:** +55 phone number for SMS, BR delivery address, aged accounts at the 3 tiers.
7. **Google Play Services / Maps:** update both (the BRD screenshot shows "Google Play Services: atualizando", which can make location flaky).

Risk: automated access probably violates Keeta's ToS. Expect device-fingerprint, mock-GPS and velocity checks; budget for account bans.

---

## 5. adb + scrcpy on macOS

### 5.1 Install

```bash
brew install android-platform-tools scrcpy
which -a adb        # the first entry should be /opt/homebrew/bin/adb
adb version         # Android Debug Bridge version 1.0.41
```

**Gotcha you hit:** `~/miniconda3/bin/adb` was a Python script from the pip package `adb`, shadowing the real adb (`ModuleNotFoundError: No module named 'cli'`). Fix:

```bash
pip uninstall adb -y
rm -f ~/miniconda3/bin/adb
hash -r
which -a adb
```

Or put Homebrew first in `~/.zshrc`:

```bash
export PATH="/opt/homebrew/bin:$PATH"
```

Never `pip install adb`; uiautomator2 uses the system adb.

### 5.2 Phone prerequisites (MIUI)

Developer options:
- USB debugging: ON
- **USB debugging (Security settings): ON** (needs Mi account + SIM or network; required for tap/input simulation and the `--stay-awake` flag)
- Install via USB: ON
- Stay awake (screen stays on while charging): ON (alternative to scrcpy `--stay-awake`)
- USB mode: File transfer

### 5.3 Connect

```bash
adb kill-server
adb devices
```

| Output | Meaning / action |
|---|---|
| `device` | OK |
| `unauthorized` | Tap "Allow USB debugging" on the phone, tick "Always allow" |
| empty list | USB mode -> File transfer; try another cable |

### 5.4 scrcpy

```bash
scrcpy --window-title keeta                       # mirror
scrcpy --stay-awake --window-title keeta          # needs USB debugging (Security settings)
scrcpy --record=evidence.mp4                     # record evidence video (not committed: *.mp4 is git-ignored)
scrcpy --turn-screen-off --stay-awake             # mirror with phone screen off
scrcpy --max-size 1024 --max-fps 30               # lighter on bandwidth
```

**Known error:** `Permission denial: writing to settings requires android.permission.WRITE_SECURE_SETTINGS` with `stay_on_while_plugged_in`. It comes from `--stay-awake`; mirroring still works. Fix by enabling *USB debugging (Security settings)*, or drop the flag and use the "Stay awake" developer option.

Useful scrcpy shortcuts (macOS, MOD = Option on the left): `MOD+h` Home, `MOD+b` Back, `MOD+s` App switch, `MOD+f` fullscreen, `MOD+r` rotate.

### 5.5 Keeta app control via adb

```bash
# Verify install and version
adb shell pm list packages | grep sankuai
adb shell dumpsys package com.sankuai.sailor.afooddelivery | grep versionName

# Launch / stop / reset
adb shell monkey -p com.sankuai.sailor.afooddelivery -c android.intent.category.LAUNCHER 1
adb shell am force-stop com.sankuai.sailor.afooddelivery
adb shell pm clear com.sankuai.sailor.afooddelivery        # wipes login/data; use with care

# Current foreground activity
adb shell dumpsys activity activities | grep mResumedActivity

# Screenshot (keeps evidence on the Mac)
adb exec-out screencap -p > shot_$(date +%Y%m%d_%H%M%S).png

# Logs for the app process
adb logcat --pid=$(adb shell pidof -s com.sankuai.sailor.afooddelivery)

# Basic input (for quick tests; use uiautomator2 for real runs)
adb shell input tap 540 1200
adb shell input swipe 540 1800 540 600 300
adb shell input text "pizza"
adb shell input keyevent KEYCODE_BACK
```

Check the share-link deeplink (shopId from project.md) before relying on it in the pipeline:

```bash
adb shell am start -a android.intent.action.VIEW -d "<keeta share link with shopId=...&region=BR>"
```

---

## 6. Critical Check: Can We Read P3 as Text?

Log in, add one item to the cart, open P3 (`Pedir agora`), then:

```bash
adb shell uiautomator dump /sdcard/p3.xml
adb pull /sdcard/p3.xml .
adb exec-out screencap -p > p3.png
grep -E "Previsão|Subtotal|Taxa de|Total" p3.xml
```

- **Text found:** parse the XML directly (no OCR); the UI-automation route is viable.
- **Only empty View/WebView/Flutter containers:** fall back to OCR (PaddleOCR or Tesseract with the `por` model); lower throughput.

This result decides the route. Do it first.

### 6.1 What the 2026-10-21 dumps actually showed

**Screen-by-screen accessibility is not uniform.** The feed list, shop page and checkout page need different strategies:

| Screen | Evidence | Result |
|---|---|---|
| Feed / search results | `assets/feed-pizza.xml`, 134 nodes, 24 with text or `content-desc` | Shop cards are `ViewGroup` with only `content-desc="feed shopcard"` + promo chips. Name, rating, fee, ETA, distance are **not** in the tree. |
| Shop detail | `assets/shop.xml`, 45 text nodes | Native `TextView`s. Shop name, `4.9 (50+)`, `10–25 min`, `Free / R$7.99`, item names and `After voucher` prices all readable. |
| Cart drawer | `assets/p3.xml` @ 13:04, 130 KB | Native text. `Subtotal R$42.90`, `Discount -R$12.33` (Promo -2.14, Voucher -10.19), `Total R$30.57`. Shop page text remains underneath the overlay. |
| Checkout (P3) | `assets/p3.png` @ 13:05 | Reached, screenshot only. XML dump failed; fee rows still unconfirmed. |

**Feed list needs XML bounds + OCR.** Crop each `feed shopcard` by its `bounds`, upscale 2x and run Tesseract. A sandbox test read `Futuro Kereitorio / 5.0 (40+) / R$4.99 / 26–41 min / 5.2 km` and `Massa do wild / Free / 10–25 min / 1.7 km` correctly. Struck-through original prices are unreliable (`R$14.99` → `2$44-99`) because of the line through the digits; the final fee, ETA and distance are usable. Validate with `R\$ ?\d+[.,]\d{2}`, `\d+[–-]\d+ min`, `\d+[.,]\d km`.

**Checkout arithmetic confirmed from the screenshot.** `42.90 + 7.99 + 0.99 − 10.13 = 41.75`: item original 42.90, delivery original 7.99, service fee 0.99, applied discount 10.13 (item 5% = 2.14 + free delivery 7.99). The cart's `−10.19` voucher was not applied at checkout (`Select at checkout`). This matches the BRD's P3 structure; only the visible fee rows remain to be dumped.

**Timezone mismatch.** Device status bar showed `13:05` (Vancouver) while `Est. arrival` read `17:25-17:40`, i.e. São Paulo time (UTC-3). Set the phone to `America/Sao_Paulo` before production runs, or record the UTC offset with `crawl_time`; otherwise ETA and crawl time are not comparable.

**Two dump pitfalls.**

1. `uiautomator dump` can fail with `ERROR: could not get idle state` when the page has a continuous animation. It writes nothing. `adb pull` then happily returns the **previous** file — always `rm` the remote file first and check `ls -l` before pulling.
2. The MIUI exception `java.io.FileNotFoundException: /data/system/theme_config/theme_compatibility.xml` is harmless system noise; the dump still succeeds.

**Workaround for idle + input injection.** `uiautomator2` dumps with `waitForIdleTimeout=0` and clicks through accessibility actions, so it avoids both the idle wait and MIUI's `INJECT_EVENTS` restriction:

```python
import uiautomator2 as u2
d = u2.connect("f753a0f3")
d.settings["waitForIdleTimeout"] = 0
open("assets/p3-new.xml", "w").write(d.dump_hierarchy())
```

### Interactive inspection

```bash
pip install uiautomator2 weditor
weditor            # click elements in the browser to see text/resource-id
```

```python
import uiautomator2 as u2
d = u2.connect()
d.app_start("com.sankuai.sailor.afooddelivery")
print(d(textContains="Previsão").get_text())
```

---

## 7. Traffic Capture (optional spike, API replay feasibility)

```bash
mitmproxy -p 8080
adb reverse tcp:8080 tcp:8080
adb shell settings put global http_proxy 127.0.0.1:8080
# ALWAYS clear when done, otherwise the phone loses connectivity:
adb shell settings put global http_proxy :0
```

Android 7+ apps ignore user CA certificates by default, so you will likely need root or Frida to bypass SSL pinning. Do this only after section 6.

---

## 8. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `ModuleNotFoundError: No module named 'cli'` | conda `adb` shadowing; see 5.1 |
| `unauthorized` | Accept the RSA prompt on the phone; `adb kill-server` |
| Taps/inputs ignored | Enable USB debugging (Security settings) |
| Phone has no internet after testing | Stale proxy: `adb shell settings put global http_proxy :0` |
| No restaurants / region error in app | Check BR IP, mock GPS, SIM country before blaming Region |
| Map/location flaky | Update Google Play Services and Google Maps |
| Parser finds no `Taxa de entrega` | UI language is English; switch to pt-BR or make the parser bilingual |
| `uiautomator dump` prints `/data/system/theme_config/theme_compatibility.xml` FileNotFoundException | MIUI system noise; the XML is still written normally |
| `ERROR: could not get idle state` | A view is animating continuously. Set the three animation scales to 0, wait 10 s, retry; if it still fails, use uiautomator2 with `waitForIdleTimeout=0` |
| `adb pull` succeeds but the XML is the previous screen | The dump failed and the old file was still on the device. Always `adb shell rm -f /sdcard/p3.xml` first and verify `ls -l` before pulling |
| `adb pull`: `No such file or directory` | The dump aborted before writing; see the idle-state row |
| `SecurityException: Injecting to another application requires INJECT_EVENTS permission` | Enable *USB debugging (Security settings)* on MIUI, or click through uiautomator2's accessibility actions instead of `adb shell input` |

---

## 9. Next Steps

进度、阻塞项与下一步统一维护在 `TODO.md`（A 组环境、C 组管线）。当前顺序：

1. 用 uiautomator2 的 `dump_hierarchy()` 抓 P3（绕过 idle 等待），确认 `Subtotal / Delivery fee / Service fee / Total` 四行是否可读。
2. 开启 *USB debugging (Security settings)*，或确认 uiautomator2 的无障碍点击可用，解决 `INJECT_EVENTS`。
3. 把手机时区改为 `America/Sao_Paulo`，再采一条完整 P3 样例，跑金额 QA。
4. 建 PoC 管线（店铺页 → 加购 → P3 → XML/OCR → 分单位整数），再定量级与设备池。
5. 最后再评估 API replay spike。
