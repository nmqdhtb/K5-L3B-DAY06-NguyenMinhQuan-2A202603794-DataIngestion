"""Input validation only: small synthetic vectors here are NOT ingestion data."""
import unittest
from src.store import PgVectorStore
from src.models import Chunk


class StoreValidationTests(unittest.TestCase):
    def setUp(self):
        self.store = PgVectorStore('unused', 2, {'unit_test': True})

    def test_reject_invalid_vectors_without_connecting(self):
        for vector in ([1], [0, 0], [float('nan'), 1], [float('inf'), 1]):
            with self.assertRaises(ValueError):
                self.store.search('A', vector)

    def test_reject_unknown_filters_without_connecting(self):
        for filters in ({'page': {'gte': 1}}, {'verse_start': {'sql': 'DROP TABLE chunks'}},
                        {'verse_end': {'gte': '1 OR 1=1'}}):
            with self.assertRaises(ValueError):
                self.store.search('C', [1, 0], filters=filters)

    def test_reject_duplicate_ids_and_mismatched_counts(self):
        c = Chunk('same', 'doc', 'source', 1, 'test')
        with self.assertRaises(ValueError):
            self.store.upsert('A', [c], [])
        with self.assertRaises(ValueError):
            self.store.upsert('A', [c, c], [[1,0], [0,1]])


if __name__ == '__main__':
    unittest.main()
