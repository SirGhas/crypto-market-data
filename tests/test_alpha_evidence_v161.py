import unittest
from decimal import Decimal as D
from engine.alpha_evidence_v161 import closed_volume_candles,reaction_evidence,book_sample,check_book_series,evidence_overlay

class TestExperimentalEvidence(unittest.TestCase):
    def history(self):
        r=[]
        for i in range(60):
            lo=D('95') if i%10==0 else D('99')
            r.append((i*14400,D(100),D(102),lo,D(100),D(120 if i%10==0 else 20)))
        return r
    def test_reaction_nonoverlap(self):
        z={'side':'support','low':'94.9','high':'95.1'}
        x=reaction_evidence(z,self.history(),D('2'),D('.25'))
        self.assertGreaterEqual(x['independent_confirmed_observations'],2)
        self.assertTrue(all(float(a['volume_rvol20'])>1 for a in x['events']))
    def test_volume_hist_identity(self):
        rows=[]
        for i in range(50):
            rows.append([str(i*14400*1000),'100','102','98','100','10','1000','1000','1'])
        def transport(url):return {'code':'0','data':list(reversed(rows))}
        h=closed_volume_candles('ETH','4H',49*14400,'100',transport)
        self.assertEqual(len(h),50)
        self.assertEqual(h[-1][5],D(10))
        with self.assertRaisesRegex(ValueError,'MISMATCH'):
            closed_volume_candles('ETH','4H',48*14400,'101',transport)
    def bookdata(self, ts):
        return {'code':'0','data':[{'ts':str(ts),'bids':[['100','3'],['99.5','2']],
                                        'asks':[['100.1','2'],['100.6','2']]}]}
    def test_orderbook_samples(self):
        ss=[book_sample('ETH',lambda u,t=t:self.bookdata(t),now_ms=t+50) for t in (100000,103000,106000)]
        self.assertEqual(check_book_series(ss)['sample_count'],3)
        with self.assertRaisesRegex(ValueError,'TOO_CLOSE'):
            check_book_series([ss[0],ss[0],ss[2]])
    def test_stale_book_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'STALE'):
            book_sample('ETH',lambda u:self.bookdata(100000),now_ms=300001)
    def test_invalid_book_crossed(self):
        raw=self.bookdata(100000);raw['data'][0]['asks'][0][0]='99'
        with self.assertRaisesRegex(ValueError,'CROSSED'):
            book_sample('ETH',lambda u:raw,now_ms=100050)
    def test_overlay_always_safe(self):
        report={'version':'alpha-1.6-multitimeframe-level-quality-research', 'assets':{'ETH':{'level_quality_v16':{'status':'BLOCKED'}}}}
        out=evidence_overlay(report,{}, {})
        self.assertEqual(out['signals'],[])
        self.assertFalse(out['trading_enabled'])
        self.assertFalse(out['assets']['ETH']['evidence_v161']['trade_authorized'])
    def test_wrong_version(self):
        with self.assertRaisesRegex(ValueError,'EXPECTED_V16'):
            evidence_overlay({'version':'v1','assets':{}},{},{})

if __name__=='__main__':unittest.main()
