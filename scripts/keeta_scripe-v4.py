#!/usr/bin/env python3
"""Keeta 单条 PoC：当前店铺加购简单商品，或读取当前 Checkout。
依赖：python3、uiautomator2、Pillow、系统 adb。
python3 scripts/keeta_scripe-v4.py --serial 979f0245 --item '商品完整名称'
python3 scripts/keeta_scripe-v4.py --serial 979f0245
python3 scripts/keeta_scripe-v4.py --parse-dir outputs/internal/runs/keeta-rerun-20261022
不选择必选规格、不自动应用券、不提交订单。完整首页导航仍未验收。
"""
import argparse,csv,json,re,time,math,os,shutil,subprocess,tempfile
from pathlib import Path
from datetime import datetime,timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

PACKAGE='com.sankuai.sailor.afooddelivery'
TZ=ZoneInfo('America/Sao_Paulo')
FIELDS='batch_no country platform city_name crawl_time account_id user_completed_orders_count account_type is_member shop_id shop_name crawl_lat crawl_lng crawl_address shop_lat shop_lng shop_address ceta_min ceta_max product_info product_original product_final delivery_original delivery_final service_original service_final total_original total_final distance shop_status'.split()
SENSITIVE=re.compile(r'@|william|jiang|\+\d[\d ()-]{6,}',re.I)

def nodes(root):
    result=[]
    for n in root.iter('node'):
        if n.get('package')!=PACKAGE or not n.get('text'):continue
        b=list(map(int,re.findall(r'\d+',n.get('bounds',''))))
        if len(b)==4:result.append({'text':n.get('text'),'b':b})
    return result

def capture(d,out,label):
    from PIL import ImageDraw
    started=datetime.now(TZ).isoformat(timespec='seconds')
    root=ET.fromstring(d.dump_hierarchy());im=d.screenshot();draw=ImageDraw.Draw(im)
    for n in root.iter('node'):
        if any(SENSITIVE.search(n.get(k,'')) for k in ('text','content-desc')):
            b=list(map(int,re.findall(r'\d+',n.get('bounds',''))))
            if len(b)==4:draw.rectangle(b,fill='black')
            n.set('text','[redacted]');n.set('content-desc','')
    ET.ElementTree(root).write(out/(label+'.xml'),encoding='utf-8')
    im.save(out/(label+'.png'))
    (out/(label+'.json')).write_text(json.dumps({'captured_at':started},ensure_ascii=False))
    print('已保存',label,started,flush=True)
    return nodes(root)

def money(t):
    m=re.fullmatch(r'R\$\s*([\d.,]+)',t)
    if not m:raise ValueError('不是独立金额: '+t)
    value=m[1]
    if ',' in value:value=value.replace('.','').replace(',','.')
    return int(Decimal(value)*100)

def row_money(ns,label):
    labels=[n for n in ns if n['text']==label]
    if len(labels)!=1:raise ValueError('费用标签缺失或重复: '+label)
    n=labels[0];y=(n['b'][1]+n['b'][3])/2
    vals=[x for x in ns if x['b'][0]>n['b'][2] and abs((x['b'][1]+x['b'][3])/2-y)<25 and re.fullmatch(r'R\$\s*[\d.,]+',x['text'])]
    return [money(x['text']) for x in sorted(vals,key=lambda x:x['b'][0])]

def eta_minutes(raw, captured_at):
    """同页时刻减捕获时间，向上取整；不把过期窗口截成 0。"""
    m = re.fullmatch(r'Est\. arrival (\d{1,2}):(\d{2})[-–](\d{1,2}):(\d{2})', raw or '')
    if not m:
        return None
    dt = datetime.fromisoformat(captured_at).astimezone(TZ)
    h1, m1, h2, m2 = map(int, m.groups())
    try:
        first = dt.replace(hour=h1, minute=m1, second=0, microsecond=0)
        last = dt.replace(hour=h2, minute=m2, second=0, microsecond=0)
    except ValueError:
        return None
    if first < dt:
        # 仅在午夜附近允许解释为次日；其他负时差视为过期/不确定。
        if dt.hour >= 18 and h1 <= 6:
            first += timedelta(days=1)
        else:
            return None
    if last < first:
        last += timedelta(days=1)
    seconds = ((first-dt).total_seconds(), (last-dt).total_seconds())
    if not 0 <= seconds[0] <= seconds[1] <= 6*3600:
        return None
    return tuple(math.ceil(v/60) for v in seconds)


