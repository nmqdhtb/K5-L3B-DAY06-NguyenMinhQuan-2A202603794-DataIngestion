import unittest
from src.chunking import fixed_size, by_paragraph
from src.models import DocumentPage


class ChunkingTests(unittest.TestCase):
    def page(self, text):
        return DocumentPage('doc', 'source.pdf', 2, text, {'verse_start': 10, 'verse_end': 20})

    def test_fixed_coverage_overlap_and_tail(self):
        page = self.page('abcdefghijk')
        chunks = fixed_size(page, 5, 2)
        self.assertEqual([c.text for c in chunks], ['abcde', 'defgh', 'ghijk'])
        self.assertEqual(chunks[-1].metadata['char_end'], len(page.text))

    def test_paragraphs_preserve_source_and_whole_lines(self):
        page = self.page('a\nb\n\nc\nd\n\ne\nf')
        chunks = by_paragraph(page, 6)
        self.assertEqual(''.join(c.text for c in chunks), page.text)
        self.assertTrue(all(len(c.text) <= 6 for c in chunks))
        self.assertTrue(all(c.text.endswith('\n') for c in chunks[:-1]))

    def test_oversized_line_and_unicode(self):
        page = self.page('người' * 30 + '\n\nThơ\nViệt')
        chunks = by_paragraph(page, 12)
        self.assertEqual(''.join(c.text for c in chunks), page.text)
        self.assertTrue(all(len(c.text) <= 12 for c in chunks))

    def test_empty_and_invalid_parameters(self):
        for chunker in (lambda p: fixed_size(p, 5, 1), lambda p: by_paragraph(p, 5)):
            self.assertEqual(chunker(self.page(' \n')), [])
        for size, overlap in [(0, 0), (5, 5), (5, -1)]:
            with self.assertRaises(ValueError):
                fixed_size(self.page('abc'), size, overlap)
        with self.assertRaises(ValueError):
            by_paragraph(self.page('abc'), 0)

    def test_ids_and_metadata_are_stable_and_isolated(self):
        page = self.page('abcdefghij')
        first = fixed_size(page, 5, 1)
        self.assertEqual(first, fixed_size(page, 5, 1))
        changed = self.page('abcdefghik')
        self.assertNotEqual(first[0].chunk_id, fixed_size(changed, 5, 1)[0].chunk_id)
        first[0].metadata['verse_start'] = -1
        self.assertEqual(page.metadata['verse_start'], 10)
        self.assertEqual(first[1].metadata['verse_start'], 10)


if __name__ == '__main__':
    unittest.main()
