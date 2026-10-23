"""运行：python3 -m unittest discover -s tests -v（不访问手机）。"""
import importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('keeta',ROOT/'scripts/keeta_scripe-v4.py')
k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k)
class FieldTests(unittest.TestCase):
    def test_split_checkout_items_and_price_change(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            for source in (ROOT/'tests/fixtures/checkout-address-tooltip').glob('checkout-*'):
                if source.suffix in ['.xml','.json']:shutil.copy(source,p/source.name)
            tree=ET.parse(p/'checkout-top.xml')
            for n in tree.iter('node'):
                if n.get('text')=='Total R$43.26':n.set('text','Total R$81.54')
            tree.write(p/'checkout-top.xml')
            tree=ET.parse(p/'checkout-fees.xml');root=tree.getroot()
            for n in root.iter('node'):
                if n.get('text')=='R$63.80' and n.get('bounds')=='[999,1366][1157,1426]':n.set('text','R$127.60')
                if n.get('text')=='R$43.26':n.set('text','R$81.54')
                if n.get('text')=='R$35.52 off applied':n.set('text','R$61.04 off applied')
            for text,bounds in [('1 × Fixture second item','[36,700][917,820]'),('R$38.28','[1001,700][1157,760]'),('R$63.80','[1016,760][1157,820]')]:
                ET.SubElement(root,'node',package=k.PACKAGE,text=text,bounds=bounds)
            tree.write(p/'checkout-fees.xml');k.parse(p)
            result=json.loads((p/'evidence.json').read_text())
            self.assertEqual(result['record']['product_original'],12760)
            self.assertEqual(result['conditions']['quantity'],2)
            for n in root.iter('node'):
                if n.get('text')=='R$38.28' and n.get('bounds')=='[1001,700][1157,760]':n.set('text','R$38.29')
            tree.write(p/'checkout-fees.xml')
            with self.assertRaises(AssertionError):k.parse(p)
    def test_total_footer_fallback_is_unambiguous(self):
        self.assertEqual(k.checkout_total([{'text':'Total R$63.81'}]),[6381])
        with self.assertRaises(ValueError):k.checkout_total([])
        with self.assertRaises(ValueError):k.checkout_total([{'text':'Total R$63.81'},{'text':'Total R$63.81'}])
    def test_timestamp_publication_never_overwrites(self):
        with tempfile.TemporaryDirectory() as t:
            run=Path(t)/'run';run.mkdir();final=Path(t)/'final'
            (run/'draft.xlsx').write_bytes(b'test workbook')
            (run/'draft.csv').write_text('test csv')
            targets=k.publish_files(run,final,'2026-10-22T16:33:17+00:00')
            self.assertEqual(targets[0].name,'latest_20261022_133317.xlsx')
            (run/'draft.xlsx').write_bytes(b'changed')
            with self.assertRaises(FileExistsError):
                k.publish_files(run,final,'2026-10-22T13:33:17-03:00')
            self.assertEqual(targets[0].read_bytes(),b'test workbook')
            self.assertEqual(targets[1].read_text(),'test csv')
    def test_failed_pair_leaves_no_partial_result(self):
        with tempfile.TemporaryDirectory() as t:
            run=Path(t)/'run';run.mkdir();final=Path(t)/'final'
            (run/'draft.xlsx').write_bytes(b'test workbook')
            with self.assertRaises(FileNotFoundError):
                k.publish_files(run,final,'2026-10-22T13:33:17-03:00')
            self.assertEqual(list(final.iterdir()),[])
    def test_eta_ceil(self):
        self.assertEqual(k.eta_minutes('Est. arrival 14:09-14:24','2026-10-22T13:33:17-03:00'),(36,51))
    def test_eta_midnight(self):
        self.assertEqual(k.eta_minutes('Est. arrival 00:05-00:20','2026-10-22T23:50:30-03:00'),(15,30))
    def test_stale_eta_is_missing(self):
        self.assertIsNone(k.eta_minutes('Est. arrival 13:00-13:15','2026-10-22T13:33:17-03:00'))
    def test_account_tiers(self):
        self.assertEqual([k.account_type(n) for n in [0,1,4,5]],[0,1,1,2])
        self.assertIsNone(k.account_type(-1))
    def test_verified_context(self):
        facts=k.context_fields(ROOT/'tests/fixtures/field-research')
        self.assertEqual(facts['shop_status'],'open')
        self.assertEqual(facts['user_completed_orders_count'],0)
        self.assertIn('Rua Wisard, 88',facts['shop_address'])
    def test_orders_visible_is_not_lifetime_count(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);root=ET.Element('hierarchy')
            for text in ['My orders','Delivered','Delivered']:
                ET.SubElement(root,'node',package=k.PACKAGE,text=text,bounds='[0,0][100,100]')
            ET.ElementTree(root).write(p/'orders.xml')
            self.assertNotIn('user_completed_orders_count',k.context_fields(p))
    def test_closing_time_does_not_mean_closed(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);root=ET.Element('hierarchy')
            ET.SubElement(root,'node',package=k.PACKAGE,text='Closes at 22:30',bounds='[0,0][100,100]')
            ET.ElementTree(root).write(p/'shop-info.xml')
            self.assertNotIn('shop_status',k.context_fields(p))
    def test_single_delivery_price_reconciles(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            for source in (ROOT/'tests/fixtures/checkout-address-tooltip').glob('checkout-*'):
                if source.suffix in ['.xml','.json']:shutil.copy(source,p/source.name)
            tree=ET.parse(p/'checkout-top.xml')
            for n in tree.iter('node'):
                if n.get('text')=='Total R$43.26':n.set('text','Total R$53.26')
            tree.write(p/'checkout-top.xml')
            tree=ET.parse(p/'checkout-fees.xml')
            for parent in tree.iter():
                for n in list(parent):
                    if n.get('text')=='R$3.99':parent.remove(n)
            for n in tree.iter('node'):
                if n.get('text')=='R$43.26':n.set('text','R$53.26')
                if n.get('text')=='R$35.52 off applied':n.set('text','R$25.52 off applied')
            tree.write(p/'checkout-fees.xml');k.parse(p)
            row=json.loads((p/'evidence.json').read_text())['record']
            self.assertEqual(row['delivery_original'],1399)
            self.assertEqual(row['delivery_final'],1399)
    def test_free_delivery_is_zero_not_missing(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            for source in (ROOT/'tests/fixtures/checkout-address-tooltip').glob('checkout-*'):
                if source.suffix in ['.xml','.json']:shutil.copy(source,p/source.name)
            for name in ['checkout-top.xml','checkout-fees.xml']:
                tree=ET.parse(p/name)
                for n in tree.iter('node'):
                    if n.get('text')=='R$3.99':n.set('text','Free')
                    if n.get('text')=='R$43.26':n.set('text','R$39.27')
                    if n.get('text')=='Total R$43.26':n.set('text','Total R$39.27')
                    if n.get('text')=='R$35.52 off applied':n.set('text','R$39.51 off applied')
                tree.write(p/name)
            k.parse(p);result=json.loads((p/'evidence.json').read_text())
            self.assertEqual(result['record']['delivery_final'],0)
            self.assertEqual(result['record']['delivery_original'],1399)
    def test_two_item_checkout_reconciles_without_losing_item(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            for source in (ROOT/'tests/fixtures/checkout-address-tooltip').glob('checkout-*'):
                if source.suffix in ['.xml','.json']:shutil.copy(source,p/source.name)
            tree=ET.parse(p/'checkout-top.xml');root=tree.getroot()
            for text,bounds in [('1 × Fixture second item','[36,2100][917,2220]'),('R$38.28','[1001,2100][1157,2160]'),('R$63.80','[1016,2160][1157,2220]')]:
                ET.SubElement(root,'node',package=k.PACKAGE,text=text,bounds=bounds)
            for n in root.iter('node'):
                if n.get('text')=='Total R$43.26':n.set('text','Total R$81.54')
            tree.write(p/'checkout-top.xml')
            tree=ET.parse(p/'checkout-fees.xml')
            for n in tree.iter('node'):
                if n.get('text')=='R$63.80' and n.get('bounds')=='[999,1366][1157,1426]':n.set('text','R$127.60')
                if n.get('text')=='R$43.26':n.set('text','R$81.54')
                if n.get('text')=='R$35.52 off applied':n.set('text','R$61.04 off applied')
            tree.write(p/'checkout-fees.xml');k.parse(p)
            result=json.loads((p/'evidence.json').read_text())
            self.assertEqual(result['record']['product_original'],12760)
            self.assertEqual(result['record']['product_final'],7656)
            self.assertIn('Fixture second item',result['record']['product_info'])
            self.assertEqual(result['conditions']['quantity'],2)
    def test_address_tooltip_is_not_selected_address(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)
            for source in (ROOT/'tests/fixtures/checkout-address-tooltip').glob('checkout-*'):
                if source.suffix in ['.xml','.json']:shutil.copy(source,p/source.name)
            k.parse(p)
            data=json.loads((p/'evidence.json').read_text())
            self.assertIsNone(data['record']['crawl_address'])
            self.assertFalse(data['conditions']['delivery_address_confirmed'])
            self.assertTrue(data['qa']['amounts_reconciled'])
if __name__=='__main__':unittest.main()
