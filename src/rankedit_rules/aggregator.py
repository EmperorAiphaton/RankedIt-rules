"""Named aggregation methods operating on independently constructed profiles."""
from __future__ import annotations
import math
from collections.abc import Sequence

from .profile import RankingProfile
from ._registry import RULE_REGISTRY, build_custom_rule
from .rules.kemeny_ilp import PartialResult


class RankAggregator:
    """Static rule interface. Pass a RankingProfile to each compute method.

    Kemeny methods accept their own solver time_limit; None removes that limit.
    Every method returns candidate IDs in aggregate order and preserves its input.
    """

    @staticmethod
    def _validate_time_limit(time_limit: float | None) -> None:
        if time_limit is not None and (not math.isfinite(time_limit) or time_limit <= 0):
            raise ValueError("The solver time limit must be positive and finite, or None.")

    @staticmethod
    def _compute(profile: RankingProfile, rule) -> list[str]:
        if not isinstance(profile, RankingProfile):
            raise TypeError("profile must be a RankingProfile object.")
        # Revalidate a snapshot in case the user edited the profile. Canonical
        # IDs prevent solver variable-name collisions for punctuation or Unicode.
        snapshot = RankingProfile(profile.candidates, profile.rankings)
        external = {f"c{i}": c for i, c in enumerate(snapshot.candidates)}
        internal = {c: key for key, c in external.items()}
        working = RankingProfile(tuple(external), {
            tuple(internal[c] for c in ranking): weight
            for ranking, weight in snapshot.rankings.items()
        })
        try:
            ranking = rule(working)
        except PartialResult as result:
            raise PartialResult([external[c] for c in result.result], result.warning) from result
        return [external[c] for c in ranking]

    @staticmethod
    def compute_plurality(profile: RankingProfile) -> list[str]:
        """Compute Plurality."""
        return RankAggregator._compute(profile, RULE_REGISTRY['Plurality'])

    @staticmethod
    def compute_seq_winner_plurality(profile: RankingProfile) -> list[str]:
        """Compute Seq. Winner Plurality."""
        return RankAggregator._compute(profile, RULE_REGISTRY['Seq. Winner Plurality'])

    @staticmethod
    def compute_seq_loser_plurality(profile: RankingProfile) -> list[str]:
        """Compute Seq. Loser Plurality."""
        return RankAggregator._compute(profile, RULE_REGISTRY['Seq. Loser Plurality'])

    @staticmethod
    def compute_borda(profile: RankingProfile) -> list[str]:
        """Compute Borda."""
        return RankAggregator._compute(profile, RULE_REGISTRY['Borda'])

    @staticmethod
    def compute_seq_winner_borda(profile: RankingProfile) -> list[str]:
        """Compute Seq. Winner Borda."""
        return RankAggregator._compute(profile, RULE_REGISTRY['Seq. Winner Borda'])

    @staticmethod
    def compute_seq_loser_borda(profile: RankingProfile) -> list[str]:
        """Compute Seq. Loser Borda."""
        return RankAggregator._compute(profile, RULE_REGISTRY['Seq. Loser Borda'])

    @staticmethod
    def compute_veto(profile: RankingProfile) -> list[str]:
        """Compute Veto."""
        return RankAggregator._compute(profile, RULE_REGISTRY['Veto'])

    @staticmethod
    def compute_seq_winner_veto(profile: RankingProfile) -> list[str]:
        """Compute Seq. Winner Veto."""
        return RankAggregator._compute(profile, RULE_REGISTRY['Seq. Winner Veto'])

    @staticmethod
    def compute_seq_loser_veto(profile: RankingProfile) -> list[str]:
        """Compute Seq. Loser Veto."""
        return RankAggregator._compute(profile, RULE_REGISTRY['Seq. Loser Veto'])

    @staticmethod
    def compute_prop_seq_plurality(profile: RankingProfile) -> list[str]:
        """Compute Prop. Seq. Plurality."""
        return RankAggregator._compute(profile, RULE_REGISTRY['Prop. Seq. Plurality'])

    @staticmethod
    def compute_prop_seq_borda(profile: RankingProfile) -> list[str]:
        """Compute Prop. Seq. Borda."""
        return RankAggregator._compute(profile, RULE_REGISTRY['Prop. Seq. Borda'])

    @staticmethod
    def compute_prop_seq_veto(profile: RankingProfile) -> list[str]:
        """Compute Prop. Seq. Veto."""
        return RankAggregator._compute(profile, RULE_REGISTRY['Prop. Seq. Veto'])

    @staticmethod
    def compute_reverse_sequential_stv(profile: RankingProfile) -> list[str]:
        """Compute Reverse Sequential STV."""
        return RankAggregator._compute(profile, RULE_REGISTRY['Reverse Sequential STV'])

    @staticmethod
    def compute_kemeny(profile: RankingProfile, *, time_limit: float | None = None) -> list[str]:
        """Compute Kemeny with a solver time limit in seconds (None: unlimited)."""
        RankAggregator._validate_time_limit(time_limit)
        return RankAggregator._compute(profile, lambda p: RULE_REGISTRY['Kemeny'](p, time_limit=time_limit))

    @staticmethod
    def compute_squared_kemeny(profile: RankingProfile, *, time_limit: float | None = None) -> list[str]:
        """Compute Squared Kemeny with a solver time limit (None: unlimited)."""
        RankAggregator._validate_time_limit(time_limit)
        return RankAggregator._compute(profile, lambda p: RULE_REGISTRY['Squared Kemeny'](p, time_limit=time_limit))

    @staticmethod
    def compute_scr(profile: RankingProfile) -> list[str]:
        """Compute SCR."""
        return RankAggregator._compute(profile, RULE_REGISTRY['SCR'])

    @staticmethod
    def compute_reverse_sequential_ear(profile: RankingProfile) -> list[str]:
        """Compute Reverse Sequential EAR."""
        return RankAggregator._compute(profile, RULE_REGISTRY['Reverse Sequential EAR'])

    @staticmethod
    def compute_standard_PSE(profile: RankingProfile) -> list[str]:
        """Compute standard PSE with the all-ones positional weight vector."""
        return RankAggregator.compute_pse(profile, weights=[1] * len(profile.candidates))

    @staticmethod
    def compute_pse(profile: RankingProfile, weights: Sequence[float] | None = None) -> list[str]:
        """Compute PSE; optional positional weights customize the standard rule."""
        if weights is None:
            return RankAggregator._compute(profile, RULE_REGISTRY["PSE"])
        rule = build_custom_rule("pse", {"weights": weights}, len(profile.candidates))
        return RankAggregator._compute(profile, rule)

    @staticmethod
    def compute_factorial_pse(profile: RankingProfile) -> list[str]:
        """Compute Factorial PSE."""
        return RankAggregator._compute(profile, RULE_REGISTRY['Factorial PSE'])

    @staticmethod
    def compute_scoring(
        profile: RankingProfile, scores: Sequence[float] | None = None, *,
        score_mode: str = "chop_bottom", score_matrix: Sequence[Sequence[float]] | None = None,
    ) -> list[str]:
        """Compute static scoring with a vector or full triangular score matrix."""
        parameters = {"variant": 'static', "score_mode": score_mode}
        if scores is not None:
            parameters["scores"] = scores
        if score_matrix is not None:
            parameters["score_matrix"] = score_matrix
        rule = build_custom_rule("scoring", parameters, len(profile.candidates))
        return RankAggregator._compute(profile, rule)

    @staticmethod
    def compute_seq_winner_scoring(
        profile: RankingProfile, scores: Sequence[float] | None = None, *,
        score_mode: str = "chop_bottom", score_matrix: Sequence[Sequence[float]] | None = None,
    ) -> list[str]:
        """Compute seq_winner scoring with a vector or full triangular score matrix."""
        parameters = {"variant": 'seq_winner', "score_mode": score_mode}
        if scores is not None:
            parameters["scores"] = scores
        if score_matrix is not None:
            parameters["score_matrix"] = score_matrix
        rule = build_custom_rule("scoring", parameters, len(profile.candidates))
        return RankAggregator._compute(profile, rule)

    @staticmethod
    def compute_seq_loser_scoring(
        profile: RankingProfile, scores: Sequence[float] | None = None, *,
        score_mode: str = "chop_bottom", score_matrix: Sequence[Sequence[float]] | None = None,
    ) -> list[str]:
        """Compute seq_loser scoring with a vector or full triangular score matrix."""
        parameters = {"variant": 'seq_loser', "score_mode": score_mode}
        if scores is not None:
            parameters["scores"] = scores
        if score_matrix is not None:
            parameters["score_matrix"] = score_matrix
        rule = build_custom_rule("scoring", parameters, len(profile.candidates))
        return RankAggregator._compute(profile, rule)

    @staticmethod
    def compute_prop_seq_scoring(
        profile: RankingProfile, scores: Sequence[float] | None = None, *,
        score_mode: str = "chop_bottom",
        score_matrix: Sequence[Sequence[float]] | None = None,
        round_weights: Sequence[float] | None = None,
    ) -> list[str]:
        """Compute prop_seq scoring with a vector or full triangular score matrix."""
        parameters = {"variant": 'prop_seq', "score_mode": score_mode}
        if scores is not None:
            parameters["scores"] = scores
        if score_matrix is not None:
            parameters["score_matrix"] = score_matrix
        if round_weights is not None:
            parameters["round_weights"] = round_weights
        rule = build_custom_rule("scoring", parameters, len(profile.candidates))
        return RankAggregator._compute(profile, rule)

    @staticmethod
    def compute_kemeny_power(
        profile: RankingProfile, p: float = 1, *, time_limit: float | None = None,
    ) -> list[str]:
        """Compute powered Kemeny for p in [1, 5]; time_limit=None is unlimited."""
        RankAggregator._validate_time_limit(time_limit)
        rule = build_custom_rule("kemeny_power", {"p": p}, len(profile.candidates), time_limit=time_limit)
        return RankAggregator._compute(profile, rule)
