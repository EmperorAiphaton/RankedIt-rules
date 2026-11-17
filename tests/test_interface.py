import copy
import itertools
import math
import unittest
from unittest.mock import Mock, patch

from rankedit_rules import RankAggregator, RankingProfile, PartialResult


STANDARD_METHODS = (
    'plurality', 'borda', 'veto',
    'seq_winner_plurality', 'seq_winner_borda', 'seq_winner_veto',
    'seq_loser_plurality', 'seq_loser_borda', 'seq_loser_veto',
    'prop_seq_plurality', 'prop_seq_borda', 'prop_seq_veto',
    'reverse_sequential_stv', 'reverse_sequential_ear', 'scr',
    'standard_PSE', 'factorial_pse', 'kemeny', 'squared_kemeny',
)


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.profile = RankingProfile(['a', 'b', 'c'], {('a', 'b', 'c'): 3, ('c', 'b', 'a'): 2})

    def test_all_standard_methods_return_candidate_ids(self):
        self.assertEqual(len(STANDARD_METHODS), 19)
        for method in STANDARD_METHODS:
            with self.subTest(method=method):
                self.assertCountEqual(getattr(RankAggregator, 'compute_' + method)(self.profile), ['a', 'b', 'c'])

    def test_repeated_calls_do_not_mutate_profile_or_arguments(self):
        candidates = ['a', 'b', 'c']
        rankings = [(['a', 'b', 'c'], 3), (['c', 'b', 'a'], 2)]
        before = copy.deepcopy((candidates, rankings))
        profile = RankingProfile(candidates, rankings)
        stored = copy.deepcopy((profile.candidates, profile.rankings))
        expected = RankAggregator.compute_borda(profile)
        for method in STANDARD_METHODS:
            getattr(RankAggregator, 'compute_' + method)(profile)
        self.assertEqual((profile.candidates, profile.rankings), stored)
        self.assertEqual((candidates, rankings), before)
        candidates.reverse()
        rankings[0][0].reverse()
        self.assertEqual(RankAggregator.compute_borda(profile), expected)

    def test_static_methods_accept_independent_profiles(self):
        first = RankingProfile(['a', 'b'], {('a', 'b'): 1})
        second = RankingProfile(['a', 'b'], {('b', 'a'): 1})
        self.assertEqual(RankAggregator.compute_borda(first), ['a', 'b'])
        self.assertEqual(RankAggregator.compute_borda(second), ['b', 'a'])
        self.assertEqual(RankAggregator.compute_borda(first), ['a', 'b'])

    def test_duplicate_weights_and_zero_weights(self):
        profile = RankingProfile(['a', 'b'], [(['a', 'b'], 3), (['a', 'b'], 3), (['b', 'a'], 4), (['b', 'a'], 0)])
        self.assertEqual(profile.rankings, {('a', 'b'): 6, ('b', 'a'): 4})
        self.assertEqual(RankAggregator.compute_plurality(profile), ['a', 'b'])

    def test_no_website_minimum_weight(self):
        profile = RankingProfile(['a', 'b'], {('a', 'b'): .002, ('b', 'a'): .001})
        self.assertEqual(RankAggregator.compute_plurality(profile), ['a', 'b'])

    def test_arbitrary_string_ids_are_safe_for_solver_variables(self):
        candidates = ['A-B', 'A+B', 'Candidate with spaces', '東京']
        profile = RankingProfile(candidates, [(candidates, 1)])
        for method in ('compute_borda', 'compute_kemeny', 'compute_squared_kemeny'):
            with self.subTest(method=method):
                self.assertEqual(getattr(RankAggregator, method)(profile), candidates)
        self.assertEqual(profile.candidates, tuple(candidates))

    def test_invalid_profiles(self):
        profiles = [
            ([], []), (['a', 'a'], [(['a', 'a'], 1)]),
            (['a', 'b'], [(['a', 'a'], 1)]), (['a', 'b'], [(['a'], 1)]),
            (['a', 'b'], [(['a', 'b'], 0)]), (['a', 'b'], [(['a', 'b'], -1)]),
            (['a', 'b'], [(['a', 'b'], math.inf)]), (['a', 'b'], [(['a', 'b'], math.nan)]),
        ]
        for candidates, rankings in profiles:
            with self.subTest(candidates=candidates, rankings=rankings):
                with self.assertRaises(ValueError):
                    RankingProfile(candidates, rankings)
        with self.assertRaises(TypeError):
            RankAggregator.compute_borda({'rankings': []})
        self.profile.rankings[('a', 'b', 'c')] = -1
        with self.assertRaises(ValueError):
            RankAggregator.compute_borda(self.profile)

    def test_custom_scoring_matches_named_variants(self):
        for custom, prefix in [('scoring', ''), ('seq_winner_scoring', 'seq_winner_'), ('seq_loser_scoring', 'seq_loser_'), ('prop_seq_scoring', 'prop_seq_')]:
            for family, matrix in [('plurality', [[1], [1, 0], [1, 0, 0]]), ('borda', [[0], [1, 0], [2, 1, 0]]), ('veto', [[0], [1, 0], [1, 1, 0]])]:
                with self.subTest(custom=custom, family=family):
                    self.assertEqual(getattr(RankAggregator, 'compute_' + custom)(self.profile, score_mode='full', score_matrix=matrix), getattr(RankAggregator, 'compute_' + prefix + family)(self.profile))

    def test_standard_pse_uses_all_ones(self):
        profiles = [self.profile, RankingProfile(['a'], {('a',): 1}),
                    RankingProfile(['c', 'b', 'a'], {('a', 'b', 'c'): 1, ('c', 'b', 'a'): 1})]
        for profile in profiles:
            with self.subTest(candidates=profile.candidates):
                self.assertEqual(
                    RankAggregator.compute_standard_PSE(profile),
                    RankAggregator.compute_pse(profile, weights=[1] * len(profile.candidates)),
                )
                self.assertEqual(RankAggregator.compute_standard_PSE(profile), RankAggregator.compute_pse(profile))

    def test_invalid_custom_parameters(self):
        cases = [
            ('compute_pse', {'weights': [1, 0]}), ('compute_pse', {'weights': [1, -1, 0]}),
            ('compute_pse', {'weights': [1, math.inf, 0]}),
            ('compute_kemeny_power', {'p': math.nan}), ('compute_kemeny_power', {'p': 0}),
            ('compute_scoring', {'scores': [2, 1]}),
            ('compute_scoring', {'scores': [2, 1, 0], 'score_mode': 'misspelled'}),
            ('compute_prop_seq_scoring', {'scores': [2, 1, 0], 'round_weights': []}),
        ]
        for method, parameters in cases:
            with self.subTest(method=method, parameters=parameters):
                with self.assertRaises(ValueError):
                    getattr(RankAggregator, method)(self.profile, **parameters)
        with self.assertRaises(TypeError):
            RankAggregator.compute_borda(self.profile, scores=[2, 1, 0])
        with self.assertRaises(TypeError):
            RankAggregator.compute_scoring(self.profile, typo=1)

    def test_powered_solver_matches_exhaustive_objective(self):
        rankings = {('a', 'c', 'b'): 4, ('b', 'a', 'c'): 3, ('c', 'b', 'a'): 2}
        profile = RankingProfile(['a', 'b', 'c'], rankings)
        def distance(left, right):
            return sum(right.index(left[i]) > right.index(left[j]) for i in range(3) for j in range(i + 1, 3))
        for power in (1, 1.5, 2, 3, 5):
            with self.subTest(power=power):
                def cost(output):
                    return sum(weight * distance(ranking, output)**power for ranking, weight in rankings.items())
                best = min(cost(output) for output in itertools.permutations('abc'))
                self.assertAlmostEqual(cost(RankAggregator.compute_kemeny_power(profile, power)), best)

    def test_partial_results_map_back_to_external_ids(self):
        def partial(profile):
            raise PartialResult(list(profile.candidates), 'Not certified')
        with patch.dict('rankedit_rules.aggregator.RULE_REGISTRY', {'Borda': partial}):
            with self.assertRaises(PartialResult) as caught:
                RankAggregator.compute_borda(RankingProfile(['A-B', 'A+B'], {('A-B', 'A+B'): 1}))
        self.assertEqual(caught.exception.result, ['A-B', 'A+B'])
        self.assertEqual(caught.exception.warning, 'Not certified')

    def test_time_limits(self):
        profile = RankingProfile(['a', 'b'], {('a', 'b'): 1})
        for method in (RankAggregator.compute_kemeny, RankAggregator.compute_squared_kemeny, RankAggregator.compute_kemeny_power):
            for time_limit in (0, -1, math.inf, math.nan):
                with self.subTest(method=method.__name__, time_limit=time_limit):
                    with self.assertRaises(ValueError):
                        method(profile, time_limit=time_limit)
            self.assertEqual(method(profile, time_limit=None), ['a', 'b'])
        self.assertEqual(RankAggregator.compute_kemeny_power(profile, 2, time_limit=None), ['a', 'b'])

    def test_solver_time_limits_are_forwarded_per_call(self):
        def solve(profile, *args, **parameters):
            return list(profile.candidates)
        for method, key in [(RankAggregator.compute_kemeny, 'Kemeny'), (RankAggregator.compute_squared_kemeny, 'Squared Kemeny')]:
            solver = Mock(side_effect=solve)
            with patch.dict('rankedit_rules.aggregator.RULE_REGISTRY', {key: solver}):
                for limit in (60, None, 14):
                    method(self.profile, time_limit=limit)
                    self.assertEqual(solver.call_args.kwargs['time_limit'], limit)
                method(self.profile)
                self.assertIsNone(solver.call_args.kwargs['time_limit'])
        with patch('rankedit_rules._registry.p_kemeny_ilp', side_effect=solve) as solver:
            RankAggregator.compute_kemeny_power(self.profile, 2, time_limit=60)
            self.assertEqual(solver.call_args.kwargs['time_limit'], 60)
            RankAggregator.compute_kemeny_power(self.profile, 2)
            self.assertIsNone(solver.call_args.kwargs['time_limit'])
