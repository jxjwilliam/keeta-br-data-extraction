#!/usr/bin/env python3
"""逐条持久化：内部 SQLite 为提交账本，CSV 每条原子快照，XLSX 同步快照。
运行：python3 scripts/keeta_stream.py --serial 979f0245 --interval 30
恢复：加 --resume outputs/internal/streams/<会话目录>。
当前只自动选择无需必选规格的商品；不下单、不改账号、不操作优惠。
"""
import argparse,csv,gzip,hashlib,importlib.util,json,os,re,shutil,sqlite3,subprocess,sys,tempfile,time,traceback,threading
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('keeta_v4',ROOT/'scripts/keeta_scripe-v4.py')
k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k)

class Ledger:
    def __init__(self, directory, final):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.final=Path(final);self.final.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.directory/'records.sqlite')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS records (key TEXT PRIMARY KEY, body TEXT NOT NULL, evidence TEXT NOT NULL)')
        self.db.commit()
        self.csv_path=self.final/(self.directory.name+'.csv')
        self.xlsx_path=self.final/(self.directory.name+'.xlsx')
    def rows(self):
        return [json.loads(r[0]) for r in self.db.execute('SELECT body FROM records ORDER BY rowid')]
    def append(self, record, evidence):
        key=hashlib.sha256(json.dumps(record,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        with self.db:
            cursor=self.db.execute('INSERT OR IGNORE INTO records VALUES (?,?,?)',(key,json.dumps(record,ensure_ascii=False),str(evidence)))
        self.write_csv()
        return cursor.rowcount==1
    def write_csv(self):
        fd,name=tempfile.mkstemp(prefix='.csv-',dir=self.final)
        try:
            with os.fdopen(fd,'w',encoding='utf-8-sig',newline='') as f:
                w=csv.DictWriter(f,fieldnames=k.FIELDS);w.writeheader();w.writerows(self.rows());f.flush();os.fsync(f.fileno())
            os.replace(name,self.csv_path)
        finally:
            if Path(name).exists():Path(name).unlink()
    def write_xlsx(self):
        rows=self.rows()
        if not rows:return
        data=self.directory/'records.json';tmp=data.with_suffix('.tmp')
        tmp.write_text(json.dumps(rows,ensure_ascii=False));tmp.replace(data)
        runtime=Path(os.environ.get('KEETA_RUNTIME',Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies'))
        node=runtime/'node/bin/node';modules=runtime/'node/node_modules'
        if not node.exists():raise RuntimeError('XLSX 运行时缺失，CSV/账本已保存')
        target=self.directory/'snapshot.xlsx'
        with tempfile.TemporaryDirectory(prefix='keeta-stream-xlsx-') as t:
            work=Path(t);(work/'node_modules').symlink_to(modules,target_is_directory=True)
            shutil.copy2(ROOT/'scripts/export_keeta_stream.mjs',work/'export.mjs')
            result=subprocess.run([str(node),str(work/'export.mjs'),str(data.resolve()),str(target.resolve()),str(ROOT)],capture_output=True,text=True)
            (self.directory/'xlsx.log').write_text(result.stdout+'\n'+result.stderr)
            if result.returncode:raise RuntimeError('XLSX 更新失败，CSV/账本已保存')
        # 新快照完整写成后再替换；旧的完整工作簿在此之前保持可用。
        fd,name=tempfile.mkstemp(prefix='.xlsx-',dir=self.final)
        try:
            with os.fdopen(fd,'wb') as f:
                f.write(target.read_bytes());f.flush();os.fsync(f.fileno())
            os.replace(name,self.xlsx_path)
        finally:
            if Path(name).exists():Path(name).unlink()

def trim_evidence(session, keep=10):
    attempts=sorted(session.glob('attempt_*'))
    older=attempts[:-keep] if keep else attempts
    for attempt in older:
        for image in attempt.glob('*.png'):
            image.unlink()
        for xml in attempt.glob('*.xml'):
            target=xml.with_suffix('.xml.gz')
            temporary=target.with_suffix('.tmp')
            with xml.open('rb') as src,gzip.open(temporary,'wb') as dest:
                shutil.copyfileobj(src,dest)
            temporary.replace(target);xml.unlink()


def pending_required_choices(ns):
    """只处理明确的单选必选组；Done 组和可选项不触碰。"""
    choices=[]
    for i,n in enumerate(ns):
        if n['text'].strip().lower() not in ('select 1','choose 1'):
            continue
        previous=ns[max(0,i-2):i]
        if not any(x['text']=='Required' for x in previous):
            continue
        if i+1>=len(ns):continue
        option=ns[i+1]
        if option['text'] in ('Required','Optional','Add to cart') or 'R$' in option['text']:
            continue
        title=next((x['text'] for x in previous if x['text']!='Required'),'必选单选')
        choices.append({'group':title,'option':option['text']})
    return choices


class Collector:
    def __init__(self,d,session,ledger):
        self.d=d;self.session=session;self.ledger=ledger
        self.account={};self.done={r.get('shop_name') for r in ledger.rows()}
        self.tried=set();self.failures=0
        for attempt in self.session.glob('attempt_*'):
            if (attempt/'failure.log').exists() and '商品存在必选规格' not in (attempt/'failure.log').read_text():
                try:
                    name=k.context_fields(attempt).get('shop_name')
                    if name:self.done.add(name)
                except Exception:
                    pass
    def texts(self):return k.nodes(__import__('xml.etree.ElementTree',fromlist=['']).fromstring(self.d.dump_hierarchy()))
    def wait(self):time.sleep(2.5)
    def click(self,text):
        if text.lower() in ['place order','fazer pedido','pay now']:raise RuntimeError('禁止下单')
        self.d(text=text).click();self.wait()
    def home(self):
        if self.d.app_current().get('package')!=k.PACKAGE:
            self.d.app_start(k.PACKAGE);self.wait()
        for _ in range(5):
            if not self.texts():raise RuntimeError('手机息屏、锁屏或页面树为空，暂停等待解锁')
            if self.d(text='Back to Top').exists:
                self.click('Back to Top');return
            if self.d(text='Home').exists:
                self.click('Home');return
            self.d.press('back');self.wait()
        raise RuntimeError('无法返回首页')
    def account_context(self):
        existing=self.session/'account'/'orders.json'
        if existing.exists():
            stamp=datetime.fromisoformat(json.loads(existing.read_text())['captured_at'])
            if 0 <= (datetime.now(k.TZ)-stamp).total_seconds() <= 300:
                self.account={key:value for key,value in k.context_fields(existing.parent).items() if key in ['user_completed_orders_count','account_type']}
                return
        self.home();self.click('Account')
        self.d(text='Orders')[0].click();self.wait()
        out=self.session/'account';out.mkdir(exist_ok=True)
        ns=k.capture(self.d,out,'orders')
        if any(n['text']=='No orders yet' for n in ns):self.account={'user_completed_orders_count':0,'account_type':0}
        self.home()
    def check_limit(self):
        blob='\n'.join(n['text'] for n in self.texts()).lower()
        if any(t in blob for t in ['too many requests','too frequent','try again later','access restricted','verify you are human','muitas solicitações']):
            raise RuntimeError('页面出现限流或验证提示，暂停采集；已有结果保留')
    def open_shop(self):
        if self.d(text='Add to cart').exists:
            self.d.press('back');self.wait()
        if self.d(text='Check out').exists:
            ns=self.texts()
            if ns and ns[0]['text'].strip() not in self.done:
                return ns[0]['text'].strip()
        self.home()
        for scroll in range(12):
            self.check_limit()
            import xml.etree.ElementTree as E
            candidates=[]
            for n in E.fromstring(self.d.dump_hierarchy()).iter('node'):
                if n.get('content-desc')=='feed shopcard':
                    b=list(map(int,re.findall(r'-?\d+',n.get('bounds',''))))
                    if len(b)==4 and b[3]-b[1]>220 and b[1]>350 and b[3]<2400:candidates.append(b)
            for b in candidates:
                key=(scroll,tuple(b))
                if key in self.tried:continue
                self.tried.add(key);self.d.click((b[0]+b[2])//2,(b[1]+b[3])//2);self.wait()
                ns=self.texts()
                if not ns:raise RuntimeError('页面没有可读取内容')
                if not any(n['text']=='Delivery\ufeff ' or 'vouchers' in n['text'] for n in ns) and not any('R$' in n['text'] for n in ns):
                    self.d.press('back');self.wait();continue
                name=ns[0]['text'].strip()
                if name in self.done:
                    self.d.press('back');self.wait();continue
                return name
            w,h=self.d.window_size();self.d.swipe(w//2,int(h*.76),w//2,int(h*.35),.5);self.wait()
        raise RuntimeError('当前列表未找到新店铺，停止而非重复插入旧店')
    def quote(self,name,run):
        self.click(name)
        ns=k.capture(self.d,run,'shop-info');facts=k.context_fields(run)
        if facts.get('shop_status')!='open':raise RuntimeError('没有明确 Open 状态，跳过')
        self.d.press('back');self.wait()
        if not self.d(text='Check out').exists(timeout=2):
            # 只有当前店铺没有可结算购物车时才加购。
            ns=self.texts();custom=[n for n in ns if n['text']=='Customisable' and n['b'][1]>1200]
            if not custom:raise RuntimeError('没有可确认的商品入口')
            candidate=custom[0];self.d.click((candidate['b'][0]+candidate['b'][2])//2,(candidate['b'][1]+candidate['b'][3])//2);self.wait()
            ns=self.texts()
            selected=[]
            for _ in range(8):
                choices=pending_required_choices(ns)
                if not choices:break
                choice=choices[0];self.click(choice['option']);selected.append(choice)
                ns=self.texts()
            if pending_required_choices(ns):raise RuntimeError('必选规格未完成，跳过该店')
            (run/'selected-options.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2))
            if selected:k.capture(self.d,run,'product-options')
            if not self.d(text='Add to cart').exists(timeout=3):raise RuntimeError('未找到 Add to cart')
            self.click('Add to cart')
            ns=self.texts()
            if any('another restaurant' in n['text'].lower() or 'clear cart' in n['text'].lower() for n in ns):
                raise RuntimeError('出现购物车冲突，暂停；不清除未知购物车')
        if not self.d(text='Check out').exists(timeout=6):raise RuntimeError('加购未成功或未达起送价')
        self.click('Check out')
        if not self.d(text='Checkout').exists:raise RuntimeError('未到 Checkout')
        w,h=self.d.window_size()
        ns=k.capture(self.d,run,'checkout-top')
        if any(n['text']=='Select a delivery address' for n in ns):
            self.click('Select a delivery address')
            addr=self.d(text='Rua Jandaia, 7550, São Paulo, SP')
            if not addr.exists:raise RuntimeError('结算未选地址，指定已保存地址不存在')
            addr.click();self.wait();ns=k.capture(self.d,run,'checkout-top')
        for _ in range(3):
            self.d.swipe(w//2,int(h*.78),w//2,int(h*.35),.4);self.wait()
            if self.d(text='Service fee').exists:break
        k.capture(self.d,run,'checkout-fees');k.parse(run)
        evidence=json.loads((run/'evidence.json').read_text());row=evidence['record']
        if not row.get('crawl_address') or not row.get('city_name'):
            raise RuntimeError('地址尚未明确选中，拒绝写入有效记录')
        if row['shop_name']!=facts['shop_name']:raise RuntimeError('店名不一致')
        for field in ['shop_address','shop_status']:row[field]=facts.get(field)
        row.update(self.account)
        selection_path=run/'selected-options.json'
        selected=json.loads(selection_path.read_text()) if selection_path.exists() else []
        if selected:
            row['product_info']+=' [规格: '+ '; '.join(c['group']+'='+c['option'] for c in selected)+']'
            evidence['selected_options']=selected
            evidence['field_sources']['product_info']='Checkout 商品文字及本轮商品规格选择页面'
        evidence['record']=row;evidence['stream_context']={'account':self.account,'shop_captured_at':json.loads((run/'shop-info.json').read_text())['captured_at']}
        for field in ['shop_address','shop_status']:evidence['field_sources'][field]='本轮同店详情页'
        for field in self.account:evidence['field_sources'][field]='本会话同账号订单空历史；类型按用户确认规则派生'
        (run/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
        return row

def main():
    p=argparse.ArgumentParser();p.add_argument('--serial',default='979f0245');p.add_argument('--interval',type=float,default=30);p.add_argument('--resume',type=Path);p.add_argument('--keep-screenshots',type=int,default=10);a=p.parse_args()
    if a.keep_screenshots<0:p.error('keep-screenshots 必须为非负数')
    session=a.resume or ROOT/'outputs/internal/streams'/('continuous_'+datetime.now(k.TZ).strftime('%Y%m%d_%H%M%S'))
    ledger=Ledger(session,ROOT/'outputs/final');ledger.write_csv()
    print('SESSION',session,flush=True);print('CSV',ledger.csv_path,flush=True)
    import uiautomator2 as u
    d=u.connect(a.serial);d.jsonrpc.setConfigurator({'waitForIdleTimeout':0})
    stop_awake=threading.Event()
    def keep_awake():
        while not stop_awake.is_set():
            subprocess.run(['adb','-s',a.serial,'shell','input','keyevent','KEYCODE_WAKEUP'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            stop_awake.wait(5)
    threading.Thread(target=keep_awake,daemon=True).start()
    collector=Collector(d,session,ledger)
    try:
        collector.account_context()
        while True:
            collector.check_limit();name=collector.open_shop()
            run=session/('attempt_'+datetime.now(k.TZ).strftime('%H%M%S_%f'));run.mkdir()
            try:
                row=collector.quote(name,run)
                ledger.append(row,run);collector.done.add(name);collector.failures=0
                print('SAVED',len(ledger.rows()),name,sum(v is not None for v in row.values()),'/30',flush=True)
                try:ledger.write_xlsx()
                except Exception as e:print(str(e),flush=True)
            except Exception as e:
                collector.failures+=1
                (run/'failure.log').write_text(traceback.format_exc())
                print('FAILED',name,str(e),flush=True)
                # 已尝试店不重复加购，不把失败记作有效样本。
                collector.done.add(name)
                if any(t in str(e) for t in ['购物车冲突','结算未选地址','地址尚未','限流']):raise
                if collector.failures>=3:raise RuntimeError('连续三店失败，停止无效重试')
            trim_evidence(session,a.keep_screenshots)
            time.sleep(max(a.interval,10))
    except KeyboardInterrupt:
        print('STOPPED：已写记录保留',len(ledger.rows()),flush=True)
    except Exception as e:
        (session/'stop.log').write_text(traceback.format_exc());print('STOPPED',str(e),'已保存',len(ledger.rows()),flush=True)
    finally:
        stop_awake.set()
        trim_evidence(session,a.keep_screenshots)
        ledger.write_csv()
        if ledger.rows():
            try:ledger.write_xlsx()
            except Exception as e:print('保留 CSV；',str(e),flush=True)
        print('TOTAL',len(ledger.rows()),flush=True)

if __name__=='__main__':main()
