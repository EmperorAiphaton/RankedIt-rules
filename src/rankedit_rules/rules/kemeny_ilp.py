from __future__ import annotations

from itertools import combinations

from pulp import LpBinary, LpMinimize, LpProblem, LpSolutionIntegerFeasible, LpSolutionOptimal, LpStatus, LpVariable, PULP_CBC_CMD, lpSum

from ..profile import RankingProfile


class PartialResult(Exception):
    """Raised when a rule produces a result that may not be optimal."""

    def __init__(self, result: list[str], warning: str) -> None:
        super().__init__(warning)
        self.result = result
        self.warning = warning


def _completeness_and_transitivity(problem: LpProblem, candidates: list[str], x: dict[tuple[str, str], LpVariable]) -> None:
    for i, a in enumerate(candidates):
        for b in candidates[i + 1 :]:
            problem += x[(a, b)] + x[(b, a)] == 1
    for a, b, c in combinations(candidates, 3):
        problem += x[(a, b)] + x[(b, c)] + x[(c, a)] >= 1
        problem += x[(a, c)] + x[(c, b)] + x[(b, a)] >= 1


def _solve_and_rank(problem: LpProblem, x: dict[tuple[str, str], LpVariable], candidates: list[str], profile: RankingProfile, solver_name: str, time_limit: float | None = None) -> list[str]:
    solver = PULP_CBC_CMD(msg=False, timeLimit=time_limit)
    result_status = problem.solve(solver)
    status_text = LpStatus.get(result_status, "Unknown")
    if status_text not in ("Optimal", "Not Solved"):
        raise RuntimeError(f"{solver_name} ILP solver failed with status: {status_text}")

    if problem.sol_status not in (LpSolutionOptimal, LpSolutionIntegerFeasible):
        raise RuntimeError(f"{solver_name} ILP solver returned no feasible integer solution")

    is_optimal = (problem.sol_status == LpSolutionOptimal)

    tie_break_order = profile.candidate_order()
    wins: dict[str, int] = {candidate: 0 for candidate in candidates}
    for a in candidates:
        for b in candidates:
            if a != b and x[(a, b)].value() >= 0.5:
                wins[a] += 1

    ranking = sorted(candidates, key=lambda candidate: (-wins[candidate], tie_break_order[candidate]))
    if not is_optimal:
        raise PartialResult(ranking, "Time limit reached — result may not be optimal")
    return ranking


def _pairwise_margins(profile: RankingProfile) -> dict[tuple[str, str], float]:
    margins: dict[tuple[str, str], float] = {(c,d): 0.0 for c in profile.get_candidates() for d in profile.get_candidates()}

    for ranking in profile.get_rankings():
        weight = profile.get_weight(ranking)
        for i in range(len(ranking)):
            for j in range(i + 1, len(ranking)):
                margins[(ranking[i], ranking[j])] += weight
    return margins


def kemeny_ilp(profile: RankingProfile, time_limit: float | None = None) -> list[str]:
    candidates = list(profile.get_candidates())
    if len(candidates) <= 1:
        return candidates

    margins = _pairwise_margins(profile)
    problem = LpProblem("kemeny_lp3", LpMinimize)

    x: dict[tuple[str, str], LpVariable] = {}
    for a in candidates:
        for b in candidates:
            if a != b:
                x[(a, b)] = LpVariable(f"x__{a}__{b}", cat=LpBinary)

    _completeness_and_transitivity(problem, candidates, x)

    objective_terms = [
        margins[(b, a)] * x[(a, b)]
        for a in candidates
        for b in candidates
        if a != b
    ]
    problem += lpSum(objective_terms)

    return _solve_and_rank(problem, x, candidates, profile, "Kemeny", time_limit)


def p_kemeny_ilp(profile: RankingProfile, p: float = 1.0, time_limit: float | None = None) -> list[str]:
    candidates = list(profile.candidates)
    candidate_count = len(candidates)
    max_swaps = candidate_count * (candidate_count - 1) // 2

    if candidate_count <= 1:
        return candidates

    problem = LpProblem("p_kemeny", LpMinimize)

    x: dict[tuple[str, str], LpVariable] = {}
    for left in candidates:
        for right in candidates:
            if left != right:
                x[(left, right)] = LpVariable(f"x__{left}__{right}", cat=LpBinary)

    _completeness_and_transitivity(problem,candidates,x)

    dist: list[LpVariable] = []
    pdist: list[LpVariable] = []
    for ranking_index, (ranking, weight) in enumerate(profile.rankings.items()):
        dist_var = LpVariable(f"dist_{ranking_index}", lowBound=0, upBound=max_swaps)
        pdist_var = LpVariable(f"pdist_{ranking_index}", lowBound=0)
        dist.append(dist_var)
        pdist.append(pdist_var)

        inversion_terms = []
        for left_index, left in enumerate(ranking):
            for right in ranking[left_index + 1 :]:
                inversion_terms.append(x[(right, left)])
        problem += dist_var == lpSum(inversion_terms)

        for k in range(max_swaps + 1):
            slope = p * (k ** (p - 1)) if k > 0 else (p if p == 1 else 0.0)
            intercept = (k ** p) - slope * k
            problem += pdist_var >= slope * dist_var + intercept

    problem += lpSum(weight * pdist_var for (_, weight), pdist_var in zip(profile.rankings.items(), pdist))

    return _solve_and_rank(problem, x, candidates, profile, f"{p}-power Kemeny", time_limit)


def squared_kemeny_ilp(profile: RankingProfile, time_limit: float | None = None) -> list[str]:
    return p_kemeny_ilp(profile, 2.0, time_limit)
