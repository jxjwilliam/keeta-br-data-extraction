import importlib.util,tempfile,unittest,csv
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('stream',ROOT/'scripts/keeta_stream.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class LedgerTests(unittest.TestCase):
    def test_ready_wait_and_access_error(self):
        c=s.Collector.__new__(s.Collector)
        with patch.object(c,'texts',side_effect=[[{'text':'Loading...'}],[{'text':'Checkout'}],[{'text':'Checkout'}]]),patch.object(s.time,'sleep'):
            c.wait('Checkout')
        with patch.object(c,'texts',side_effect=s.AccessPaused('blocked')),patch.object(s.time,'sleep'):
            with self.assertRaises(s.AccessPaused):c.wait()
    def test_simple_product_title_priority(self):
        ns=[{'text':'Combo A','b':[33,1100,200,1140]}, {'text':'R$30.00','b':[33,1140,200,1200]},
            {'text':'Falafel','b':[360,1100,550,1140]}, {'text':'R$20.00','b':[360,1140,550,1200]}]
        self.assertEqual([n['text'] for n in s.simple_product_candidates(ns,(1080,2000))],['Falafel','Combo A'])
    def test_offline_recovery_idempotent_no_phone(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);session=root/'session';run=session/'attempt_1';run.mkdir(parents=True)
            for name in ['checkout-top','checkout-fees','shop-info']:(run/(name+'.xml')).write_text('<hierarchy/>')
            ledger=s.Ledger(session,root/'final')
            with patch.object(s.k,'parse'),patch.object(s,'assemble_record',return_value=self.record('fixture')),patch.object(ledger,'write_xlsx'):
                self.assertEqual(s.recover_saved_attempts(session,ledger),1)
                self.assertEqual(s.recover_saved_attempts(session,ledger),0)
            self.assertEqual(len(ledger.rows()),1);ledger.db.close()
    def test_partial_attempt_upgrade_and_missing_values(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);ledger=s.Ledger(root/'session',root/'final')
            row=self.record('fixture-A')
            ledger.record_attempt(row,root/'attempt_1','partial','fixture failure')
            ledger.record_attempt(row,root/'attempt_1','partial','same attempt')
            self.assertEqual(len(ledger.export_rows()),1)
            audit=ledger.export_rows()[0]
            self.assertEqual(audit['collection_status'],'partial')
            self.assertFalse(audit['amounts_validated'])
            self.assertEqual(audit['filled_fields'],3)
            self.assertIsNone(audit['shop_id']);self.assertEqual(audit['delivery_final'],0)
            ledger.append(row,root/'attempt_1');ledger.record_attempt(row,root/'attempt_1','complete')
            ledger.record_attempt(row,root/'attempt_1','partial','cannot downgrade')
            self.assertEqual(len(ledger.export_rows()),1)
            self.assertTrue(ledger.export_rows()[0]['amounts_validated'])
            ledger.db.close()
    def test_partial_shop_only_keeps_unknown_money_empty(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            (root/'shop-info.xml').write_text('<hierarchy><node package="com.sankuai.sailor.afooddelivery" text="Fixture Shop" bounds="[0,0][100,100]"/><node package="com.sankuai.sailor.afooddelivery" text="Open" bounds="[0,100][100,200]"/></hierarchy>')
            row=s.partial_record(root)
            self.assertEqual(row['shop_name'],'Fixture Shop')
            self.assertEqual(row['shop_status'],'open')
            self.assertIsNone(row['crawl_address']);self.assertIsNone(row['total_final'])
    def test_vouchers_guard_ignores_shop_promotions(self):
        self.assertTrue(s.is_voucher_page([{'text':x} for x in ['Vouchers','Past vouchers','Enter your code','Apply']]))
        self.assertFalse(s.is_voucher_page([{'text':x} for x in ['Fixture Shop','8 vouchers','Delivery']]))
        c=s.Collector.__new__(s.Collector)
        with patch.object(c,'texts',return_value=[{'text':'Vouchers'},{'text':'Past vouchers'}]),patch.object(c,'recover_page',return_value=True) as recover:
            self.assertTrue(c.leave_vouchers());recover.assert_called_once()
    def make_recovery_collector(self,directory):
        from unittest.mock import Mock
        c=s.Collector.__new__(s.Collector);c.session=Path(directory);c.recovery_count=0;c.d=Mock()
        c.d.app_current.return_value={'package':s.k.PACKAGE}
        return c
    def test_page_kinds_checkout_vs_payment_and_ads(self):
        ns=lambda *labels:[{'text':label} for label in labels]
        self.assertEqual(s.page_kind(ns('Checkout','Payment method','Place order')),'checkout')
        self.assertEqual(s.page_kind(ns('Payment methods','Pix','Add card')),'payment')
        self.assertEqual(s.page_kind(ns('Confirm payment','Pay now')),'order_confirmation')
        self.assertEqual(s.page_kind(ns('Order placed')),'submitted_order')
        self.assertEqual(s.page_kind(ns('Advertisement','Close')),'advertisement')
        self.assertEqual(s.page_kind(ns('Checkout','Advertisement','Close')),'advertisement')
        self.assertEqual(s.page_kind(ns('Strange page')),'unknown')
    def test_recovery_backs_out_and_relocalizes(self):
        with tempfile.TemporaryDirectory() as t:
            c=self.make_recovery_collector(t)
            with patch.object(c,'texts',side_effect=[[{'text':'Payment methods'}],[{'text':'Checkout'},{'text':'Place order'}]]),patch.object(s.time,'sleep'):
                self.assertTrue(c.recover_page())
            c.d.press.assert_called_once_with('back');c.d.assert_not_called()
    def test_repeated_page_stops_and_never_clicks_cta(self):
        with tempfile.TemporaryDirectory() as t:
            c=self.make_recovery_collector(t)
            with patch.object(c,'texts',return_value=[{'text':'Confirm payment'},{'text':'Pay now'}]),patch.object(s.time,'sleep'):
                with self.assertRaises(s.RecoveryFailed):c.recover_page()
            self.assertEqual(c.d.press.call_count,2);c.d.assert_not_called()
    def test_ad_only_dismisses_explicit_close(self):
        with tempfile.TemporaryDirectory() as t:
            c=self.make_recovery_collector(t)
            ad=[{'text':'Advertisement'},{'text':'Close'},{'text':'Apply'}]
            with patch.object(c,'texts',side_effect=[ad,[{'text':'Checkout'}]]),patch.object(s.time,'sleep'):
                c.recover_page()
            c.d.assert_called_once_with(text='Close');c.d.press.assert_not_called()
    def test_access_error_is_not_backed_out_and_order_cta_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            c=self.make_recovery_collector(t)
            with patch.object(c,'texts',side_effect=s.AccessPaused('verification')):
                with self.assertRaises(s.AccessPaused):c.recover_page()
            c.d.press.assert_not_called()
            for text in ['Place order','Pay now','Confirm order','Confirm payment']:
                with self.assertRaises(RuntimeError):c.click(text)
            c.d.assert_not_called()
    def test_wait_recovers_and_cancels_stale_action(self):
        with tempfile.TemporaryDirectory() as t:
            c=self.make_recovery_collector(t)
            with patch.object(c,'texts',return_value=[{'text':'Payment methods'}]),patch.object(c,'recover_page',return_value=True) as recover,patch.object(s.time,'sleep'):
                with self.assertRaises(s.PageRecovered):c.wait()
            recover.assert_called_once()
    def test_xlsx_staging_is_temporary_and_failure_preserves_final(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);runtime=root/'runtime'
            (runtime/'node/bin').mkdir(parents=True);(runtime/'node/bin/node').touch()
            (runtime/'node/node_modules/@oai/artifact-tool').mkdir(parents=True)
            ledger=s.Ledger(root/'session',root/'final');ledger.append(self.record('fixture-A'),root/'attempt_1')
            staging=[]
            def export(args,**kwargs):
                staging.append(Path(args[2]).parent)
                self.assertTrue(Path(args[2]).exists())
                Path(args[3]).write_bytes(b'fixture workbook')
                return SimpleNamespace(returncode=0,stdout='',stderr='')
            with patch.dict(s.os.environ,{'KEETA_RUNTIME':str(runtime)}),patch.object(s.subprocess,'run',side_effect=export):ledger.write_xlsx()
            self.assertEqual(ledger.xlsx_path.read_bytes(),b'fixture workbook')
            self.assertFalse(any(path.exists() for path in staging))
            self.assertFalse((ledger.directory/'records.json').exists());self.assertFalse((ledger.directory/'snapshot.xlsx').exists())
            with patch.dict(s.os.environ,{'KEETA_RUNTIME':str(runtime)}),patch.object(s.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='',stderr='fixture failure')):
                with self.assertRaises(RuntimeError):ledger.write_xlsx()
            self.assertEqual(ledger.xlsx_path.read_bytes(),b'fixture workbook');ledger.db.close()
    def test_access_error_persists_pause(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(s.AccessPaused):
                s.guard_access([{ "text":"Access error"}],Path(t))
            self.assertTrue((Path(t)/"access-paused.json").exists())
            self.assertEqual(s.guard_access([{"text":"Home"}],Path(t)),[{"text":"Home"}])
    def record(self,shop):
        row={k:None for k in s.k.FIELDS};row.update(shop_name=shop,crawl_time='2026-10-23T12:00:00-03:00',delivery_final=0);return row
    def test_required_single_choice_only(self):
        ns=[{'text':t} for t in ['Fritas ou Purê?','Required','Select 1','Fritas','Purê','Optional sauce','Optional','Select 1','Paid sauce']]
        self.assertEqual(s.pending_required_choices(ns),[{'group':'Fritas ou Purê?','option':'Fritas'}])
        self.assertEqual(s.pending_required_choices([{'text':t} for t in ['Fritas ou Purê?','Required','Done','Fritas']]),[])
    def test_resume_and_no_duplicate(self):
        with tempfile.TemporaryDirectory() as t:
            run=Path(t)/'session';final=Path(t)/'final';a=s.Ledger(run,final)
            self.assertTrue(a.append(self.record('fixture-A'),'fixture-A'))
            self.assertTrue(a.append(self.record('fixture-B'),'fixture-B'))
            self.assertFalse(a.append(self.record('fixture-B'),'fixture-B'))
            a.db.close();b=s.Ledger(run,final);b.write_csv()
            with b.csv_path.open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
            self.assertEqual([r['shop_name'] for r in rows],['fixture-A','fixture-B'])
            self.assertEqual(rows[0]['delivery_final'],'0');self.assertEqual(rows[0]['shop_id'],'');b.db.close()
    def test_interrupted_snapshot_preserves_committed_records(self):
        with tempfile.TemporaryDirectory() as t:
            run=Path(t)/'session';final=Path(t)/'final';a=s.Ledger(run,final)
            a.append(self.record('fixture-A'),'fixture-A');before=a.csv_path.read_bytes()
            with patch.object(s.os,'replace',side_effect=OSError('simulated interruption')):
                with self.assertRaises(OSError):a.append(self.record('fixture-B'),'fixture-B')
            self.assertEqual(a.csv_path.read_bytes(),before)
            a.db.close();b=s.Ledger(run,final);b.write_csv()
            self.assertEqual(len(b.rows()),2);b.db.close()
if __name__=='__main__':unittest.main()
