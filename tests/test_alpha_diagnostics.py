import unittest
from decimal import Decimal
from engine.alpha_diagnostics import diagnose
class DiagnosticTests(unittest.TestCase):
 def rows(self, current_close='100',current_volume='30'):
  out={}
  for i in range(61):
   t=(100-i)*300
   out[t]={'close':Decimal(current_close if i==0 else '99'),'open':Decimal('99'), 'high':Decimal('110'), 'low':Decimal('90'),'base_volume':Decimal(current_volume if i==0 else '10')}
  return out
 def test_diagnostics(self):
  x=diagnose(self.rows(),'5m',101*300,300)
  self.assertEqual(x['status'],'RESEARCH_DIAGNOSTICS_ONLY')
  self.assertEqual(x['relative_volume_20'],'3')
  self.assertFalse(x['signal_authorized'])
  self.assertIsNone(x['synthetic_volume'])
 def test_missing_history_blocks(self):
  rows=self.rows();rows.pop(70*300)
  self.assertEqual(diagnose(rows,'5m',101*300,300)['status'],'BLOCKED')
 def test_breakout(self):
  x=diagnose(self.rows('111'),'5m',101*300,300)
  self.assertTrue(x['breakout_close_above_resistance'])
  self.assertIsNone(x['illustrative_long_rr_to_prior_high_60'])
 def test_empty_base_volume(self):
  rows=self.rows()
  for i in range(1,61):rows[(100-i)*300]['base_volume']=Decimal(0)
  self.assertIsNone(diagnose(rows,'5m',101*300,300)['relative_volume_20'])
if __name__=='__main__':unittest.main()
