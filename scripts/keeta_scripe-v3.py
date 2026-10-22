#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Keeta 提单页数据自动抓取 v1 (ADB + uiautomator2)

流程: 启动 Keeta -> 读账号信息 -> 逐家进店 -> 加一件高销菜 -> 进提单页(Resumo do pedido)
      -> 提取红框字段 + 截图 -> 写 30 列 CSV (BRD 字段顺序)

诚实规则 (按 William 要求):
- 只写页面上真实显示的值; 页面没有的字段留空, 绝不编造。
- 派生值只有两种, 且都是由页面显示值做算术: ceta_min/max (由 Previsão 时钟窗口换算分钟),
  total_original (各原价之和 / 总价+已用优惠)。其余一律页面直读。
- v2 全自动: 无任何人工暂停。导航/选店/加菜/规格选择/凑起送价/清购物车全部自动;
  单家失败自动跳过并继续下一家, 每步截图+控件树存 debug/ 供事后校准选择器。
- 绝不点击 "Fazer pedido" (提交订单)。

在 Mac 上运行 (POCO X3 已 USB 连接、Keeta 已登录、配送地址为账号缺省):
    pip3 install uiautomator2
    python3 keeta_scrape.py            # 默认抓 3 家店
    python3 keeta_scrape.py 5          # 抓 5 家店

