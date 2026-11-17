"""User-created weighted profiles shared by all aggregation methods."""
from __future__ import annotations
from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
import math


class RankingProfile:
    """Complete strict rankings over ordered, distinct string candidate IDs.

    Candidate order defines fixed tie-breaking. Input rankings may be a mapping
    or (ranking, weight) pairs. Duplicate rankings are summed; zero weights are
    ignored. Inputs are copied and weights must be finite and nonnegative with
    positive total weight. Aggregation methods never mutate this object.
    """

    def __init__(
        self,
        candidates: Sequence[str],
        rankings: Mapping[tuple[str, ...], float] | Iterable[tuple[Sequence[str], float]],
    ) -> None:
        candidates = tuple(candidates)
        if not candidates or any(not isinstance(c, str) for c in candidates):
            raise ValueError("Provide a nonempty ordered sequence of string candidate IDs.")
        if len(set(candidates)) != len(candidates):
            raise ValueError("Candidate IDs must be distinct.")
        combined: dict[tuple[str, ...], float] = {}
        entries = rankings.items() if isinstance(rankings, Mapping) else rankings
        for ranking, value in entries:
            ranking = tuple(ranking)
            if len(ranking) != len(candidates) or set(ranking) != set(candidates):
                raise ValueError("Every ranking must contain every candidate exactly once.")
            try:
                weight = float(value)
            except (TypeError, ValueError, OverflowError) as error:
                raise ValueError("Ranking weights must be finite nonnegative numbers.") from error
            if not math.isfinite(weight) or weight < 0:
                raise ValueError("Ranking weights must be finite nonnegative numbers.")
            if weight == 0:
                continue
            key = ranking
            combined[key] = combined.get(key, 0.0) + weight
        if not combined:
            raise ValueError("At least one ranking must have positive weight.")
        if any(not math.isfinite(weight) for weight in combined.values()) or not math.isfinite(sum(combined.values())):
            raise ValueError("The total ranking weight must be finite.")
        self.candidates = candidates
        self.rankings = combined

    def get_candidates(self) -> set[str]:
        return set(self.candidates)

    def get_rankings(self) -> set[tuple[str, ...]]:
        return set(self.rankings.keys())

    def get_weight(self, ranking: tuple[str, ...]) -> float:
        return self.rankings[ranking]

    def copy(self) -> RankingProfile:
        return deepcopy(self)

    def candidate_order(self) -> dict[str, int]:
        return {candidate: index for index, candidate in enumerate(self.candidates)}

    def get_position(self, ranking: tuple[str, ...], candidate: str) -> int:
        return ranking.index(candidate)

    def update_weight(self, ranking: tuple[str, ...], new_weight: float) -> None:
        self.rankings[ranking] = new_weight

    def delete_candidate(self, candidate: str) -> None:
        self.candidates = tuple(c for c in self.candidates if c != candidate)
        new_rankings: dict[tuple[str, ...], float] = {}
        for ranking, weight in self.rankings.items():
            key = tuple(c for c in ranking if c != candidate)
            new_rankings[key] = new_rankings.get(key, 0) + weight
        self.rankings = new_rankings
