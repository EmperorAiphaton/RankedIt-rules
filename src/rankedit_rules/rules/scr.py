from __future__ import annotations

import copy

from ..profile import RankingProfile

def scr_rule(profile: RankingProfile) -> list[str]:
    tie_break = profile.candidate_order()
    supported_candidate_sets = {frozenset(ranking[0:i]) for ranking in profile.get_rankings() for i in range(1, len(ranking)+1)}
    solid_coalitions: dict[frozenset[str], float] = {}
    for supported_candidate_set in supported_candidate_sets:
        support = 0.0
        for ranking in profile.rankings:
            worst_pos = max([ranking.index(c) for c in supported_candidate_set])
            if worst_pos < len(supported_candidate_set):
                support += profile.get_weight(ranking)
        solid_coalitions[supported_candidate_set] = support
    output = []
    outputset = set()

    while len(output)<len(profile.get_candidates()):
        working_support_sets=copy.deepcopy(supported_candidate_sets)
        most_underrepresented_set = min(working_support_sets,
                                        key=lambda X: (-solid_coalitions[X] / (1 + len(outputset.intersection(X))),
                                                       len(X), tuple(sorted(tie_break[c] for c in X))))
        while len(most_underrepresented_set.difference(outputset))>1:
            working_support_sets = {working_support_set for working_support_set in working_support_sets
                                    if working_support_set.issubset(most_underrepresented_set)
                                    and len(working_support_set)<len(most_underrepresented_set)}
            most_underrepresented_set = min(working_support_sets,
                                        key=lambda X: (-solid_coalitions[X] / (1 + len(outputset.intersection(X))),
                                                       len(X), tuple(sorted(tie_break[c] for c in X))))
        winner = list(most_underrepresented_set.difference(outputset)).pop()
        output.append(winner)
        outputset.add(winner)
        supported_candidate_sets = {supported_candidate_set for supported_candidate_set in supported_candidate_sets
                                        if not supported_candidate_set.issubset(outputset)}
    return output
