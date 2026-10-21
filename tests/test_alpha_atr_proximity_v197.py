import unittest
from decimal import Decimal
from unittest.mock import patch
from engine.alpha_atr_proximity_v197 import analyze,atr_at_decision,evaluate
def bars(n=18):
    return [(i*14400,Decimal(100),Decimal(102),Decimal(98),Decimal(100),Decimal(10)) for i in range(n)]
def e(t,p,o):return {'decision_epoch':t,'level':p,'outcome':o}
R='CONFIRMED_REJECTION';B='CONFIRMED_CLOSE_THROUGH'
class AtrProximityTests(unittest.TestCase):
    def test_predecision_atr(self):
        x=atr_at_decision(bars())
        self.assertEqual(x[14*14400],Decimal(4))
    def test_mixed_pair_in_atr_units(self):
        x=analyze(bars(),[e(14*14400,'100',R),e(14*14400,'101',B)])
        self.assertEqual(x['counts']['within_0.25_atr'],1)
        self.assertEqual(x['counts']['mixed_windows'],1)
    def test_missing_atr_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'MISSING_CAUSAL_ATR'):
            analyze(bars(),[e(1,'100',R),e(1,'101',B)])
    def test_safety(self):
        with patch('engine.alpha_atr_proximity_v197.replay',return_value={'events':[]}):
            x=evaluate(bars())
        self.assertEqual(x['signals'],[])
        self.assertIsNone(x['signal_generation']['generated_signals'])
        for k in ('signals_enabled','trading_enabled','trade_authorized','release_6_0_0_approved'):
            self.assertFalse(x[k])
if __name__=='__main__':unittest.main()
