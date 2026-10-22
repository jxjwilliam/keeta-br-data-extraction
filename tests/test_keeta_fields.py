"""运行：python3 -m unittest discover -s tests -v（不访问手机）。"""
import importlib.util,json,shutil,tempfile,unittest
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('keeta',ROOT/'scripts/keeta_scripe-v4.py')
k=importlib.util.module_from_spec(spec);spec.loader.exec_module(k)
class FieldTests(unittest.TestCase):
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
