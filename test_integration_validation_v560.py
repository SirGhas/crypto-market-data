import copy
import unittest
from test_shadow_relative_screen_v553 import ShadowTests, NOW
from integration_validation_v560 import inspect

class IntegrationTests(unittest.TestCase):
    def inputs(self):return ShadowTests().inputs()
    def test_full_pass_and_immutability(self):
        args=self.inputs();before=copy.deepcopy(args)
        r=inspect(*args,NOW)
        self.assertEqual(r['summary']['PASS'],4)
        self.assertEqual(r['summary']['publication_gates_modified'],0)
        self.assertEqual(args,before)
    def test_block_if_derived_invalid(self):
        args=self.inputs();args[0]['pairs']['AAVEBTC']['frames']['4h']['status']='DERIVED_BLOCKED'
        self.assertEqual(inspect(*args,NOW)['coins']['AAVE']['status'],'BLOCK')
    def test_block_if_original_guard_disagrees(self):
        args=self.inputs();args[3]['coins']['AAVE']['score']=99
        self.assertEqual(inspect(*args,NOW)['coins']['AAVE']['status'],'BLOCK')
    def test_no_threshold_grants_publication(self):
        args=self.inputs();r=inspect(*args,NOW)
        self.assertEqual(r['coins']['AAVE']['original_publication_gate'],'BLOCK')
        self.assertTrue(r['coins']['AAVE']['threshold_crossings']['70'])
    def test_invalid_weight_blocks(self):
        args=self.inputs();args[1]['evaluations'][0]['weights']['relative_btc']=10
        self.assertEqual(inspect(*args,NOW)['coins']['AAVE']['status'],'BLOCK')
    def test_stale_guard_fails_closed(self):
        args=self.inputs();args[3]['generated_at_utc']='2020-01-01T00:00:00+00:00'
        with self.assertRaises(ValueError):inspect(*args,NOW)
if __name__=='__main__':unittest.main()