def account_type(count):
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        return None
    return 0 if count == 0 else (1 if count <= 4 else 2)


def context_fields(directory):
    """只解析已留证的店铺详情/空订单页；不会把可见订单卡数量当累计完单数。"""
    facts = {}
    shop_path = directory / 'shop-info.xml'
    if shop_path.exists():
        ns = nodes(ET.parse(shop_path).getroot())
        texts = [n['text'].strip() for n in ns]
        if 'Address' in texts:
            i = texts.index('Address')
            if i + 1 < len(texts):
                facts['shop_address'] = texts[i + 1].strip('\ufeff ')
        if 'Open' in texts:
            facts['shop_status'] = 'open'
        elif 'Closed' in texts:
            facts['shop_status'] = 'close'
        facts['shop_name'] = texts[0] if texts else None
    order_path = directory / 'orders.xml'
    if order_path.exists():
        texts = [n['text'].strip() for n in nodes(ET.parse(order_path).getroot())]
        if 'My orders' in texts and 'No orders yet' in texts:
            facts['user_completed_orders_count'] = 0
            facts['account_type'] = account_type(0)
    return facts


def parse(out, context=None):
    top=nodes(ET.parse(out/'checkout-top.xml').getroot());fees=nodes(ET.parse(out/'checkout-fees.xml').getroot())
    stamp=json.loads((out/'checkout-top.json').read_text())['captured_at'];dt=datetime.fromisoformat(stamp)
    row={f:None for f in FIELDS}
    row.update(batch_no=dt.strftime('%Y%m%d'),country='BR',platform='Keeta',crawl_time=dt.isoformat(timespec='seconds'))
    address=[n for n in top if re.search(r'^(Rua |R\. |Av\.|Avenida )',n['text'])]
    address_unconfirmed = any(n['text'] == 'Select a delivery address' for n in top)
    if len(address)==1 and not address_unconfirmed:
        row['crawl_address']=address[0]['text']
        if 'São Paulo' in address[0]['text']:row['city_name']='São Paulo'
    summary=next(i for i,n in enumerate(top) if n['text']=='Order summary')
    row['shop_name']=top[summary+1]['text']
    items=[n for n in top if re.match(r'^\d+\s*[×x]\s+',n['text'])]
    if len(items)!=1:raise ValueError('此 PoC 只支持单商品；不确定时停止导出')
    item=items[0];row['product_info']=item['text']
    amounts=[n for n in top if n['b'][0]>item['b'][2] and item['b'][1]-5<=n['b'][1]<=item['b'][3] and re.fullmatch(r'R\$\s*[\d.,]+',n['text'])]
    amounts.sort(key=lambda n:n['b'][1])
    if len(amounts)!=2:raise ValueError('商品原价/折后价未分别读到')
    row['product_final'],row['product_original']=[money(n['text']) for n in amounts]
    subtotal=row_money(fees,'Subtotal');delivery=row_money(fees,'Delivery fee');service=row_money(fees,'Service fee');total=row_money(fees,'Total')
    if len(delivery)!=2 or len(service)!=1 or len(total)!=1:raise ValueError('费用结构变化，停止导出')
    row.update(delivery_original=delivery[0],delivery_final=delivery[1],service_original=service[0],service_final=service[0],total_final=total[0])
    row['total_original']=row['product_original']+row['delivery_original']+row['service_original']
    assert subtotal==[row['product_original']], '商品原价与 Subtotal 不符'
    assert row['product_final']+row['delivery_final']+row['service_final']==row['total_final'],'费用不平'
    applied=[n['text'] for n in fees if re.fullmatch(r'R\$[\d.,]+ off applied',n['text'])]
    if len(applied)!=1:raise ValueError('未明确读取总已应用优惠')
    discount=money(applied[0].replace(' off applied',''))
    assert row['total_original']-row['total_final']==discount,'优惠不平'
    top_total=[n['text'] for n in top if n['text'].startswith('Total R$')]
    assert top_total==['Total R$'+format(Decimal(row['total_final'])/100,'.2f')],'跨页报价变化'
    eta=next((n['text'] for n in top if n['text'].startswith('Est. arrival ')),None)
    eta_result = eta_minutes(eta, stamp)
    if eta_result:
        row['ceta_min'], row['ceta_max'] = eta_result
    if context:
        facts=context_fields(context)
        if facts.get('shop_name') != row['shop_name']:
            raise ValueError('上下文店铺与结算店铺不匹配')
        for label in ('shop-info','orders'):
            context_stamp=json.loads((context/(label+'.json')).read_text())['captured_at']
            if abs((datetime.fromisoformat(context_stamp)-dt).total_seconds())>300:
                raise ValueError('上下文与结算超过 5 分钟，需同轮重采')
        for field in ('shop_address','shop_status','user_completed_orders_count','account_type'):
            row[field]=facts.get(field)
    notes={f:('未取得；留空' if row[f] is None else '实时结算页') for f in FIELDS}
    if address_unconfirmed:notes['crawl_address']='地址栏仍要求选择地址；提示气泡不视为已选中地址'
    for f in ['batch_no','country','platform']:notes[f]='采集日期或用户确认的巴西 Keeta 上下文'
    notes['crawl_time']='顶部 XML 捕获开始时间，America/Sao_Paulo'
    notes['city_name']='当前结算地址'
    notes['total_original']='商品原价 + 配送原价 + 服务费（计算值）'
    notes['service_original']='项目口径：单一可见服务费同时填原价与现价'
    for f in ['ceta_min','ceta_max']:notes[f]='送达时刻减同页捕获时间，向上取整分钟；跨日仅接受午夜附近且 6 小时内，否则留空'
    if context:
        for f in ('shop_address','shop_status'):notes[f]='同店铺详情页，来源时间见上下文 shop-info.json'
        notes['user_completed_orders_count']='同设备登录会话订单页 My orders / No orders yet；未统计可见订单卡'
        notes['account_type']='用户确认映射：0单→0，1–4单→1，≥5单→2'
    evidence={'record':row,'field_sources':notes,'eta_raw':eta,'timezone':'America/Sao_Paulo','fee_capture':json.loads((out/'checkout-fees.json').read_text()),'conditions':{'delivery_address_confirmed':not address_unconfirmed,'quantity':1,'account':'当前已登录账号，内部 ID 未读取','promotion':'未操作 Apply now；可用券不计入已用优惠','address':row['crawl_address']},'qa':{'subtotal_cents':subtotal[0],'applied_discount_cents':discount,'amounts_reconciled':True,'same_item_and_total_across_pages':True},'limitations':['未取得页面未展示的账号、坐标、店铺 ID/地址/距离及明确营业状态','顶部与费用页为顺序采集，并非原子报价','未提交订单']}
    (out/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
    with (out/'draft.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerow(row)
    print('金额校验通过，已填',sum(v is not None for v in row.values()),'/ 30；',out/'draft.csv')

def publish_files(run, final, captured_at):
    """使用采集当地时间命名，排他创建；绝不替换已有结果。"""
    stamp = datetime.fromisoformat(captured_at).astimezone(TZ).strftime('%Y%m%d_%H%M%S')
    targets = [final / ('latest_' + stamp + '.' + suffix) for suffix in ('xlsx', 'csv')]
    final.mkdir(parents=True, exist_ok=True)
    for target in targets:
        if target.exists():
            raise FileExistsError('该时间戳已有结果，不覆盖：' + str(target))
    created = []
    try:
        for suffix, target in zip(('xlsx', 'csv'), targets):
            with (run / ('draft.' + suffix)).open('rb') as source, target.open('xb') as dest:
                created.append(target)
                shutil.copyfileobj(source, dest)
    except Exception:
        for target in created:
            target.unlink()
        raise
    return targets


def export_bundle(run, output_root=None):
    """先在内部目录生成一对文件，记录有效时才发布到 final。"""
    repo = Path(__file__).resolve().parents[1]
    output_root = output_root or repo / 'outputs'
    evidence = json.loads((run / 'evidence.json').read_text())
    row = evidence['record']
    draft_csv = run / 'draft.csv'
    with draft_csv.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerow(row)
    runtime = Path(os.environ.get('KEETA_RUNTIME', Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies'))
    node = runtime/'node/bin/node'
    modules = runtime/'node/node_modules'
    if not node.exists() or not (modules/'@oai/artifact-tool').exists():
        raise RuntimeError('XLSX 运行时缺失；设置 KEETA_RUNTIME。CSV 草稿已留在内部目录，未发布半套文件。')
    marker = Path.home()/'.codex/plugins/cache/openai-primary-runtime/spreadsheets/26.1015.12040/skills/spreadsheets/container_tools/mark_artifact_operation_started.mjs'
    if marker.exists():
        subprocess.run([str(node),str(marker),'--operation-kind','create','--expected-output-count','1','--output-format','xlsx'],check=True,capture_output=True)
    with tempfile.TemporaryDirectory(prefix='keeta-export-') as t:
        work = Path(t)
        (work/'node_modules').symlink_to(modules,target_is_directory=True)
        shutil.copy2(repo/'scripts/export_keeta.mjs',work/'export.mjs')
        proc = subprocess.run([str(node),str(work/'export.mjs'),str(run.resolve()),str((run/'draft.xlsx').resolve()),str(repo)],capture_output=True,text=True)
        (run/'export.log').write_text(proc.stdout+'\n'+proc.stderr)
        if proc.returncode:
            raise RuntimeError('XLSX 导出失败，见内部 export.log；未发布。')
    ready = (evidence.get('conditions',{}).get('delivery_address_confirmed') is True
             and row.get('crawl_address') and row.get('city_name')
             and evidence.get('qa',{}).get('amounts_reconciled') is True
             and evidence.get('qa',{}).get('same_item_and_total_across_pages') is True)
    if not ready:
        (run/'publication.json').write_text(json.dumps({'published':False,'reason':'地址或报价校验未通过；保留内部草稿'},ensure_ascii=False))
        print('本轮仅保留内部草稿，final 不更新：',run)
        return False
    final = output_root/'final'
    targets = publish_files(run, final, row['crawl_time'])
    (run/'publication.json').write_text(json.dumps({'published':True,'run_id':run.name,'files':[str(p) for p in targets]},ensure_ascii=False))
    print('最终结果：',*targets)
    return True


def main():
    p=argparse.ArgumentParser();p.add_argument('--serial',default='979f0245');p.add_argument('--item');p.add_argument('--parse-dir',type=Path);p.add_argument('--export-run',type=Path);p.add_argument('--context-dir',type=Path);p.add_argument('--inspect-context-dir',type=Path);a=p.parse_args()
    if a.export_run:export_bundle(a.export_run);return
    if a.inspect_context_dir:
        facts=context_fields(a.inspect_context_dir)
        (a.inspect_context_dir/'context-fields.json').write_text(json.dumps(facts,ensure_ascii=False,indent=2))
        print(json.dumps(facts,ensure_ascii=False,indent=2));return
    if a.parse_dir:parse(a.parse_dir,a.context_dir);return
    import uiautomator2 as u
    d=u.connect(a.serial);d.jsonrpc.setConfigurator({'waitForIdleTimeout':0})
    if d.app_current()['package']!=PACKAGE:raise RuntimeError('请先打开 Keeta')
    if a.item:
        if not d(text=a.item).exists:raise RuntimeError('当前店铺未显示指定商品')
        d(text=a.item).click();time.sleep(1)
        # TextView 的 clickable=false 不代表其父容器不能响应触摸。
        if not d(text='Add to cart').exists:raise RuntimeError('未找到明确 Add to cart，停止')
        d(text='Add to cart').click();time.sleep(1)
        if not d(text='Check out').exists:raise RuntimeError('未找到 Check out；可能有必选规格，停止')
        d(text='Check out').click();time.sleep(2)
    if not d(text='Checkout').exists:raise RuntimeError('当前不是 Checkout')
    out=Path(__file__).resolve().parents[1]/'outputs'/'internal'/'runs'/('keeta-'+datetime.now(TZ).strftime('%Y%m%d-%H%M%S-%f'));out.mkdir(parents=True)
    w,h=d.window_size()
    for _ in range(3):
        if d(textStartsWith='Est. arrival').exists:break
        d.swipe(w//2,int(h*.35),w//2,int(h*.78),.4);time.sleep(.5)
    ns=capture(d,out,'checkout-top')
    if not any(n['text'].startswith('Est. arrival') for n in ns):raise RuntimeError('未读到顶部 ETA')
    for _ in range(3):
        d.swipe(w//2,int(h*.78),w//2,int(h*.35),.4);time.sleep(.5)
        if d(text='Service fee').exists:break
    capture(d,out,'checkout-fees');parse(out,a.context_dir);export_bundle(out)

if __name__=='__main__':main()
