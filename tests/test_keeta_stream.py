import importlib.util,tempfile,unittest,csv
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('stream',ROOT/'scripts/keeta_stream.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class LedgerTests(unittest.TestCase):
    def record(self,shop):
        row={k:None for k in s.k.FIELDS};row.update(shop_name=shop,crawl_time='2026-10-23T12:00:00-03:00',delivery_final=0);return row
    def test_required_single_choice_only(self):
        ns=[{'text':t} for t in ['Fritas ou Purê?','Required','Select 1','Fritas','Purê','Optional sauce','Optional','Select 1','Paid sauce']]
        self.assertEqual(s.pending_required_choices(ns),[{'group':'Fritas ou Purê?','option':'Fritas'}])
        self.assertEqual(s.pending_required_choices([{'text':t} for t in ['Fritas ou Purê?','Required','Done','Fritas']]),[])
    def test_resume_and_no_duplicate(self):
        with tempfile.TemporaryDirectory() as t:
            run=Path(t)/'session';final=Path(t)/'final';a=s.Ledger(run,final)
            self.assertTrue(a.append(self.record('fixture-A'),'fixture'))
            self.assertTrue(a.append(self.record('fixture-B'),'fixture'))
            self.assertFalse(a.append(self.record('fixture-B'),'fixture'))
            a.db.close();b=s.Ledger(run,final);b.write_csv()
            with b.csv_path.open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
            self.assertEqual([r['shop_name'] for r in rows],['fixture-A','fixture-B'])
            self.assertEqual(rows[0]['delivery_final'],'0');self.assertEqual(rows[0]['shop_id'],'');b.db.close()
    def test_interrupted_snapshot_preserves_committed_records(self):
        with tempfile.TemporaryDirectory() as t:
            run=Path(t)/'session';final=Path(t)/'final';a=s.Ledger(run,final)
            a.append(self.record('fixture-A'),'fixture');before=a.csv_path.read_bytes()
            with patch.object(s.os,'replace',side_effect=OSError('simulated interruption')):
                with self.assertRaises(OSError):a.append(self.record('fixture-B'),'fixture')
            self.assertEqual(a.csv_path.read_bytes(),before)
            a.db.close();b=s.Ledger(run,final);b.write_csv()
            self.assertEqual(len(b.rows()),2);b.db.close()
if __name__=='__main__':unittest.main()
