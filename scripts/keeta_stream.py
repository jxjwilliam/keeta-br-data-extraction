#!/usr/bin/env python3
"""逐条持久化：内部 SQLite 为提交账本，CSV 每条原子快照，XLSX 同步快照。
运行命令：见README.md；当前X3 --serial f753a0f3，店间至少180秒。
恢复：加 --resume outputs/internal/streams/<会话目录>。
优先简单商品，支持明确的单选必选规格；不下单、不改账号、不操作优惠。
"""
import argparse,csv,gzip,hashlib,importlib.util,json,os,re,shutil,sqlite3,subprocess,sys,tempfile,time,traceback,threading,signal,itertools
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('keeta_v4',ROOT/'scripts/keeta_scripe-v4.py')
k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k)

class RunDeadlineReached(KeyboardInterrupt):
    pass

def stop_deadline(clock,zone,now=None):
    from zoneinfo import ZoneInfo
    local=now or datetime.now(ZoneInfo(zone))
    hour,minute=map(int,clock.split(':'))
    target=local.replace(hour=hour,minute=minute,second=0,microsecond=0)
    if target<=local:raise ValueError('截止时间已过；请指定今天尚未到达的时刻')
    return target

def arm_deadline(deadline):
    if deadline is None:return
    def interrupt(signum,frame):raise RunDeadlineReached('达到用户指定截止时间')
    signal.signal(signal.SIGALRM,interrupt)
    signal.setitimer(signal.ITIMER_REAL,max(.001,deadline.timestamp()-time.time()))

