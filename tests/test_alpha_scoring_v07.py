import unittest,copy
from engine.alpha_scoring_v07 import analyze,grade
def item(breakout=True):
    return {'status':'RESEARCH_VALIDATED','sma_close':{'status':'SMA_CLOSE_VALIDATED','identity':'100:5','sma_source':'CLOSE',
        'smas':{'SMA233':{'value':'10','slope':'UP','close_above':True,'close_below':False}}},
        'rsi14':{'status':'RSI_WILDER_CLOSE_VALIDATED','identity':'100:5','source':'CLOSE','value':'58'},
        'native_volume_price_action':{'status':'NATIVE_VOLUME_PRICE_ACTION_VALIDATED','identity':'100:5','volume_source':'OKX_NATIVE_BASE_VOLUME',
        'rvol20':'2.2','closed_above_prior_resistance_20':breakout,'closed_below_prior_support_20':False}}
class Tests(unittest.TestCase):
    def test_high_score_never_authorizes(self):
        b={'5m':{'SOL':item()},'15m':{'SOL':item()}}
        v=grade('5m','SOL',b)
        self.assertEqual(v['research_score'],100);self.assertEqual(v['research_tier'],'GREEN');self.assertFalse(v['signal_authorized'])
    def test_no_breakout(self):
        b={'5m':{'SOL':item(False)},'15m':{'SOL':item()}}
        self.assertEqual(grade('5m','SOL',b)['side'],'NONE')
    def test_fail_closed_bad_identity(self):
        x=item();x['rsi14']['identity']='WRONG'
        self.assertEqual(grade('5m','SOL',{'5m':{'SOL':x}})['status'],'BLOCKED')
    def test_invalid_volume(self):
        x=item();x['native_volume_price_action']['rvol20']='NaN'
        self.assertEqual(grade('5m','SOL',{'5m':{'SOL':x}})['status'],'BLOCKED')
    def test_unsafe_report_rejected(self):
        with self.assertRaises(ValueError):analyze({'version':'alpha-0.6-rsi-volume','research_only':True,'signals_enabled':True,'trading_enabled':False})
if __name__=='__main__':unittest.main()
