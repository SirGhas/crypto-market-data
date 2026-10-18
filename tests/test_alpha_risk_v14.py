import json, unittest
from engine.alpha_risk_v14 import overlay,compute_risk,merge_related_alerts

class TestAlphaRisk(unittest.TestCase):
    def test_fail_closed_missing_data(self):
        r=compute_risk('X',{})
        self.assertFalse(r['trade_authorized']);self.assertIsNone(r['hypothetical_stop'])
    def test_structural_levels_not_invent_stop(self):
        d={'timeframes':{'4h':{'status':'VALIDATED','identity':'1:240','close':'100','static_levels':{'20':{'support':'94','resistance':'109'},'60':{'support':'91','resistance':'110'}}},'1D':{'status':'VALIDATED','identity':'1:1440','static_levels':{'20':{'support':'85','resistance':'125'}}}}}
        r=compute_risk('X',d)
        self.assertEqual(r['nearest_4h_support'],'94');self.assertEqual(r['distance_to_4h_support_pct'],'6')
        self.assertIsNone(r['hypothetical_stop']);self.assertFalse(r['atr14_4h_verified'])
        self.assertEqual(r['nearest_4h_overhead_resistance'],'109')
    def test_reject_invalid_price(self):
        r=compute_risk('X',{'timeframes':{'4h':{'status':'VALIDATED','close':'-1'},'1D':{'status':'VALIDATED'}}})
        self.assertIn('INVALID_REFERENCE_CLOSE',r['blocking_reasons'])
    def test_consolidation(self):
        events=[{'asset':'LTC','type':'DOWNSIDE_SUPPORT_BREAK','direction':'RISK_DOWN','timeframe':t,'event_id':t} for t in ('15m','30m')]
        bundles=merge_related_alerts(events)
        self.assertEqual(len(bundles),1);self.assertEqual(bundles[0]['underlying_event_count'],2)
        self.assertEqual(bundles[0]['timeframes'],['15m','30m'])
    def test_no_cross_asset_merge(self):
        events=[{'asset':a,'type':'DOWNSIDE_SUPPORT_BREAK','direction':'RISK_DOWN','timeframe':'15m','event_id':a} for a in ('LTC','ETH')]
        self.assertEqual(len(merge_related_alerts(events)),2)
    def test_version_gate(self):
        with self.assertRaises(ValueError):overlay({'version':'wrong'})
    def test_flags(self):
        r=overlay({'version':'alpha-1.3-directional-research-alerts','assets':{'X':{}},'research_alerts':[],'signals':[1],'trading_enabled':True})
        self.assertFalse(r['trading_enabled']);self.assertEqual(r['signals'],[]);self.assertEqual(r['totals']['risk_records'],1)
if __name__=='__main__':unittest.main()
