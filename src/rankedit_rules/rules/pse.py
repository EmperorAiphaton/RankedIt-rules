from __future__ import annotations

from fractions import Fraction
from math import factorial, isclose
from typing import Tuple, Dict

from ..profile import RankingProfile


def Bottom_scores(profile: RankingProfile, active_candidates: set[str]) -> dict[str, Fraction]:
    totals: dict[str, Fraction] = {c: Fraction(0) for c in profile.get_candidates()}
    for ranking in profile.get_rankings():
        lowest_active_candidate = max(active_candidates, key=lambda c: ranking.index(c))
        totals[lowest_active_candidate] += Fraction(profile.get_weight(ranking))
    return totals


def run_eating_process(profile: RankingProfile) -> tuple[str, dict[tuple[str, ...], dict[str, float]]]:
    candidates_eating_shares: dict[str, Fraction] = {c: Fraction(0) for c in profile.get_candidates()}
    eating_shares: dict[tuple[str, ...], dict[str, float]] = {
        ranking: {c: 0.0 for c in profile.get_candidates()}
        for ranking in profile.get_rankings()}
    active_candidates = profile.get_candidates()
    tie_break = profile.candidate_order()
    last_candidate = ""
    while len(active_candidates) > 0:
        bottom_scores = Bottom_scores(profile, active_candidates)
        finishing_times: dict[str, Fraction] = {}
        for candidate in active_candidates:
            if bottom_scores[candidate] == 0:
                finishing_times[candidate] = Fraction(10**18)
            else:
                finishing_times[candidate] = (Fraction(1)-candidates_eating_shares[candidate])/bottom_scores[candidate]
        loser = min(active_candidates, key=lambda c: finishing_times[c])
        to_delete = set()
        for candidate in active_candidates:
            candidates_eating_shares[candidate] += bottom_scores[candidate]*finishing_times[loser]
            if candidates_eating_shares[candidate] >= Fraction(1):
                to_delete.add(candidate)
        for ranking in profile.get_rankings():
            lowest_active_candidate = max(active_candidates, key=lambda c: ranking.index(c))
            eating_shares[ranking][lowest_active_candidate] += float(finishing_times[loser]) * profile.get_weight(ranking)
        if active_candidates.issubset(to_delete):
            last_candidate = max(active_candidates, key=lambda c: -tie_break[c])
            break
        else:
            for candidate in to_delete:
                active_candidates.remove(candidate)
    return last_candidate, eating_shares


def pse_rule(profile: RankingProfile, weights: tuple[int, ...]) -> list[str]:
    m = len(profile.get_candidates())
    tie_break = profile.candidate_order()
    max_utility = sum(weights[i] * (m-i-1) for i in range(m))
    total_weight = sum(profile.get_weight(ranking) for ranking in profile.get_rankings())
    round_index = 0
    output = []

    for ranking in profile.get_rankings():
        ranking_weight = profile.get_weight(ranking)
        profile.update_weight(ranking, 1.0 * ranking_weight * max_utility / total_weight)

    while len(profile.get_candidates()) > 0:
        total_budget = sum(profile.get_weight(ranking) for ranking in profile.get_rankings())
        if total_budget == 0:
            winner = max(profile.get_candidates(), key=lambda c: -tie_break[c])
            output.append(winner)
            profile.delete_candidate(winner)
        else:
            winner, eating_shares = run_eating_process(profile.copy())
            output.append(winner)
            multiplier = min(weights[round_index], 1.0 * total_budget / len(profile.get_candidates()))
            for ranking in profile.get_rankings():
                total_consumption = sum(eating_shares[ranking][candidate] for candidate in profile.get_candidates() if candidate!=winner)
                old_budget = profile.get_weight(ranking)
                new_budget = old_budget - multiplier * total_consumption
                profile.update_weight(ranking, new_budget)
            profile.delete_candidate(winner)
        round_index+=1
    return output


def standard_pse_rule(profile: RankingProfile) -> list[str]:
    """PSE with the standard weight vector (1, ..., 1, 0)."""
    m = len(profile.candidates)
    weights = tuple(1 for _ in range(m - 1)) + (0,)
    return pse_rule(profile, weights)


def factorial_pse_rule(profile: RankingProfile) -> list[str]:
    """PSE with the factorial weight vector ((m-1)!, (m-2)!, ..., 1!, 0)."""
    m = len(profile.candidates)
    weights = tuple(factorial(m - 1 - i) for i in range(m - 1)) + (0,)
    return pse_rule(profile, weights)
