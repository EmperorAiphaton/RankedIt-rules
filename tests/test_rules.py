import unittest
from rankedit_rules import RankAggregator, RankingProfile
SAMPLE_PROFILE = RankingProfile(candidates=('A', 'B', 'C', 'D'), rankings={('A', 'B', 'C', 'D'): 0.4, ('B', 'C', 'D', 'A'): 0.35, ('C', 'D', 'A', 'B'): 0.25})

class StandardRuleTests(unittest.TestCase):

    def test_kemeny_ilp_rules(self):
        result_kemeny = RankAggregator.compute_kemeny(SAMPLE_PROFILE)
        result_squared = RankAggregator.compute_squared_kemeny(SAMPLE_PROFILE)
        self.assertEqual(set(result_kemeny), set(('A', 'B', 'C', 'D')))
        self.assertEqual(set(result_squared), set(('A', 'B', 'C', 'D')))

    def test_reverse_sequential_rules(self):
        result_rev_stv = RankAggregator.compute_reverse_sequential_stv(SAMPLE_PROFILE)
        result_rev_ear = RankAggregator.compute_reverse_sequential_ear(SAMPLE_PROFILE)
        self.assertEqual(set(result_rev_stv), set(('A', 'B', 'C', 'D')))
        self.assertEqual(set(result_rev_ear), set(('A', 'B', 'C', 'D')))

    def test_squared_kemeny_max_distance_counterexample(self):
        profile = RankingProfile(candidates=('a', 'b', 'c'), rankings={tuple(r): w for r, w in [('cba', 1), ('abc', 12), ('acb', 17), ('bca', 20), ('bac', 12), ('cab', 3)]})
        self.assertEqual(RankAggregator.compute_squared_kemeny(profile), ['a', 'b', 'c'])

    def test_squared_kemeny_two_candidates(self):
        for ranking in (('a', 'b'), ('b', 'a')):
            with self.subTest(ranking=ranking):
                profile = RankingProfile(candidates=('a', 'b'), rankings={ranking: 1})
                self.assertEqual(RankAggregator.compute_squared_kemeny(profile), list(ranking))

    def test_pse_rule_matches_paper_example(self):
        profile = RankingProfile(candidates=('x1', 'x2', 'x3', 'x4', 'x5'), rankings={('x1', 'x2', 'x3', 'x4', 'x5'): 0.5, ('x5', 'x1', 'x2', 'x3', 'x4'): 0.25, ('x5', 'x4', 'x3', 'x2', 'x1'): 0.25})
        result = RankAggregator.compute_pse(profile, weights=(5, 5, 2, 1, 0))
        self.assertEqual(result, ['x2', 'x1', 'x5', 'x4', 'x3'])

    def test_factorial_pse(self):
        profile = RankingProfile(candidates=('x1', 'x2', 'x3', 'x4', 'x5', 'x6'), rankings={('x1', 'x2', 'x3', 'x4', 'x5', 'x6'): 2, ('x6', 'x5', 'x4', 'x3', 'x2', 'x1'): 1})
        result = RankAggregator.compute_factorial_pse(profile)
        self.assertEqual(['x2', 'x6', 'x5', 'x4', 'x3', 'x1'], result)
if __name__ == '__main__':
    unittest.main(verbosity=2)