输出: ~/Desktop/keeta/output/keeta_YYYYMMDD_HHMMSS.csv + 同目录 debug/ (每步截图和控件树 XML)
"""

import csv
import os
import re
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    import uiautomator2 as u2
except ImportError:
    print("缺少 uiautomator2, 先运行: pip3 install uiautomator2")
    sys.exit(1)

SP_TZ = ZoneInfo("America/Sao_Paulo")
PACKAGE = "com.sankuai.sailor.afooddelivery"
OUT_DIR = os.path.expanduser("~/Desktop/keeta/output")
DEBUG_DIR = os.path.join(OUT_DIR, "debug")

FIELDS = [
    "batch_no", "country", "platform", "city_name", "crawl_time",
    "account_id", "user_completed_orders_count", "account_type", "is_member",
    "shop_id", "shop_name", "crawl_lat", "crawl_lng", "crawl_address",
    "shop_lat", "shop_lng", "shop_address", "ceta_min", "ceta_max",
    "product_info", "product_original", "product_final",
    "delivery_original", "delivery_final",
    "service_original", "service_final",
    "total_original", "total_final", "distance", "shop_status",
]

# ---------------- 工具函数 ----------------

def now_sp():
    return datetime.now(SP_TZ)


def money_to_cents(s):
    """'R$ 1.234,56' / 'R$ 45,00' / 'R$ 2.99' -> 分(int)。解析不了返回 None。"""
    if s is None:
        return None
    s = s.replace("R$", "").strip().replace("\u00a0", "")
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return int(round(float(s) * 100))
    except ValueError:
        return None


MONEY_RE = re.compile(r"R\$\s*[\d\.,]+")

def texts_of(d):
    """返回当前界面所有可见文本(按控件树顺序)。"""
    import xml.etree.ElementTree as ET
    xml = d.dump_hierarchy()
    root = ET.fromstring(xml)
    out = []
    for node in root.iter("node"):
        t = (node.attrib.get("text") or "").strip()
        if t:
            out.append(t)
    return out, xml


def joined(texts):
    return "\n".join(texts)


def tap_text(d, *candidates, timeout=6):
    """按文本点第一个命中的元素; 找不到返回 False。绝不点 Fazer pedido。"""
    for c in candidates:
        if "fazer pedido" in c.lower():
            continue
        el = d(text=c)
        if el.exists(timeout=timeout):
            el.click()
            return True
    return False


def tap_contains(d, *candidates, timeout=6):
    for c in candidates:
        if "fazer pedido" in c.lower():
            continue
        el = d(textContains=c)
        if el.exists(timeout=timeout):
            el.click()
            return True
    return False


def manual(step_cn, step_pt=""):
    print("\n>>> 需要你手动操作: %s %s" % (step_cn, ("(" + step_pt + ")") if step_pt else ""))
    print(">>> 在 scrcpy 镜像里完成后, 回到这个终端按回车继续...")
    input()


def save_debug(d, tag):
    os.makedirs(DEBUG_DIR, exist_ok=True)
    ts = datetime.now().strftime("%H%M%S")
    try:
        d.screenshot(os.path.join(DEBUG_DIR, "%s_%s.png" % (ts, tag)))
    except Exception:
        pass
    try:
        _, xml = texts_of(d)
        with open(os.path.join(DEBUG_DIR, "%s_%s.xml" % (ts, tag)), "w", encoding="utf-8") as f:
            f.write(xml)
    except Exception:
        pass
    print("    [debug 已存: %s]" % tag)


KNOWN_LABELS = ("subtotal", "taxa de entrega", "taxa de serviço", "taxa de servico",
                "delivery fee", "service fee", "total")

def _is_other_label(line, current):
    low = line.lower()
    return any(lab in low and lab != current for lab in KNOWN_LABELS)

def parse_money_after(texts, label, max_lookahead=4):
    """在文本序列里找到 label, 返回其行内及其后紧邻纯金额行里的金额(分)列表。
    遇到下一条已知标签行即停, 避免吞掉下一行费用的金额。"""
    lab = label.lower()
    for i, t in enumerate(texts):
        if lab in t.lower():
            vals = []
            for m in MONEY_RE.findall(t):
                c = money_to_cents(m)
                if c is not None:
                    vals.append(c)
            for j in range(i + 1, min(i + 1 + max_lookahead, len(texts))):
                line = texts[j]
                if _is_other_label(line, lab):
                    break
                ms = MONEY_RE.findall(line)
                if not ms:
                    if vals:
                        break
                    continue
                for m in ms:
                    c = money_to_cents(m)
                    if c is not None:
                        vals.append(c)
            return vals
    return []

# ---------------- 字段解析 ----------------

def parse_checkout(texts):
    """从提单页(Resumo do pedido)文本里提取红框字段。返回 dict(值为分或原文)。"""
    r = {}
    blob = joined(texts)

    # 商品明细行: '3 × Tapioca Com Nutella' 或 '3 x ...'
    items = []
    for t in texts:
        m = re.match(r"^\s*(\d+)\s*[×xX]\s*(.+)$", t)
        if m and "R$" not in t:
            items.append("%s × %s" % (m.group(1), m.group(2).strip()))
    if items:
        r["product_info"] = "; ".join(items)

    sub = parse_money_after(texts, "Subtotal")
    if sub:
        r["product_original"] = sub[0]

    # 配送费: 葡/英标签都试; 标签附近出现 Free/Grátis 表示券后为 0
    fee_label = None
    for cand in ("Taxa de entrega", "Delivery fee"):
        if any(cand.lower() in t.lower() for t in texts):
            fee_label = cand
            break
    fee = parse_money_after(texts, fee_label) if fee_label else []
    free_near_fee = False
    if fee_label:
        for i, t in enumerate(texts):
            if fee_label.lower() in t.lower():
                free_near_fee = any(x.strip().lower() in ("free", "grátis", "gratis")
                                    for x in texts[i:i + 3])
                break
    if fee:
        r["delivery_original"] = max(fee)
        r["delivery_final"] = 0 if free_near_fee else min(fee)
    elif free_near_fee:
        r["delivery_final"] = 0

    svc = parse_money_after(texts, "Taxa de serviço") or parse_money_after(texts, "Taxa de servico") \
        or parse_money_after(texts, "Service fee")
    if svc:
        r["service_original"] = svc[0]
        r["service_final"] = svc[0]

    # Total 行: 排除小节标题 'Total do pedido', 取最后一个以 Total 开头的标签行
    tot = []
    for i, t in enumerate(texts):
        low = t.strip().lower()
        if low.startswith("total") and "do pedido" not in low:
            cand = parse_money_after(texts[i:], "Total")
            if cand:
                tot = cand
    if tot:
        r["total_final"] = tot[0]  # Total 行的金额是第一个; 其后可能是优惠说明行

    # 已应用优惠: 'Desconto de R$ 10,00 aplicado' / 'Discount of R$ 10.00 applied'
    m = re.search(r"[Dd]esconto de\s*(R\$\s*[\d\.,]+)", blob) \
        or re.search(r"[Dd]iscount of\s*(R\$\s*[\d\.,]+)", blob)
    discount = money_to_cents(m.group(1)) if m else None

    # 商品券后价: 无商品级折扣行时, 券后价=原价(页面实付即原价, 非编造)
    if "product_original" in r and "product_final" not in r:
        r["product_final"] = r["product_original"]

    # 总价原价: 各原价之和 (派生, 来源均为页面显示值)
    parts = [r.get("product_original"), r.get("delivery_original"), r.get("service_original")]
    if all(p is not None for p in parts):
        r["total_original"] = sum(parts)
    elif discount is not None and "total_final" in r:
        r["total_original"] = r["total_final"] + discount

    # 预计送达窗口 Previsão 07:12-07:27 -> ceta_min/max (分钟, 相对圣保罗当前时间换算)
    m = re.search(r"(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})", blob)
    if m:
        n = now_sp()
        h1, m1, h2, m2 = (int(x) for x in m.groups())
        t1 = n.replace(hour=h1, minute=m1, second=0, microsecond=0)
        t2 = n.replace(hour=h2, minute=m2, second=0, microsecond=0)
        r["ceta_min"] = max(0, int((t1 - n).total_seconds() // 60))
        r["ceta_max"] = max(0, int((t2 - n).total_seconds() // 60))
    else:
        # 另一种显示: '30-45 min'
        m = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*min", blob)
        if m:
            r["ceta_min"] = int(m.group(1))
            r["ceta_max"] = int(m.group(2))

    # 配送地址行 (提单页顶部, 含 São Paulo / SP)
    for t in texts:
        if ("São Paulo" in t or "Sao Paulo" in t) and ("Rua" in t or "Av." in t or "SP" in t):
            r["crawl_address"] = t
            r["city_name"] = "São Paulo"
            break
    return r


def parse_shop_page(texts):
    """店铺页可得字段: 店名候选/距离/地址/状态。拿不准的留空。"""
    r = {}
    blob = joined(texts)
    m = re.search(r"(\d+[.,]?\d*)\s*km", blob)
    if m:
        r["distance"] = m.group(1).replace(".", ",") + " km"
    if re.search(r"\bFechado\b|Fecha às|Abre às", blob):
        r["shop_status"] = "close"
    else:
        r["shop_status"] = "open"
    for t in texts:
        if t.startswith("Endereço") or ("Rua" in t and "São Paulo" in t and len(t) > 12):
            r["shop_address"] = t.replace("Endereço:", "").strip()
            break
    return r

# ---------------- 主流程 (v3: 按真实英文界面/行结构重写) ----------------

import xml.etree.ElementTree as ET

BLOCKED_WORDS = ("fazer pedido", "place order", "pagar agora", "pay now",
                 "finalizar compra", "confirmar pedido")

def _bounds(node):
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
    if not m:
        return None
    l, t, r, b = (int(x) for x in m.groups())
    return (l, t, r, b)

def hierarchy_nodes(d):
    root = ET.fromstring(d.dump_hierarchy())
    nodes = []
    for n in root.iter("node"):
        b = _bounds(n)
        if not b:
            continue
        nodes.append({
            "text": (n.attrib.get("text") or "").strip(),
            "desc": (n.attrib.get("content-desc") or "").strip(),
            "cls": n.attrib.get("class") or "",
            "clickable": n.attrib.get("clickable") == "true",
            "checkable": n.attrib.get("checkable") == "true",
            "checked": n.attrib.get("checked") == "true",
            "bounds": b,
            "cx": (b[0] + b[2]) // 2,
            "cy": (b[1] + b[3]) // 2,
        })
    return nodes

def _blocked(node):
    s = (node["text"] + " " + node["desc"]).lower()
    return any(w in s for w in BLOCKED_WORDS)

def click_node(d, node):
    if _blocked(node):
        print("    [安全拦截] 跳过疑似下单按钮: %s" % (node["text"] or node["desc"]))
        return False
    d.click(node["cx"], node["cy"])
    return True

def ensure_app(d):
    """确保 Keeta 在前台 (防通知/其他 App 抢前台污染抓取)。"""
    try:
        cur = d.app_current()
        if cur.get("package") == "com.android.systemui":
            d.press("back")
            time.sleep(0.8)
            cur = d.app_current()
        if cur.get("package") != PACKAGE:
            d.app_start(PACKAGE)
            time.sleep(3.5)
    except Exception:
        pass

def dismiss_popups(d, rounds=2):
    for _ in range(rounds):
        hit = False
        for t in ("Agora não", "Not now", "No, thanks", "Não, obrigado", "Mais tarde",
                  "Later", "Entendi", "Got it", "Pular", "Skip", "Fechar"):
            el = d(text=t)
            if el.exists(timeout=0.4):
                el.click()
                hit = True
                time.sleep(1)
                break
        if not hit:
            for node in hierarchy_nodes(d):
                if node["clickable"] and node["desc"].lower() in ("fechar", "close", "dismiss"):
                    if click_node(d, node):
                        hit = True
                        time.sleep(1)
                    break
        if not hit:
            break

def handle_cart_conflict(d):
    """购物车有别家的菜时, 点清空/重新开始 (中英葡)。"""
    texts, _ = texts_of(d)
    blob = joined(texts).lower()
    keys = ("sacola", "cart")
    hints = ("outra loja", "outro restaurante", "another restaurant", "another store",
             "esvaziar", "limpar", "clear your", "clear the")
    if any(k in blob for k in keys) and any(h in blob for h in hints):
        for t in ("Clear cart", "Esvaziar sacola", "Esvaziar", "Limpar sacola", "Limpar",
                  "Start new order", "Começar novo pedido", "Clear", "Yes", "Sim",
                  "Continue", "Continuar"):
            el = d(text=t)
            if el.exists(timeout=0.4):
                el.click()
                time.sleep(1.5)
                return True
    return False

# ---------- 店铺行定位 (以距离文本为锚) ----------

NAME_EXCLUDE = re.compile(r"R\$|min|km|%|\boff\b|free|top\b|dedicated|google maps", re.I)

def find_shop_rows(d):
    """列表/首页里的店铺行: 找 'x.x km' 距离节点, 店名取其上方最近的有效文本。"""
    nodes = hierarchy_nodes(d)
    w, h = d.window_size()
    rows = []
    seen = set()
    dist_nodes = [n for n in nodes if re.search(r"\d+[.,]\d+\s*km", n["text"])]
    for dn in dist_nodes:
        dl, dt, dr, db = dn["bounds"]
        cands = []
        for n in nodes:
            t = n["text"]
            if not t or len(t) < 4 or NAME_EXCLUDE.search(t):
                continue
            if re.match(r"^\d[.,]\d", t):  # 评分行 '4.8 (500+)'
                continue
            nl, nt, nr, nb = n["bounds"]
            if nb <= dt + 6 and dt - nb <= 360 and abs(nl - dl) <= 80:
                cands.append(n)
        if not cands:
            continue
        name = max(cands, key=lambda n: n["bounds"][3])
        if name["text"] in seen:
            continue
        seen.add(name["text"])
        m = re.search(r"(\d+[.,]\d+)\s*km", dn["text"])
        eta = re.search(r"(\d+)\s*[-–]\s*(\d+)\s*min", dn["text"])
        rows.append({
            "name": name["text"],
            "x": name["cx"], "y": name["cy"],
            "img_x": int(0.17 * w), "img_y": (name["bounds"][1] + db) // 2,
            "distance": (m.group(1).replace(".", ",") + " km") if m else "",
            "eta_min": int(eta.group(1)) if eta else None,
            "eta_max": int(eta.group(2)) if eta else None,
        })
    rows.sort(key=lambda r: r["y"])
    return rows

def is_shop_page(texts):
    blob = joined(texts)
    if "Sort by" in blob or "Back to Top" in blob:
        return False
    prices = sum(1 for t in texts if re.fullmatch(r"R\$\s*[\d\.,]+", t.strip()))
    return prices >= 2

def go_home(d):
    ensure_app(d)
    for _ in range(5):
        texts, _ = texts_of(d)
        if find_shop_rows(d) or "Your welcome gifts" in joined(texts) or "Sort by" in joined(texts):
            return True
        d.press("back")
        time.sleep(1.2)
    return True

def open_next_shop(d, tried):
    """滚动找店铺行并点进店; 返回 row dict 或 None。"""
    for _round in range(6):
        ensure_app(d)
        for row in find_shop_rows(d):
            if row["name"] in tried:
                continue
            tried.add(row["name"])
            d.click(row["x"], row["y"])
            time.sleep(2.5)
            dismiss_popups(d)
            texts, _ = texts_of(d)
            if is_shop_page(texts):
                return row
            if "Sort by" in joined(texts):
                # 还在列表: 换点图片区域再试一次
                d.click(row["img_x"], row["img_y"])
                time.sleep(2.5)
                texts, _ = texts_of(d)
                if is_shop_page(texts):
                    return row
            else:
                d.press("back")
                time.sleep(1.2)
        w, h = d.window_size()
        d.swipe(w // 2, int(h * 0.78), w // 2, int(h * 0.32), 0.4)
        time.sleep(1.5)
    return None

# ---------- 加菜 ----------

def _add_buttons(d):
    return [n for n in hierarchy_nodes(d)
            if n["clickable"] and not _blocked(n)
            and (n["text"].startswith("Add") or n["text"].startswith("Adicionar")
                 or n["desc"].lower() in ("add", "adicionar", "+"))]

def _cart_bar_visible(texts):
    blob = joined(texts)
    return any(k in blob for k in ("View cart", "Ver sacola", "View bag", "Sacola")) \
        or ("Cart" in blob and "R$" in blob)

def add_item_auto(d):
    """自动加一件菜: 点菜品行 -> 详情页选必选规格(每组第一项) -> 点底部 Add。"""
    for item_try in range(3):
        nodes = hierarchy_nodes(d)
        w, h = d.window_size()
        prices = [n for n in nodes
                  if re.fullmatch(r"R\$\s*[\d\.,]+", n["text"]) and n["bounds"][1] > 0.14 * h]
        if not prices:
            d.swipe(w // 2, int(h * 0.7), w // 2, int(h * 0.4), 0.4)
            time.sleep(1.2)
            continue
        price = prices[item_try % len(prices)]
        # 菜品名: 价格上方最近的有效文本
        name = None
        for n in nodes:
            t = n["text"]
            if t and len(t) >= 4 and "R$" not in t and "%" not in t:
                if n["bounds"][3] <= price["bounds"][1] + 6 and price["bounds"][1] - n["bounds"][3] <= 220 \
                        and abs(n["bounds"][0] - price["bounds"][0]) <= 120:
                    if name is None or n["bounds"][3] > name["bounds"][3]:
                        name = n
        d.click(*( (name["cx"], name["cy"]) if name else (price["cx"], price["cy"]) ))
        time.sleep(2)
        handle_cart_conflict(d)
        texts, _ = texts_of(d)
        if _cart_bar_visible(texts):
            return True
        # 详情页: 处理必选规格后点底部 Add
        for _ in range(8):
            texts, _ = texts_of(d)
            if _cart_bar_visible(texts):
                return True
            opts = [n for n in hierarchy_nodes(d)
                    if n["clickable"] and n["checkable"] and not n["checked"] and not _blocked(n)]
            if opts:
                click_node(d, sorted(opts, key=lambda n: (n["bounds"][1], n["bounds"][0]))[0])
                time.sleep(0.8)
                continue
            btns = _add_buttons(d)
            if btns:
                click_node(d, max(btns, key=lambda n: n["cy"]))
                time.sleep(1.8)
                handle_cart_conflict(d)
                texts, _ = texts_of(d)
                if _cart_bar_visible(texts) or not _add_buttons(d):
                    return True
            w2, h2 = d.window_size()
            d.swipe(w2 // 2, int(h2 * 0.7), w2 // 2, int(h2 * 0.45), 0.3)
            time.sleep(0.8)
        d.press("back")
        time.sleep(1.2)
    return False

def clear_cart(d):
    if tap_contains(d, "View cart", timeout=2) or tap_contains(d, "Ver sacola", timeout=2) \
            or tap_contains(d, "Sacola", timeout=2):
        time.sleep(1.5)
        if tap_contains(d, "Clear", timeout=2) or tap_contains(d, "Limpar", timeout=2) \
                or tap_contains(d, "Esvaziar", timeout=2):
            time.sleep(1)
            tap_text(d, "Yes", timeout=1.5) or tap_text(d, "Sim", timeout=1.5) \
                or tap_text(d, "Confirm", timeout=1.5) or tap_text(d, "Confirmar", timeout=1.5) \
                or tap_contains(d, "Clear", timeout=1.5) or tap_contains(d, "Esvaziar", timeout=1.5)
            time.sleep(1)

# ---------- 账号 ----------

def get_account_info(d):
    """Account/Perfil 页读邮箱; Orders/Pedidos 页数完单数。读不到留空, 不编造。"""
    info = {}
    ensure_app(d)
    if not (tap_text(d, "Account", timeout=3) or tap_text(d, "Perfil", timeout=2)):
        tap_contains(d, "Account", timeout=2)
    time.sleep(2)
    texts, _ = texts_of(d)
    save_debug(d, "perfil")
    for t in texts:
        if "@" in t and "." in t:
            info["account_id"] = t
            break
    if tap_text(d, "Orders", timeout=3) or tap_contains(d, "Pedidos", timeout=2) \
            or tap_contains(d, "Meus pedidos", timeout=2):
        time.sleep(2)
        texts2, _ = texts_of(d)
        save_debug(d, "pedidos")
        blob = joined(texts2)
        if re.search(r"no orders|haven't placed|não fez|nenhum pedido|sem pedidos|nenhuma ordem", blob, re.I):
            info["user_completed_orders_count"] = 0
        else:
            done = len(re.findall(r"Delivered|Entregue|Concluído|Concluido", blob))
            if done:
                info["user_completed_orders_count"] = done
    tap_text(d, "Home", timeout=2) or tap_text(d, "Início", timeout=2) or d.press("back")
    time.sleep(1)
    return info

# ---------- 单店 ----------

def scrape_one_shop_auto(d, idx, tried, attempt_no):
    print("\n=== 尝试 #%d: 目标第 %d 家 ===" % (attempt_no, idx))
    ensure_app(d)
    row_meta = open_next_shop(d, tried)
    if row_meta is None:
        save_debug(d, "no_shop_open")
        print("找不到可进的店, 本轮跳过 (debug 已存)")
        return None
    time.sleep(1)
    texts, _ = texts_of(d)
    save_debug(d, "shop_auto_page")
    row = parse_shop_page(texts)
    row["shop_name"] = row_meta["name"]
    if row_meta.get("distance"):
        row["distance"] = row_meta["distance"]
    if row.get("shop_status") == "close":
        print("这家已打烊, 跳过。")
        d.press("back")
        return None

    if not add_item_auto(d):
        save_debug(d, "add_fail")
        print("自动加菜失败, 本家跳过 (debug 已存)")
        clear_cart(d)
        go_home(d)
        return None

    # 凑起送价 + 进购物车页
    for _ in range(3):
        if tap_contains(d, "View cart", timeout=3) or tap_contains(d, "Ver sacola", timeout=2) \
                or tap_contains(d, "Sacola", timeout=2):
            time.sleep(1.5)
        texts, _ = texts_of(d)
        save_debug(d, "sacola")
        blob = joined(texts)
        short = any(k in blob for k in ("Faltam", "Add more", "Minimum order", "Pedido mínimo")) \
            and ("Resumo" not in blob and "Order summary" not in blob)
        if short and re.search(r"R\$\s*[\d\.,]+\s*(more|faltando)|Faltam|Add .* more", blob):
            print("未达起送价, 再加一件...")
            d.press("back")
            time.sleep(1.2)
            if not add_item_auto(d):
                break
            continue
        break

    # 进提单页 (购物车页 -> Checkout/Pedir agora)
    texts, _ = texts_of(d)
    arrived = any(k in joined(texts) for k in ("Order summary", "Resumo do pedido"))
    if not arrived:
        tap_text(d, "Checkout", timeout=4) or tap_text(d, "Pedir agora", timeout=3) \
            or tap_contains(d, "Review order", timeout=2)
        time.sleep(2)
    texts, _ = texts_of(d)
    save_debug(d, "checkout_auto")
    if not any(k in joined(texts) for k in ("Order summary", "Resumo do pedido", "Subtotal")):
        print("!! 没到提单页, 本家跳过 (debug 已存 checkout_auto, 发我看)")
        clear_cart(d)
        go_home(d)
        return None
    data = parse_checkout(texts)
    # ceta 兜底: 提单页没读到时用列表页的 min 范围 (页面真实显示)
    if "ceta_min" not in data and row_meta.get("eta_min") is not None:
        data["ceta_min"] = row_meta["eta_min"]
        data["ceta_max"] = row_meta["eta_max"]
    row.update(data)
    print("提取到字段: %s" % ", ".join(sorted(data.keys())))
    clear_cart(d)
    go_home(d)
    return row


def main():
    n_shops = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    os.makedirs(OUT_DIR, exist_ok=True)
    d = u2.connect()
    print("已连接设备: %s" % d.info.get("productName", "?"))
    d.app_start(PACKAGE)
    time.sleep(5)
    dismiss_popups(d)
    save_debug(d, "home")

    acct = get_account_info(d)
    cnt = acct.get("user_completed_orders_count")
    if cnt is not None:
        acct["account_type"] = 0 if cnt == 0 else (1 if cnt <= 4 else 2)
    acct["is_member"] = 0  # BRD 注明 Keeta 目前无会员体系

    rows = []
    tried = set()
    attempts = 0
    while len(rows) < n_shops and attempts < n_shops + 6:
        attempts += 1
        row = scrape_one_shop_auto(d, len(rows) + 1, tried, attempts)
        if not row:
            continue
        base = {
            "batch_no": now_sp().strftime("%Y%m%d"),
            "country": "BR",
            "platform": "Keeta",
            "city_name": row.get("city_name", "São Paulo"),
            "crawl_time": now_sp().strftime("%Y-%m-%d %H:%M:%S"),
        }
        base.update(acct)
        base.update(row)
        rows.append({f: base.get(f, "") for f in FIELDS})
        filled = sum(1 for v in rows[-1].values() if v != "")
        print("第 %d 家完成, 已填 %d/30 字段" % (len(rows), filled))

    if not rows:
        print("\n一家都没抓到, 把 output/debug 里的截图和 XML 发我, 我照真实结构改选择器。")
        return
    fn = os.path.join(OUT_DIR, "keeta_%s.csv" % now_sp().strftime("%Y%m%d_%H%M%S"))
    with open(fn, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print("\n完成: %d 行 -> %s" % (len(rows), fn))
    print("把这个 CSV 发回给我, 我核对字段和金额。")


if __name__ == "__main__":
    main()
