import unittest
from decimal import Decimal as D
from engine.alpha_feature_separation_v211 import features,evaluate

class FeatureTests(unittest.TestCase):
    def test_touch_episodes_and_missing_response(self):
        bars=[(i*14400,D(10),D(11),D(9),D(10),D(1)) for i in range(21)]
        z={'body_level':'10','type':'support','events':[],'body_pivot_count':1,'confirmed_approach_rejections':0}
        f=features(z,bars,D('.1'))
        self.assertEqual(f['touch_episodes'],1)
        self.assertIsNone(f['median_response_atr'])
        self.assertEqual(D(f['aligned_return_20']),0)
        self.assertEqual(f['legacy_score'],45)
    def test_direction_and_response(self):
        bars=[(i*14400,D(10+i),D(11+i),D(9+i),D(10+i),D(1)) for i in range(21)]
        z={'body_level':'40','type':'resistance','events':[{'response_atr':'1'},{'response_atr':'3'}],'body_pivot_count':2,'confirmed_approach_rejections':2}
        f=features(z,bars,D('.1'))
        self.assertEqual(D(f['median_response_atr']),2)
        self.assertLess(D(f['aligned_return_20']),0)
        self.assertEqual(f['touch_episodes'],0)
    def test_short_history_rejected(self):
        with self.assertRaisesRegex(ValueError,'INVALID_HISTORY'):
            evaluate([])
