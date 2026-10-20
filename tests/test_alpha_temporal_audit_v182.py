import unittest
from decimal import Decimal as D
from unittest.mock import patch
from engine.alpha_temporal_audit_v182 import evaluate,aggregate,band

def bar(i):
    return (i*14400,D('100'),D('105'),D('95'),D('101'),D('100'))

class TemporalAuditTests(unittest.TestCase):
    def test_bins(self):
        self.assertEqual([band(x) for x in (47,48,53,54,59)],
                         ['LOW','MEDIUM','MEDIUM','HIGH','HIGH'])
        with self.assertRaises(ValueError):band(101)

    def test_chronology_and_disabled_capabilities(self):
        bars=[bar(i) for i in range(270)]
        snap={'candidates':[{'type':'resistance','body_level':'104',
                'body_pivot_count':3,'confirmed_approach_rejections':2}]}
        with patch('engine.alpha_score_audit_v180.extract',return_value=snap):
            data=evaluate(bars)
        self.assertGreater(data['train']['decision_windows'],0)
        self.assertGreater(data['held_out']['decision_windows'],0)
        self.assertGreater(data['first_test_decision_epoch'],0)
        self.assertEqual(data['train']['by_band']['HIGH']['levels'],
                         data['train']['decision_windows'])
        self.assertFalse(data['signals_enabled'])
        self.assertFalse(data['trading_enabled'])
        self.assertFalse(data['trade_authorized'])
        self.assertFalse(data['release_6_0_0_approved'])
        self.assertEqual(data['signals'],[])

    def test_bad_fraction(self):
        with self.assertRaisesRegex(ValueError,'INVALID_TRAIN_FRACTION'):
            evaluate([],train_fraction=0.9)

    def test_decision_clustering(self):
        row={'decision_epoch':14400,'heuristic_score':54,
             'outcome':'CONFIRMED_REJECTION'}
        s=aggregate([row,row])
        self.assertEqual(s['by_band']['HIGH']['levels'],2)
        self.assertEqual(s['by_band']['HIGH']['distinct_decisions'],1)

if __name__=='__main__':unittest.main()
