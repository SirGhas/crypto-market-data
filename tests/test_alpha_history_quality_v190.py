import unittest
from unittest.mock import patch
from engine.alpha_history_quality_v190 import audit,evaluate
B=(14400,10,12,9,11,100)
class QualityTests(unittest.TestCase):
    def test_valid(self):
        q=audit([B,(28800,11,13,10,12,0)])
        self.assertTrue(q['contiguous'])
        self.assertEqual(q['bar_count'],2)
        self.assertEqual(q['sha256_normalized_history'],audit([B,(28800,11,13,10,12,0)])['sha256_normalized_history'])
    def test_empty(self):
        with self.assertRaisesRegex(ValueError,'EMPTY_HISTORY'):audit([])
    def test_gaps_and_duplicates(self):
        for data in ([B,(43200,11,13,10,12,0)],[B,B]):
            with self.assertRaisesRegex(ValueError,'NON_CONTIGUOUS_HISTORY'):audit(data)
    def test_bad_prices(self):
        for b in ((14400,10,9,8,11,10),(14400,10,12,9,11,-1),(14400,10,float('nan'),9,11,1)):
            with self.assertRaises(ValueError):audit([b])
    def test_safety(self):
        with patch('engine.alpha_history_quality_v190.tiers',return_value={'periods':[]}):
            x=evaluate([B])
        self.assertTrue(x['research_only'])
        self.assertEqual(x['signals'],[])
        for k in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(x[k])
if __name__=='__main__':unittest.main()
