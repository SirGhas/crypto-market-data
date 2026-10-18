import unittest
from decimal import Decimal
from engine.alpha_sma_v04 import collect_history,sma_audit
from engine.alpha_core import InvalidMarketData

class CloseOnlySMATests(unittest.TestCase):
    def test_233_close_and_slope(self):
        now=300*400
        exp=(now//300-1)*300
        rows={exp-i*300:{'close':Decimal(500-i)} for i in range(234)}
        r=sma_audit(rows,'5m',now)
        self.assertEqual(r['status'],'SMA_CLOSE_VALIDATED')
        self.assertEqual(r['smas']['SMA233']['slope'],'UP')
        self.assertEqual(Decimal(r['smas']['SMA233']['value']),Decimal(384))
    def test_missing_one_candle_blocks(self):
        now=300*400;exp=(now//300-1)*300
        rows={exp-i*300:{'close':Decimal(500)} for i in range(234)}
        del rows[exp-50*300]
        self.assertEqual(sma_audit(rows,'5m',now)['status'],'BLOCKED')
    def test_233_not_enough_for_slope(self):
        now=300*400;exp=(now//300-1)*300
        rows={exp-i*300:{'close':Decimal(500)} for i in range(233)}
        self.assertEqual(sma_audit(rows,'5m',now)['status'],'BLOCKED')
    def test_paginated_collection(self):
        now=300*400;exp=(now//300-1)*300
        calls=[]
        def fetch(inst,bar,after=None):
            calls.append(after)
            newest=exp if after is None else int(after)//1000-300
            d=[]
            for i in range(100):
                ts=newest-i*300
                d.append([str(ts*1000),'100','500','99',str(101+i),'4','400','400','1'])
            return {'code':'0','data':d}
        rows=collect_history('ETH-USDT','5m',now,fetch)
        self.assertGreaterEqual(len(rows),234)
        self.assertEqual(len(calls),3)
    def test_pagination_no_progress_rejected(self):
        now=300*400;exp=(now//300-1)*300
        def fetch(inst,bar,after=None):
            return {'code':'0','data':[[str((exp-i*300)*1000),'100','101','99','100','4','400','400','1'] for i in range(100)]}
        with self.assertRaisesRegex(InvalidMarketData,'PAGINATION_NOT_ADVANCING'):
            collect_history('ETH-USDT','5m',now,fetch)

if __name__=='__main__':unittest.main()
