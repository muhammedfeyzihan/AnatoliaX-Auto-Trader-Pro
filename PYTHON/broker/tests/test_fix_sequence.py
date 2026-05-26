"""
tests/test_fix_sequence.py — FIX sequence number testleri
"""
import unittest
from PYTHON.broker.protocols.fix_sequence import SequenceManager


class TestSequenceManager(unittest.TestCase):
    def test_increment(self):
        sm = SequenceManager()
        self.assertEqual(sm.next(), 1)
        self.assertEqual(sm.next(), 2)

    def test_reset(self):
        sm = SequenceManager()
        sm.next()
        sm.reset()
        self.assertEqual(sm.next(), 1)

    def test_gap(self):
        sm = SequenceManager()
        sm._seq = 5
        self.assertTrue(sm.gap_detected(3))
        self.assertFalse(sm.gap_detected(6))


if __name__ == "__main__":
    unittest.main()
