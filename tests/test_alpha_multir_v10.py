import unittest
from decimal import Decimal as D
from engine.alpha_multir_v10 import simulate,scenario_result,pivot_lows
class TestMultiR(unittest.TestCase):
 def fixture(self):
  rows={};now=399*300
  for i in range(399):
   close=D('100')+D(i)/D('1000');volume=D('10')
   rows[i*300]={'open':close,'high':close+D('.2'),'low':close-D('.2'),'close':close,'base_volume':volume}
  return rows,now
 def test_no_future_missing(self):
  rows,now=self.fixture();del rows[50*300]
  self.assertEqual(simulate(rows,'5m',now)['status'],'BLOCKED')
 def test_no_events_flat(self):
  rows,now=self.fixture()
  x=simulate(rows,'5m',now)
  self.assertEqual(x['candidate_events'],0)
  self.assertIsNone(x['statistics']['2.5']['mean_net_r_all'])
 def test_pivots_causal(self):
  rows,now=self.fixture();cs=list(rows.values());cs[20]['low']=D('80');
  self.assertFalse(any(i==20 for i,_ in pivot_lows(cs,22)))
  self.assertTrue(any(i==20 for i,_ in pivot_lows(cs,23)))
 def test_targets_same_entry(self):
  c=[{'open':D('101'),'high':D('130'),'low':D('101'),'close':D('120')}]
  a=scenario_result(c,-1,D('101'),D('100'),D('2'),1)
  b=scenario_result(c,-1,D('101'),D('100'),D('3'),1)
  self.assertEqual(a['exit_reason'],'TARGET');self.assertEqual(b['exit_reason'],'TARGET')
 def test_only_research(self):
  rows,now=self.fixture()
  self.assertFalse(simulate(rows,'5m',now)['signal_authorized'])
if __name__=='__main__':unittest.main()
