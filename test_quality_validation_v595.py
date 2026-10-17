import unittest
from quality_validation_v595 import rr_sanity,replay_scenarios,volume_comparison,evaluate

class Tests(unittest.TestCase):
    def test_rr_normal(self):
        x=rr_sanity({'reference_price_usdt':100,'static_levels':{'support':95,'resistance':125}})
        self.assertEqual(x['status'],'SENSITIVITY_PASS')
        self.assertLess(x['net_rr'],x['gross_rr'])
    def test_rr_tiny_stop(self):
        x=rr_sanity({'reference_price_usdt':100,'static_levels':{'support':99.9,'resistance':105}})
        self.assertIn('stop_distance_below_0_5_percent_sensitivity',x['reasons'])
    def test_rr_missing(self):
        self.assertEqual(rr_sanity({})['status'],'BLOCK')
    def test_rr_cost(self):
        x=rr_sanity({'reference_price_usdt':100,'static_levels':{'support':95,'resistance':110}})
        self.assertIn('cost_adjusted_rr_below_3',x['reasons'])
    def test_queue_replay(self):
        self.assertEqual(replay_scenarios()['status'],'PASS_SIMULATION_ONLY')
    def test_missing_volume(self):
        x=volume_comparison({'pairs':{}})
        self.assertEqual(x['AAVE']['4h']['status'],'UNVERIFIED')
    def test_stale_fails_closed(self):
        x=evaluate({'generated_at_utc':'2020-01-01T00:00:00Z'}, {}, {}, 2000000000)
        self.assertEqual(x['status'],'BLOCK')
    def test_no_auto_approval(self):
        self.assertFalse(evaluate({'generated_at_utc':'2020-01-01T00:00:00Z'}, {}, {}, 2000000000)['release_6_0_0_approved'])

if __name__=='__main__':unittest.main()
