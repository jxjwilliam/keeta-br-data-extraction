import sys,subprocess,json,datetime,time,re
from pathlib import Path
import xml.etree.ElementTree as E
import uiautomator2 as u
OUT=Path('/Users/william.jiang/Desktop/keeta/outputs/keeta-rerun-20261021')
d=u.connect('f753a0f3')
d.jsonrpc.setConfigurator({'waitForIdleTimeout':0})
args=sys.argv[1:]; label=args.pop(0)
if args: subprocess.run(['adb','-s','f753a0f3','shell','input',*args],check=True)
x=d.dump_hierarchy();r=E.fromstring(x)
nodes=[dict(n.attrib) for n in r.iter('node') if n.get('package')=='com.sankuai.sailor.afooddelivery']
stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
if label.startswith('private-'):
 nodes=[n for n in nodes if not any(s in (n.get('text','')+n.get('content-desc','')).lower() for s in ['@','jiang','william']) and not re.search(r'\+\d[\d\s-]{6,}',n.get('text',''))]
 (OUT/(label+'.json')).write_text(json.dumps({'captured_at_utc':stamp,'nodes':nodes,'privacy':'Contact text excluded; no screenshot saved.'},ensure_ascii=False,indent=2))
elif nodes:
 (OUT/(label+'.json')).write_text(json.dumps({'captured_at_utc':stamp,'nodes':nodes},ensure_ascii=False,indent=2))
 with open(OUT/(label+'.png'),'wb') as f: subprocess.run(['adb','-s','f753a0f3','exec-out','screencap','-p'],stdout=f,check=True)
print(stamp)
print('\n'.join(str((n.get('text'),n.get('content-desc'),n.get('bounds'))) for n in nodes if n.get('text') or n.get('content-desc')))