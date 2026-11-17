import json
import os
import subprocess
import sys
import unittest
from rankedit_rules import RankAggregator, RankingProfile

class TieBreakingTests(unittest.TestCase):

    def test_scr_uses_fixed_profile_based_set_order(self):
        for candidates in (('a', 'b', 'c'), ('c', 'b', 'a')):
            with self.subTest(candidates=candidates):
                profile = RankingProfile(candidates, {('a', 'b', 'c'): 1, ('b', 'a', 'c'): 1, ('c', 'b', 'a'): 1, ('b', 'c', 'a'): 1})
                expected = ['b', 'a', 'c'] if candidates[0] == 'a' else ['b', 'c', 'a']
                self.assertEqual(RankAggregator.compute_scr(profile), expected)

    def test_scr_ties_are_stable_across_processes(self):
        script = '\nimport json\nfrom rankedit_rules import RankAggregator, RankingProfile\nprofile = RankingProfile((\'b\', \'a\'), {(\'a\', \'b\'): 1, (\'b\', \'a\'): 1})\nprint(json.dumps(RankAggregator.compute_scr(profile)))\n'
        for seed in (1, 2, 3, 4):
            with self.subTest(seed=seed):
                result = subprocess.check_output([sys.executable, '-c', script], env={**os.environ, 'PYTHONHASHSEED': str(seed)}, text=True)
                self.assertEqual(json.loads(result), ['b', 'a'])

    def test_proportional_scoring_fallback_follows_profile_order(self):
        candidates = ('c', 'a', 'b')
        profile = RankingProfile(candidates, {('a', 'b', 'c'): 1})
        result = RankAggregator.compute_prop_seq_scoring(profile, score_mode='full', score_matrix=[[0], [0, 0], [0, 0, 0]])
        self.assertEqual(result, list(candidates))
if __name__ == '__main__':
    unittest.main()
