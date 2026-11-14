import unittest
from src.evaluation import evaluate_query, summarize


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.q = dict(id='q', split='dev', question='Q', expected_answer='A',
                      gold_source_id='doc', gold_page=2, evidence_quote='Đủ bằng chứng', filter=None)

    def hit(self, text='Đủ bằng chứng', page=2, doc='doc'):
        return dict(text=text, page=page, document_id=doc)

    def test_requires_source_page_and_complete_evidence(self):
        for h in [self.hit(page=3), self.hit(doc='other'), self.hit(text='Đủ bằng')]:
            self.assertFalse(evaluate_query(self.q,[h])['hit3'])

    def test_rank_whitespace_and_top_three(self):
        r=evaluate_query(self.q,[self.hit('wrong'),self.hit('Đủ\n bằng  chứng')])
        self.assertFalse(r['hit1']);self.assertTrue(r['hit3'])
        self.assertFalse(evaluate_query(self.q,[self.hit('wrong')]*3+[self.hit()])['hit3'])

    def test_split_evidence_is_not_a_hit(self):
        r=evaluate_query(self.q,[self.hit('Đủ bằng'),self.hit('chứng')])
        self.assertFalse(r['hit3'])

    def test_alternative_gold_and_empty_results(self):
        self.q['alternative_gold']=[dict(gold_source_id='other',gold_page=8,evidence_quote='Cách khác')]
        self.assertTrue(evaluate_query(self.q,[self.hit('Cách khác',8,'other')])['hit1'])
        self.assertFalse(evaluate_query(self.q,[])['hit1'])
        self.q['evidence_quote']=' '
        with self.assertRaises(ValueError):evaluate_query(self.q,[])

    def test_summary_denominator_and_duplicate_rejection(self):
        a={**evaluate_query(self.q,[self.hit()]),'strategy':'A'}
        b={**evaluate_query({**self.q,'id':'q2'},[]),'strategy':'A'}
        r=summarize([a,b])[0]
        self.assertEqual((r['hit1_numerator'],r['question_count'],r['hit3']),(1,2,0.5))
        with self.assertRaises(ValueError):summarize([a,a])


if __name__ == '__main__':unittest.main()
