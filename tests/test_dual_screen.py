import datetime as dt
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dual_screen_v53 as engine

class ScreenTests(unittest.TestCase):
    def test_weights(self):
        self.assertEqual(sum(engine.WEIGHTS.values()), 100)
        self.assertEqual(engine.WEIGHTS['static_levels']+engine.WEIGHTS['volume'], 55)

    def test_missing_feeds_block(self):
        x=engine.evaluate('ETH', {'pairs': {}}, None, 1_000_000)
        self.assertEqual(x['tier'], 'blocked')

    def test_no_multitouch_cannot_pass(self):
        now=1_000_000
        pairs={}
        for symbol in ('ETHUSDT','BTCUSDT'):
            frames={}
            for tf,sec in engine.FRAMES.items():
                end=now-now%sec
                rows=[{'t':end-sec*(240-i),'o':100+i*.02,'h':101+i*.02,
                       'l':99+i*.02,'c':100+i*.02,'v':100} for i in range(240)]
                frames[tf]={'status':'available','candles':rows,
                            'source':'synthetic test', 'last_closed_at_utc':'synthetic'}
            pairs[symbol]={'frames':frames}
        x=engine.evaluate('ETH', {'pairs':pairs}, None, now)
        self.assertNotIn(x['tier'],('tier_1_priority_watch','tier_2_conditional_watch'))
        self.assertIsNone(x['risk_reward_validated_levels'])

if __name__=='__main__': unittest.main()
