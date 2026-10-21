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
| Home/store screen dump (`assets/p3.xml`, 40 readable text nodes) | Done — UI-XML route looks viable |
| Logged-in BR account, P3 reached | Pending |
| `uiautomator dump` check on P3 | Pending (decides UI-XML vs OCR route) |

> 进度、阻塞项与下一步统一维护在 `notes-todos.md`；本文件只讲**怎么做**。

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

The BRD says 5,000/week, but its formula (2 cities x 500 shops x 1 x 1 account type x 5 distance bands x 2 rounds) gives 10,000. project.md says 30,000/week, which equals the formula with 3 account types. Confirm before sizing devices — tracked as **B1** in `notes-todos.md`.

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
scrcpy --record=keeta_test.mp4                    # record evidence video
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

---

## 9. Next Steps

进度、阻塞项与下一步统一维护在 `notes-todos.md`（A 组环境、C 组管线）。顺序：切 pt-BR → 登录 BR 账号触达 P3 → 在 P3 重跑 dump（`assets/p3.xml` 现存的是首页，不是 P3）→ 建 PoC 管线 → 定量级与设备池 → 再考虑 API replay spike。