def save_run_status(ledger,metadata):
    path=ledger.run_metadata_path
    path.write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
    (ledger.directory/'run-status.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))

AUDIT_FIELDS=['attempt_id','collection_status','filled_fields','error_reason','amounts_validated']
EXPORT_FIELDS=k.FIELDS+AUDIT_FIELDS

class Ledger:
    def __init__(self, directory, final):
        self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.final=Path(final);self.final.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.directory/'records.sqlite')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS records (key TEXT PRIMARY KEY, body TEXT NOT NULL, evidence TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS attempts (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
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
    def record_attempt(self,record,evidence,status,reason=''):
        key=Path(evidence).name
        body={field:record.get(field) for field in k.FIELDS}
        body.update(attempt_id=key,collection_status=status,filled_fields=sum(body[f] is not None and body[f]!='' for f in k.FIELDS),error_reason=reason,amounts_validated=status=='complete')
        with self.db:
            old=self.db.execute('SELECT body FROM attempts WHERE id=?',(key,)).fetchone()
            if old and json.loads(old[0])['collection_status']=='complete' and status!='complete':return
            self.db.execute('INSERT OR REPLACE INTO attempts VALUES (?,?)',(key,json.dumps(body,ensure_ascii=False)))
        self.write_csv()
    def export_rows(self):
        attempts={r['attempt_id']:r for (body,) in self.db.execute('SELECT body FROM attempts') for r in [json.loads(body)]}
        for body,evidence in self.db.execute('SELECT body,evidence FROM records ORDER BY rowid'):
            row=json.loads(body);key=Path(evidence).name
            row.update(attempt_id=key,collection_status='complete',filled_fields=sum(v is not None and v!='' for v in row.values()),error_reason='',amounts_validated=True)
            attempts[key]=row
        return [attempts[key] for key in sorted(attempts)]
    def write_csv(self):
        fd,name=tempfile.mkstemp(prefix='.csv-',dir=self.final)
        try:
            with os.fdopen(fd,'w',encoding='utf-8-sig',newline='') as f:
                w=csv.DictWriter(f,fieldnames=EXPORT_FIELDS);w.writeheader();w.writerows(self.export_rows());f.flush();os.fsync(f.fileno())
            os.replace(name,self.csv_path)
            audit=self.export_rows();complete=sum(r['collection_status']=='complete' for r in audit)
            stats={'attempts':len(audit),'complete':complete,'partial':sum(r['collection_status']=='partial' for r in audit),'failed':sum(r['collection_status']=='failed' for r in audit),'navigation':sum(r['collection_status']=='navigation' for r in audit),'complete_rate':complete/sum(r['collection_status']!='navigation' for r in audit) if any(r['collection_status']!='navigation' for r in audit) else None,'field_coverage':{field:sum(r.get(field) is not None and r.get(field)!='' for r in audit) for field in k.FIELDS}}
            (self.directory/'statistics.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2))
        finally:
            if Path(name).exists():Path(name).unlink()
    def write_xlsx(self):
        rows=self.export_rows()
        if not rows:return
        runtime=Path(os.environ.get('KEETA_RUNTIME',Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies'))
        node=runtime/'node/bin/node';modules=runtime/'node/node_modules'
        if not node.exists() or not (modules/'@oai/artifact-tool').exists():
            raise RuntimeError('XLSX 运行时缺失，CSV/账本已保存；见docs/resources.md')
        with tempfile.TemporaryDirectory(prefix='keeta-stream-xlsx-') as t:
            work=Path(t);(work/'node_modules').symlink_to(modules,target_is_directory=True)
            data=work/'records.json';target=work/'snapshot.xlsx'
            data.write_text(json.dumps([{f:r.get(f) for f in EXPORT_FIELDS} for r in rows],ensure_ascii=False))
            shutil.copy2(ROOT/'scripts/export_keeta_stream.mjs',work/'export.mjs')
            result=subprocess.run([str(node),str(work/'export.mjs'),str(data),str(target),str(ROOT),str(getattr(self,'run_metadata_path',''))],capture_output=True,text=True)
            (self.directory/'xlsx.log').write_text(result.stdout+'\n'+result.stderr)
            if result.returncode:raise RuntimeError('XLSX 更新失败，CSV/账本已保存')
            # 成品完整后原子替换；临时JSON/XLSX随目录释放，不留重复快照。
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


class AccessPaused(RuntimeError):
    pass

def guard_access(ns, session):
    blob="\n".join(n["text"] for n in ns).lower()
    if any(t in blob for t in ["access error", "too many requests", "too frequent", "try again later", "access restricted", "verify you are human", "muitas solicitações", "enter verification code", "security verification", "captcha"]):
        reason="页面出现访问异常或验证提示，停止采集；已有结果保留"
        (Path(session)/"access-paused.json").write_text(json.dumps({"time":datetime.now(k.TZ).isoformat(),"reason":reason},ensure_ascii=False))
        raise AccessPaused(reason)
    return ns

class PageRecovered(RuntimeError):
    """页面已恢复，但旧动作作废，必须重新定位。"""

class FeedWindowExhausted(RuntimeError):
    pass

class RecoveryFailed(RuntimeError):
    pass

def page_kind(ns):
    labels=[n['text'].strip() for n in ns];lower={x.lower() for x in labels}
    title=labels[0].lower() if labels else ''
    if not labels:return 'empty'
    if is_voucher_page(ns):return 'vouchers'
    if any(n.get('description') and n['text'].lower() in ('close ad','dismiss ad') for n in ns):return 'advertisement'
    if lower & {'advertisement','sponsored'} and lower & {'close','dismiss','skip ad'}:return 'advertisement'
    # Checkout 自身有 Payment method 和 Place order，不能凭它们误判。
    if title=='checkout':return 'checkout'
    if title in ('payment methods','select payment method','add payment method','add a card','add card','payment details'):
        return 'payment'
    if title in ('confirm payment','confirm order','review and pay','payment confirmation'):
        return 'order_confirmation'
    if title in ('order placed','order confirmed','payment successful'):
        return 'submitted_order'
    close=bool(lower & {'close','close ad','dismiss','dismiss ad','skip ad'})
    promo=any(any(word in x.lower() for word in ['advertisement','sponsored','welcome gift','promotion','voucher','promo']) for x in labels)
    if close and promo:return 'advertisement'
    if title in ('select delivery address','addresses'):return 'addresses'
    if title=='my orders':return 'orders'
    if 'Settings' in labels and 'Orders' in labels:return 'account'
    if 'Add to cart' in labels:return 'product'
    if 'Home' in labels and 'Account' in labels:return 'home'
    if 'Address' in labels and ('Open' in labels or 'Closed' in labels):return 'shop_info'
    if any(x.strip('\ufeff ').lower()=='delivery' for x in labels) and any('R$' in x for x in labels):return 'shop'
    return 'unknown'

NORMAL_PAGES={'checkout','addresses','orders','account','product','home','shop_info','shop'}
IRREGULAR_PAGES={'vouchers','payment','order_confirmation','advertisement','unknown'}

def is_voucher_page(ns):
    labels={n['text'].strip().lower() for n in ns}
    return 'vouchers' in labels and bool(labels & {'past vouchers','enter your code'})

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


def simple_product_candidates(ns,size):
    """用商品价上方同列标题作为入口，优先非套餐/无定制标记的候选。"""
    width,height=size;found=[]
    for price in ns:
        if not re.fullmatch(r'R\$\s*[\d.,]+',price['text']) or price['b'][1]<height*.55:continue
        titles=[n for n in ns if n['b'][1]>=height*.5 and 0<=price['b'][1]-n['b'][3]<=45 and abs(n['b'][0]-price['b'][0])<25 and not re.search(r'R\$|off|voucher|Customisable|After voucher|1st order',n['text'],re.I)]
        if not titles:continue
        title=max(titles,key=lambda n:n['b'][3])
        if title['text'] not in [n['text'] for n in found]:found.append(title)
    if found:return sorted(found,key=lambda n:('combo' in n['text'].lower(),n['b'][1]))
    return [n for n in ns if n['text']=='Customisable' and n['b'][1]>height*.5]


def partial_record(run,name=None):
    """独立提取可见字段；不复用金额校验失败的派生值。"""
    import xml.etree.ElementTree as E
    row={f:None for f in k.FIELDS};sources={}
    def read(label):
        path=run/(label+'.xml')
        if path.exists():return k.nodes(E.parse(path).getroot())
        zipped=run/(label+'.xml.gz')
        if zipped.exists():
            with gzip.open(zipped,'rb') as f:return k.nodes(E.parse(f).getroot())
        return []
    top=read('checkout-top');fees=read('checkout-fees');shop=read('shop-info')
    metadata=run/'attempt.json'
    saved_name=json.loads(metadata.read_text()).get('shop_name') if metadata.exists() else None
    row.update(country='BR',platform='Keeta',shop_name=name or saved_name or (shop[0]['text'] if shop else None))
    for label in ['checkout-top','shop-info']:
        meta=run/(label+'.json')
        if meta.exists():
            stamp=json.loads(meta.read_text())['captured_at'];row['crawl_time']=stamp;row['batch_no']=datetime.fromisoformat(stamp).strftime('%Y%m%d');break
    labels=[n['text'] for n in shop]
    if 'Address' in labels:
        i=labels.index('Address')
        if i+1<len(labels):row['shop_address']=labels[i+1]
    if 'Open' in labels:row['shop_status']='open'
    elif 'Closed' in labels:row['shop_status']='close'
    if top and not any(n['text']=='Select a delivery address' for n in top):
        address=[n['text'] for n in top if re.search(r'^(Rua |R\. |Av\.|Avenida )',n['text'])]
        if len(address)==1:
            row['crawl_address']=address[0]
            if 'São Paulo' in address[0]:row['city_name']='São Paulo'
        stamp_path=run/'checkout-top.json'
        if stamp_path.exists():
            stamp=json.loads(stamp_path.read_text())['captured_at']
            eta=next((n['text'] for n in top if n['text'].startswith('Est. arrival ')),None)
            value=k.eta_minutes(eta,stamp)
            if value:row['ceta_min'],row['ceta_max']=value
    items=list(dict.fromkeys(n['text'] for page in (top,fees) for n in page if re.match(r'^\d+\s*[×x]\s+',n['text'])))
    if items:row['product_info']='; '.join(items)
    for label,field in [('Subtotal','product_original'),('Service fee','service_final')]:
        try:
            values=k.row_money(fees,label)
            if len(values)==1:row[field]=values[0]
        except ValueError:pass
    # 单一服务费的原价口径与项目约定一致，其他金额不反推。
    if row['service_final'] is not None:row['service_original']=row['service_final']
    try:
        values=k.checkout_total(fees)
        if len(values)==1:row['total_final']=values[0]
    except ValueError:pass
    try:
        values=k.row_money(fees,'Delivery fee')
        label=next(n for n in fees if n['text']=='Delivery fee');y=(label['b'][1]+label['b'][3])/2
        free=any(n['text'].lower() in ('free','grátis','gratis') and n['b'][0]>label['b'][2] and abs((n['b'][1]+n['b'][3])/2-y)<25 for n in fees)
        if len(values)==2:row['delivery_original'],row['delivery_final']=values
        elif len(values)==1:
            row['delivery_final']=0 if free else values[0]
            if free:row['delivery_original']=values[0]
    except (ValueError,StopIteration):pass
    context=run/'account-context.json'
    if context.exists():
        account=json.loads(context.read_text())
        for field in ['user_completed_orders_count','account_type']:row[field]=account.get(field)
    for field,value in row.items():
        if value is not None:sources[field]='本次已保存页面/上下文；部分记录未通过完整金额校验'
    (run/'partial-evidence.json').write_text(json.dumps({'record':row,'field_sources':sources,'amounts_validated':False},ensure_ascii=False,indent=2))
    return row


def backfill_attempts(session,ledger):
    complete={Path(e).name:json.loads(body) for body,e in ledger.db.execute('SELECT body,evidence FROM records')}
    for run in sorted(session.glob('attempt_*')):
        if run.name in complete:ledger.record_attempt(complete[run.name],run,'complete');continue
        reason=(run/'failure.log').read_text().splitlines()[-1] if (run/'failure.log').exists() else '历史尝试中断或未完成'
        row=partial_record(run)
        if row.get('shop_name')=='Vouchers':
            # 经用户截图和原始证据确认，此条是导航事件，不是店铺失败。
            row={f:None for f in k.FIELDS}
            ledger.record_attempt(row,run,'navigation','误入优惠券页，已忽略；不计入店铺成功率')
            continue
        ledger.record_attempt(row,run,'partial' if any(row.get(f) is not None for f in ['shop_name','shop_address','product_info','total_final']) else 'failed',reason)
    ledger.write_xlsx()
    rows=[r for r in ledger.export_rows() if r['collection_status']!='navigation'];ok=sum(r['collection_status']=='complete' for r in rows)
    print('ATTEMPTS',len(rows),'COMPLETE',ok,'OTHER',len(rows)-ok,'RATE',f'{ok/len(rows):.1%}' if rows else 'N/A',flush=True)


def recover_saved_attempts(session,ledger):
    """只处理本地证据；绝不为解析错误重新请求页面。"""
    committed={r[0] for r in ledger.db.execute('SELECT evidence FROM records')}
    recovered=0
    for run in sorted(session.glob('attempt_*')):
        if str(run) in committed or str(run.resolve()) in {str(Path(x).resolve()) for x in committed}:continue
        if not all((run/(name+'.xml')).exists() for name in ('checkout-top','checkout-fees','shop-info')):continue
        try:
            k.parse(run)
            source=run/'account-context.json'
            account=json.loads(source.read_text()) if source.exists() else {}
            row=assemble_record(run,account)
            if ledger.append(row,run):recovered+=1
        except Exception as e:
            (run/'recovery-error.log').write_text(str(e))
    if recovered:ledger.write_xlsx()
    print('OFFLINE RECOVERED',recovered,flush=True)
    return recovered


class Collector:
    def __init__(self,d,session,ledger):
        self.d=d;self.session=session;self.ledger=ledger
        self.account={};self.done={r.get('shop_name') for r in ledger.rows()}
        self.tried=set();self.failures=0;self.recovery_count=0
        checkpoint=self.session/'feed-cursor.json'
        self.feed_offset=json.loads(checkpoint.read_text()).get('offset',0) if checkpoint.exists() else 0
        for attempt in self.session.glob('attempt_*'):
            if (attempt/'failure.log').exists() and '商品存在必选规格' not in (attempt/'failure.log').read_text():
                try:
                    name=k.context_fields(attempt).get('shop_name')
                    if name:self.done.add(name)
                except Exception:
                    pass
    def texts(self):
        now=time.monotonic()
        if now-getattr(self,'_read_at',-100)<0.4:return self._last_nodes
        root=__import__('xml.etree.ElementTree',fromlist=['']).fromstring(self.d.dump_hierarchy())
        ns=k.nodes(root)
        for node in root.iter('node'):
            desc=node.get('content-desc','')
            if node.get('package')==k.PACKAGE and not node.get('text') and desc.lower() in ('close ad','dismiss ad'):
                ns.append({'text':desc,'b':list(map(int,re.findall(r'\d+',node.get('bounds','')))),'description':True})
        ns=guard_access(ns,self.session)
        self._last_nodes=ns;self._read_at=time.monotonic()
        return ns
    def log_navigation(self,event,kind,action):
        with (self.session/'navigation.jsonl').open('a') as f:
            f.write(json.dumps({'time':datetime.now(k.TZ).isoformat(),'event':event,'page':kind,'action':action},ensure_ascii=False)+'\n')
    def recover_page(self):
        self._read_at=-100
        ns=self.texts();kind=page_kind(ns)
        if kind in NORMAL_PAGES:return False
        if kind=='empty':raise RecoveryFailed('页面为空或锁屏，停止恢复')
        if kind=='submitted_order':raise RecoveryFailed('检测到订单已提交页面，暂停请用户核对')
        count=getattr(self,'recovery_count',0)
        if count>=6:raise RecoveryFailed('本进程页面恢复预算已用完，停止而非循环')
        self.recovery_count=count+1
        last=None;unchanged=0
        for step in range(3):
            # 每次读取先经过 guard_access；访问限制/验证码永不当广告跳过。
            if self.d.app_current().get('package')!=k.PACKAGE:
                raise RecoveryFailed('已离开Keeta，停止恢复，避免操作外部支付或其他App')
            action='back'
            if kind=='advertisement':
                close=next((n for n in ns if n['text'].lower() in ('close ad','dismiss ad','close','dismiss','skip ad')),None)
                if close:
                    selector=self.d(description=close['text']) if close.get('description') else self.d(text=close['text'])
                    selector.click();action='dismiss'
                else:self.d.press('back')
            else:self.d.press('back')
            self.log_navigation('recover_step',kind,action)
            time.sleep(1);self._read_at=-100
            ns=self.texts();kind=page_kind(ns)
            if kind in NORMAL_PAGES:
                self.log_navigation('recovered',kind,'relocalize')
                print('RECOVERED PAGE',kind,flush=True);return True
            if kind in ('empty','submitted_order'):raise RecoveryFailed('恢复进入空页面或订单提交页面，停止')
            fingerprint=tuple(n['text'] for n in ns)
            unchanged=unchanged+1 if fingerprint==last else 0;last=fingerprint
            if unchanged>=1:raise RecoveryFailed('返回后页面重复不变，停止恢复，避免死循环')
        raise RecoveryFailed('最多三步仍未返回正常页面，停止恢复')
    def wait(self,expected=None):
        self._read_at=-100
        previous=None;start=time.monotonic()
        while time.monotonic()-start<10:
            time.sleep(1)
            ns=self.texts();labels=[n['text'] for n in ns]
            ready=bool(ns) and not any(x.lower() in ('loading','loading...','carregando...') for x in labels)
            if ready and labels==previous:
                if page_kind(ns) in IRREGULAR_PAGES:
                    self.recover_page()
                    raise PageRecovered('意外页面已退出；旧坐标/动作作废，跳过当前操作重新定位')
                if page_kind(ns)=='submitted_order':raise RecoveryFailed('检测到订单已提交页面，暂停请用户核对')
                if not expected or expected in labels:return
            previous=labels
        self.recover_page()
        raise PageRecovered('页面超时，已检查恢复；旧动作作废')
    def click(self,text):
        if text.strip().lower() in ['place order','fazer pedido','pay now','confirm payment','confirm order','pay','pagar']:raise RuntimeError('禁止下单')
        if page_kind(self.texts()) in IRREGULAR_PAGES:
            self.recover_page();raise PageRecovered('动作前发现意外页，已恢复并取消旧动作')
        self.d(text=text).click()
        self.wait({'Check out':'Checkout','Account':'Settings','Select a delivery address':'Select delivery address'}.get(text))
    def leave_vouchers(self):
        if not is_voucher_page(self.texts()):return False
        return self.recover_page()
    def home(self):
        if self.d.app_current().get('package')!=k.PACKAGE:
            self.d.app_start(k.PACKAGE);self.wait()
        for _ in range(5):
            if page_kind(self.texts()) not in NORMAL_PAGES:
                self.recover_page();continue
            if not self.texts():raise RuntimeError('手机息屏、锁屏或页面树为空，暂停等待解锁')
            if self.d(text='Back to Top').exists:
                self.click('Back to Top');return
            if self.d(text='Home').exists:
                self.click('Home');return
            self.d.press('back')
            try:self.wait()
            except PageRecovered:continue
        raise RecoveryFailed('无法返回首页，停止而非重复导航')
    def account_context(self):
        existing=self.session/'account'/'orders.json'
        if existing.exists():
            stamp=datetime.fromisoformat(json.loads(existing.read_text())['captured_at'])
            scope=self.session/'device.json'
            same_device=scope.exists() and json.loads(scope.read_text()).get('serial')==self.d.serial
            if same_device and 0 <= (datetime.now(k.TZ)-stamp).total_seconds() <= 3600:
                self.account={key:value for key,value in k.context_fields(existing.parent).items() if key in ['user_completed_orders_count','account_type']}
                return
        # 已在账号页时直接使用订单入口，避免重复点击导致页面跳转。
        if not (self.d(text='Settings').exists and self.d(text='Orders').exists):
            self.home();self.click('Account')
        if not self.d(text='Orders').exists:
            raise RuntimeError('账号页订单入口不存在，停止而非盲点')
        self.d(text='Orders')[0].click();self.wait()
        out=self.session/'account';out.mkdir(exist_ok=True)
        ns=k.capture(self.d,out,'orders')
        if any(n['text']=='No orders yet' for n in ns):self.account={'user_completed_orders_count':0,'account_type':0}
        (self.session/'device.json').write_text(json.dumps({'serial':self.d.serial,'account_checked_at':datetime.now(k.TZ).isoformat()}))
        self.home()
    def check_limit(self):
        self.texts()
    def advance_feed(self,offset):
        if offset>12:raise RecoveryFailed('已达到列表深度预算，停止而非无界滚动')
        self.feed_offset=offset
        (self.session/'feed-cursor.json').write_text(json.dumps({'offset':offset,'updated_at':datetime.now(k.TZ).isoformat()}))
        self.log_navigation('feed_cursor','home','advance')
    def open_shop(self):
        if page_kind(self.texts()) not in NORMAL_PAGES:self.recover_page()
        if self.d(text='Add to cart').exists:
            self.d.press('back');self.wait()
        if self.d(text='Check out').exists:
            ns=self.texts()
            if ns and ns[0]['text'].strip() not in self.done:
                return ns[0]['text'].strip()
        self.home()
        base=getattr(self,'feed_offset',0)
        for _ in range(base):
            self.check_limit()
            w,h=self.d.window_size();self.d.swipe(w//2,int(h*.76),w//2,int(h*.35),.5);self.wait()
        opened=0
        for local_scroll in range(4):
            scroll=base+local_scroll
            self.check_limit()
            import xml.etree.ElementTree as E
            candidates=[]
            for n in E.fromstring(self.d.dump_hierarchy()).iter('node'):
                if n.get('content-desc')=='feed shopcard':
                    card_names={x.get('text','').strip() for x in n.iter('node')}
                    if card_names & self.done:continue
                    b=list(map(int,re.findall(r'-?\d+',n.get('bounds',''))))
                    if len(b)==4 and b[3]-b[1]>220 and b[1]>350 and b[3]<2400:candidates.append(b)
            for b in candidates:
                key=(scroll,tuple(b))
                if key in self.tried:continue
                if opened>=6:
                    self.advance_feed(scroll+1)
                    raise FeedWindowExhausted('当前列表窗口预算用完，已保存下一页游标')
                opened+=1
                self.tried.add(key);self.d.click((b[0]+b[2])//2,(b[1]+b[3])//2)
                try:self.wait()
                except PageRecovered:
                    return self.open_shop_after_recovery()

                ns=self.texts()
                if page_kind(ns) not in NORMAL_PAGES:
                    self.recover_page();return self.open_shop_after_recovery()
                if not ns:raise RuntimeError('页面没有可读取内容')
                if not any(n['text'].strip('\ufeff ').lower()=='delivery' for n in ns) or not any('R$' in n['text'] for n in ns):
                    self.d.press('back');self.wait();continue
                name=ns[0]['text'].strip()
                if name in self.done:
                    self.d.press('back');self.wait();continue
                return name
            w,h=self.d.window_size();self.d.swipe(w//2,int(h*.76),w//2,int(h*.35),.5);self.wait()
        self.advance_feed(base+4)
        raise FeedWindowExhausted('当前四页没有新店铺，已保存下一窗口游标')
    def open_shop_after_recovery(self):
        retries=getattr(self,'_navigation_retries',0)
        if retries>=2:raise RecoveryFailed('进店导航连续偏离，停止恢复')
        self._navigation_retries=retries+1
        try:return self.open_shop()
        finally:self._navigation_retries=retries
    def quote(self,name,run):
        (run/'account-context.json').write_text(json.dumps(self.account,ensure_ascii=False))
        self.click(name)
        ns=k.capture(self.d,run,'shop-info');facts=k.context_fields(run)
        if facts.get('shop_status')!='open':raise RuntimeError('没有明确 Open 状态，跳过')
        self.d.press('back');self.wait()
        if not self.d(text='Check out').exists(timeout=2):
            # 只有当前店铺没有可结算购物车时才加购。
            ns=self.texts();candidates=simple_product_candidates(ns,self.d.window_size())
            if not candidates:raise RuntimeError('没有可确认的商品入口')
            candidate=candidates[0];self.d.click((candidate['b'][0]+candidate['b'][2])//2,(candidate['b'][1]+candidate['b'][3])//2);self.wait()
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
            address=self.d(text='Rua Jandaia, 7550, São Paulo, SP')
            if not address.exists:
                raise RuntimeError('结算未选地址：未找到用户指定的7550保存地址')
            address.click();self.wait()
            ns=k.capture(self.d,run,'checkout-top')
            if any(n['text']=='Select a delivery address' for n in ns):
                raise RuntimeError('结算未选地址：7550选择尚未确认')
        for _ in range(3):
            self.d.swipe(w//2,int(h*.78),w//2,int(h*.35),.4);self.wait()
            if self.d(text='Service fee').exists:break
        k.capture(self.d,run,'checkout-fees');k.parse(run)
        return assemble_record(run,self.account)


def assemble_record(run,account):
    facts=k.context_fields(run)
    evidence=json.loads((run/'evidence.json').read_text());row=evidence['record']
    if not row.get('crawl_address') or not row.get('city_name'):
        raise RuntimeError('地址尚未明确选中，拒绝写入有效记录')
    if row['shop_name']!=facts['shop_name']:raise RuntimeError('店名不一致')
    shop_stamp=datetime.fromisoformat(json.loads((run/'shop-info.json').read_text())['captured_at'])
    if abs((datetime.fromisoformat(row['crawl_time'])-shop_stamp).total_seconds())>300:
        raise RuntimeError('店铺动态状态证据超过5分钟，拒绝拼接')
    for field in ['shop_address','shop_status']:row[field]=facts.get(field)
    row.update(account)
    selection_path=run/'selected-options.json'
    selected=json.loads(selection_path.read_text()) if selection_path.exists() else []
    if selected:
        row['product_info']+=' [规格: '+ '; '.join(c['group']+'='+c['option'] for c in selected)+']'
        evidence['selected_options']=selected
        evidence['field_sources']['product_info']='Checkout 商品文字及本轮商品规格选择页面'
    evidence['record']=row;evidence['stream_context']={'account':account,'shop_captured_at':json.loads((run/'shop-info.json').read_text())['captured_at']}
    for field in ['shop_address','shop_status']:evidence['field_sources'][field]='本轮同店详情页'
    for field in account:evidence['field_sources'][field]='本会话同账号订单空历史；类型按用户确认规则派生'
    (run/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
    (run/'draft.csv').unlink(missing_ok=True)
    return row

def main():
    p=argparse.ArgumentParser();p.add_argument('--serial',default='f753a0f3');p.add_argument('--interval',type=float,default=180);p.add_argument('--resume',type=Path);p.add_argument('--keep-screenshots',type=int,default=10);p.add_argument('--max-attempts',type=int,default=3);p.add_argument('--access-restored',action='store_true');p.add_argument('--continuous',action='store_true',help='持续到手动停止/截止/安全停止；空窗口冷却后推进，连续三个空窗口仍停止');p.add_argument('--stop-at',help='当天截止HH:MM');p.add_argument('--run-timezone',default='America/Vancouver');a=p.parse_args()
    from zoneinfo import ZoneInfo
    try:
        run_zone=ZoneInfo(a.run_timezone)
        deadline=stop_deadline(a.stop_at,a.run_timezone) if a.stop_at else None
    except (ValueError,KeyError) as e:p.error(str(e))
    if a.keep_screenshots<0:p.error('keep-screenshots 必须为非负数')
    session=a.resume or ROOT/'outputs/internal/streams'/('continuous_'+datetime.now(k.TZ).strftime('%Y%m%d_%H%M%S'))
    marker=session/'access-paused.json'
    if marker.exists():
        if not a.access_restored:p.error('此前访问异常已持久暂停；确认恢复后使用 --access-restored')
        marker.rename(session/('access-paused-'+datetime.now(k.TZ).strftime('%Y%m%d_%H%M%S')+'.json'))
    if a.max_attempts<1:p.error('max-attempts 必须大于 0')
    ledger=Ledger(session,ROOT/'outputs/final');ledger.write_csv()
    run_started=datetime.now(run_zone)
    executions=session/'executions';executions.mkdir(exist_ok=True)
    ledger.run_metadata_path=executions/('run_'+run_started.strftime('%Y%m%d_%H%M%S_%f')+'.json')
    metadata={'started_at':run_started.isoformat(timespec='seconds'),'ended_at':None,'deadline':deadline.isoformat() if deadline else None,'timezone':a.run_timezone,'status':'running','stop_reason':None}
    save_run_status(ledger,metadata)
    print('RUN START',metadata['started_at'],'STOP AT',metadata['deadline'],flush=True)
    print('SESSION',session,flush=True);print('CSV',ledger.csv_path,flush=True)
    stop_awake=threading.Event()
    try:
        arm_deadline(deadline)
        recover_saved_attempts(session,ledger)
        backfill_attempts(session,ledger)
        import uiautomator2 as u
        d=u.connect(a.serial);d.jsonrpc.setConfigurator({'waitForIdleTimeout':0})
        def keep_awake():
            while not stop_awake.is_set():
                if deadline and time.time()>=deadline.timestamp():return
                subprocess.run(['adb','-s',a.serial,'shell','input','keyevent','KEYCODE_WAKEUP'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                stop_awake.wait(5)
        threading.Thread(target=keep_awake,daemon=True).start()
        collector=Collector(d,session,ledger)
        collector.account_context()
        empty_windows=0
        indices=itertools.count() if a.continuous else range(a.max_attempts)
        for attempt_index in indices:
            collector.check_limit()
            try:
                try:name=collector.open_shop()
                except PageRecovered:name=collector.open_shop_after_recovery()
            except FeedWindowExhausted as e:
                if not a.continuous:raise
                empty_windows+=1
                if empty_windows>=3:raise RecoveryFailed('连续三个列表窗口没有新增店铺，停止无效访问')
                print('FEED COOLDOWN',str(e),'next offset',collector.feed_offset,flush=True)
                time.sleep(max(a.interval,180));continue
            empty_windows=0
            run=session/('attempt_'+datetime.now(k.TZ).strftime('%H%M%S_%f'));run.mkdir()
            (run/'attempt.json').write_text(json.dumps({'shop_name':name,'started_at':datetime.now(k.TZ).isoformat()},ensure_ascii=False))
            try:
                row=collector.quote(name,run)
                ledger.append(row,run);ledger.record_attempt(row,run,'complete');collector.done.add(name);collector.failures=0
                print('SAVED',len(ledger.rows()),name,sum(v is not None for v in row.values()),'/30',flush=True)
                try:ledger.write_xlsx()
                except Exception as e:print(str(e),flush=True)
            except PageRecovered as e:
                ledger.record_attempt(partial_record(run,name),run,'partial',str(e));ledger.write_xlsx()
                collector.done.add(name)
                print('PARTIAL RECOVERED',name,str(e),flush=True)
            except AccessPaused as e:
                ledger.record_attempt(partial_record(run,name),run,'partial',str(e));ledger.write_xlsx()
                raise
            except Exception as e:
                collector.failures+=1
                (run/'failure.log').write_text(traceback.format_exc())
                ledger.record_attempt(partial_record(run,name),run,'partial',str(e))
                ledger.write_xlsx()
                print('PARTIAL',name,str(e),flush=True)
                # 已尝试店不重复加购，不把失败记作有效样本。
                collector.done.add(name)
                if isinstance(e,RecoveryFailed):raise
                if any(t in str(e) for t in ['购物车冲突','结算未选地址','地址尚未','限流','页面未稳定']):raise
                if collector.failures>=3:raise RuntimeError('连续三店失败，停止无效重试')
            trim_evidence(session,a.keep_screenshots)
            if a.continuous or attempt_index+1<a.max_attempts:
                time.sleep(max(a.interval,180))
        print("BATCH COMPLETE：保守小批次结束，等待评估后再继续",flush=True)
    except RunDeadlineReached:
        metadata['stop_reason']='deadline'
        print('DEADLINE：停止手机采集，保存已有记录',flush=True)
    except KeyboardInterrupt:
        metadata['stop_reason']='interrupted'
        print('STOPPED：已写记录保留',len(ledger.rows()),flush=True)
    except Exception as e:
        metadata['stop_reason']=str(e)
        (session/'stop.log').write_text(traceback.format_exc());print('STOPPED',str(e),'已保存',len(ledger.rows()),flush=True)
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        stop_awake.set()
        metadata.update(status='stopped',ended_at=datetime.now(run_zone).isoformat(timespec='seconds'))
        metadata['stop_reason']=metadata['stop_reason'] or 'attempt_limit'
        save_run_status(ledger,metadata)
        trim_evidence(session,a.keep_screenshots)
        reported={r['attempt_id'] for r in ledger.export_rows()}
        for unfinished in session.glob('attempt_*'):
            if unfinished.name not in reported:
                row=partial_record(unfinished)
                ledger.record_attempt(row,unfinished,'partial' if row.get('shop_name') else 'failed','运行中断或提前停止；仅保留已读字段')
        ledger.write_csv()
        if ledger.export_rows():
            try:ledger.write_xlsx()
            except Exception as e:print('保留 CSV；',str(e),flush=True)
        metadata['export_finished_at']=datetime.now(run_zone).isoformat(timespec='seconds')
        save_run_status(ledger,metadata)
        print('RUN END',metadata['ended_at'],'REASON',metadata['stop_reason'],flush=True)
        print('TOTAL',len(ledger.rows()),'ATTEMPTS',len(ledger.export_rows()),flush=True)

if __name__=='__main__':main()
