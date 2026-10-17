import unittest
from derived_relative_strength_v551 import calculate, FRAMES

NOW = (1800000000 // 14400) * 14400 + 60


def sample():
    pairs = {}
    for coin, price in [('BTC', 80000), ('AAVE', 100), ('AVAX', 20), ('LINK', 10), ('SUI', 2)]:
        frames = {}
        for tf, period in FRAMES.items():
            end = (NOW // period) * period - period
            candles = [{'t': end - period * (232 - i), 'c': price + i * price / 10000, 'confirmed': True} for i in range(233)]
            frames[tf] = {'status': 'available', 'source': 'OKX Spot', 'candles': candles}
        pairs[coin + 'USDT'] = {'frames': frames}
    return {'pairs': pairs}


class RelativeStrengthTests(unittest.TestCase):
    def test_ready_is_informational_not_publishable(self):
        result = calculate(sample(), NOW)
        self.assertEqual(result['summary']['DERIVED_READY'], 16)
        self.assertEqual(result['summary']['direct_feeds_upgraded'], 0)
        self.assertFalse(result['publication_eligible'])
        frame = result['pairs']['AAVEBTC']['frames']['5m']
        self.assertAlmostEqual(frame['last_ratio'], 100 / 80000)
        self.assertNotIn('v', frame['series'][-1])

    def test_missing_btc_blocks(self):
        data = sample()
        del data['pairs']['BTCUSDT']
        self.assertEqual(calculate(data, NOW)['summary']['DERIVED_BLOCKED'], 16)

    def test_misaligned_blocks(self):
        data = sample()
        data['pairs']['AAVEUSDT']['frames']['5m']['candles'][-1]['t'] -= 300
        self.assertEqual(calculate(data, NOW)['pairs']['AAVEBTC']['frames']['5m']['status'], 'DERIVED_BLOCKED')

    def test_stale_blocks(self):
        data = sample()
        data['pairs']['BTCUSDT']['frames']['5m']['candles'] = [dict(c, t=c['t'] - 3600) for c in data['pairs']['BTCUSDT']['frames']['5m']['candles']]
        self.assertEqual(calculate(data, NOW)['pairs']['LINKBTC']['frames']['5m']['status'], 'DERIVED_BLOCKED')

    def test_wrong_source_blocks(self):
        data = sample()
        data['pairs']['BTCUSDT']['frames']['1h']['source'] = 'unknown'
        self.assertEqual(calculate(data, NOW)['pairs']['SUIBTC']['frames']['1h']['status'], 'DERIVED_BLOCKED')

    def test_zero_price_blocks(self):
        data = sample()
        data['pairs']['AVAXUSDT']['frames']['4h']['candles'][-1]['c'] = 0
        self.assertEqual(calculate(data, NOW)['pairs']['AVAXBTC']['frames']['4h']['status'], 'DERIVED_BLOCKED')


if __name__ == '__main__':
    unittest.main()
