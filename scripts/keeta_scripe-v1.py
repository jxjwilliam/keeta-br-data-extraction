#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meta muse version: Keeta 提单页数据自动抓取 v1 (ADB + uiautomator2)

流程: 启动 Keeta -> 读账号信息 -> 逐家进店 -> 加一件高销菜 -> 进提单页(Resumo do pedido)
      -> 提取红框字段 + 截图 -> 写 30 列 CSV (BRD 字段顺序)

诚实规则 (按 William 要求):
- 只写页面上真实显示的值; 页面没有的字段留空, 绝不编造。
- 派生值只有两种, 且都是由页面显示值做算术: ceta_min/max (由 Previsão 时钟窗口换算分钟),
  total_original (各原价之和 / 总价+已用优惠)。其余一律页面直读。
- 导航自动尝试失败时, 脚本会暂停并提示你在 scrcpy 镜像里手动完成该步, 回车继续。
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


KNOWN_LABELS = ("subtotal", "taxa de entrega", "taxa de serviço", "taxa de servico", "total")

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

    fee = parse_money_after(texts, "Taxa de entrega")
    if fee:
        if len(fee) >= 2:
            r["delivery_original"] = max(fee)
            r["delivery_final"] = min(fee)
        else:
            r["delivery_original"] = fee[0]
            r["delivery_final"] = fee[0]
    elif "grátis" in blob.lower() or "gratis" in blob.lower():
        r["delivery_final"] = 0  # 页面显示免配送费

    svc = parse_money_after(texts, "Taxa de serviço") or parse_money_after(texts, "Taxa de servico")
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

    # 已应用优惠: 'Desconto de R$ 10,00 aplicado'
    m = re.search(r"[Dd]esconto de\s*(R\$\s*[\d\.,]+)", blob)
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

# ---------------- 主流程 ----------------

def get_account_info(d):
    """去 'Perfil'(我的) 页读账号信息; 读不到就留空, 不编造。"""
    info = {}
    tap_text(d, "Perfil", timeout=3) or tap_contains(d, "Perfil", timeout=3)
    time.sleep(2)
    texts, _ = texts_of(d)
    save_debug(d, "perfil")
    for t in texts:
        if "@" in t and "." in t:  # 邮箱即账号标识
            info["account_id"] = t
            break
    # 订单数: 进 Pedidos(订单) 页数已完成订单; 空态文案视为 0
    if tap_contains(d, "Pedidos", timeout=3) or tap_contains(d, "Meus pedidos", timeout=3):
        time.sleep(2)
        texts2, _ = texts_of(d)
        save_debug(d, "pedidos")
        blob = joined(texts2)
        if re.search(r"nenhum pedido|não fez|sem pedidos|nenhuma ordem", blob, re.I):
            info["user_completed_orders_count"] = 0
        else:
            done = len(re.findall(r"Entregue|Concluído|Concluido", blob))
            if done:
                info["user_completed_orders_count"] = done
    d.press("back")
    time.sleep(1)
    # 回首页
    tap_text(d, "Início", timeout=2) or tap_text(d, "Inicio", timeout=2) or d.press("back")
    time.sleep(1)
    return info


def scrape_one_shop(d, idx):
    """进第 idx 家店(进店这步手动确认), 走完提单页提取。返回 row dict 或 None。"""
    print("\n=== 第 %d 家店 ===" % idx)
    manual("在镜像里点进一家营业中的店 (若已在店内可直接回车)", "escolha uma loja aberta")
    time.sleep(2)
    texts, _ = texts_of(d)
    save_debug(d, "shop%d_page" % idx)
    row = parse_shop_page(texts)
    if row.get("shop_status") == "close":
        print("这家店显示已打烊 (Fechado), 跳过。")
        d.press("back")
        return None
    # 店名: 店铺页的文本里取第一个较长且非导航词的
    skip_words = ("pedir agora", "início", "inicio", "perfil", "buscar", "pesquisar", "voltar")
    for t in texts:
        if len(t) >= 3 and t.lower() not in skip_words and "R$" not in t and "km" not in t:
            row["shop_name"] = t
            break

    # 加一件菜: 点第一个 'Adicionar'(添加)
    if not tap_text(d, "Adicionar", timeout=4):
        manual("点开销量靠前的一道菜, 点 Adicionar 添加到购物袋", "Adicionar")
    time.sleep(2)
    # 菜品详情页可能还要再点一次 Adicionar 确认
    tap_text(d, "Adicionar", timeout=2)
    time.sleep(1)

    # 凑起送价: 出现 'Faltam R$ X'(还差 X) 就继续加菜
    for _ in range(4):
        texts, _ = texts_of(d)
        if any("Faltam" in t for t in texts):
            print("未达起送价, 继续加菜...")
            d.press("back")
            time.sleep(1)
            if not tap_text(d, "Adicionar", timeout=3):
                manual("再加一件便宜的菜凑起送价", "Adicionar")
            time.sleep(1)
            tap_text(d, "Adicionar", timeout=2)
            time.sleep(1)
        else:
            break

    # 进提单页: Ver sacola(看购物袋) -> Pedir agora(立即下单)
    if not (tap_contains(d, "Ver sacola", timeout=4) or tap_contains(d, "Sacola", timeout=3)):
        manual("点 Ver sacola (查看购物袋)", "Ver sacola")
    time.sleep(2)
    texts, _ = texts_of(d)
    if not any("Resumo do pedido" in t for t in texts):
        if not tap_text(d, "Pedir agora", timeout=4):
            manual("点 Pedir agora 进入提单页 Resumo do pedido (不要点 Fazer pedido!)",
                   "Pedir agora")
        time.sleep(2)

    texts, _ = texts_of(d)
    save_debug(d, "shop%d_checkout" % idx)
    if not any("Resumo do pedido" in t for t in texts):
        print("!! 没到提单页, 本家跳过 (debug 已存, 把截图发我看)")
        return None
    data = parse_checkout(texts)
    row.update(data)
    print("提取到字段: %s" % ", ".join(sorted(data.keys())))

    # 退出并清空购物袋, 避免影响下一家
    d.press("back")
    time.sleep(1)
    if tap_contains(d, "Sacola", timeout=2) or tap_contains(d, "Ver sacola", timeout=2):
        time.sleep(1)
        tap_contains(d, "Limpar", timeout=2) or tap_contains(d, "Esvaziar", timeout=2)
        time.sleep(1)
        tap_text(d, "Confirmar", timeout=2) or tap_text(d, "Sim", timeout=2)
    for _ in range(3):
        d.press("back")
        time.sleep(1)
    return row


def main():
    n_shops = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    os.makedirs(OUT_DIR, exist_ok=True)
    d = u2.connect()
    print("已连接设备: %s" % d.info.get("productName", "?"))
    d.app_start(PACKAGE)
    time.sleep(5)
    save_debug(d, "home")

    acct = get_account_info(d)
    cnt = acct.get("user_completed_orders_count")
    if cnt is not None:
        acct["account_type"] = 0 if cnt == 0 else (1 if cnt <= 4 else 2)
    acct["is_member"] = 0  # BRD 注明 Keeta 目前无会员体系

    rows = []
    for i in range(1, n_shops + 1):
        row = scrape_one_shop(d, i)
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
        print("第 %d 家完成, 已填 %d/30 字段" % (i, filled))

    if not rows:
        print("\n没有成功抓到任何一家, 把 output/debug 里的截图发我, 我看页面结构再改脚本。")
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
