"""Private rule lookup and custom-parameter construction."""
import math

from .rules import (
    plurality_rule, borda_rule, veto_rule,
    seq_winner_plurality_rule, seq_winner_borda_rule, seq_winner_veto_rule,
    seq_loser_plurality_rule, seq_loser_borda_rule, seq_loser_veto_rule,
    prop_seq_plurality_rule, prop_seq_borda_rule, prop_seq_veto_rule,
    rev_seq_stv, rev_seq_EAR,
    scr_rule,
    standard_pse_rule,
    factorial_pse_rule,
    pse_rule,
    static_scoring_rule, seq_winner_scoring_rule,
    seq_loser_scoring_rule, prop_seq_scoring_rule,
)
from .rules.kemeny_ilp import kemeny_ilp, p_kemeny_ilp, squared_kemeny_ilp


RULE_REGISTRY = {
    "Plurality": plurality_rule,
    "Seq. Winner Plurality": seq_winner_plurality_rule,
    "Seq. Loser Plurality": seq_loser_plurality_rule,
    "Borda": borda_rule,
    "Seq. Winner Borda": seq_winner_borda_rule,
    "Seq. Loser Borda": seq_loser_borda_rule,
    "Veto": veto_rule,
    "Seq. Winner Veto": seq_winner_veto_rule,
    "Seq. Loser Veto": seq_loser_veto_rule,
    "Prop. Seq. Plurality": prop_seq_plurality_rule,
    "Prop. Seq. Borda": prop_seq_borda_rule,
    "Prop. Seq. Veto": prop_seq_veto_rule,
    "Reverse Sequential STV": rev_seq_stv,
    "Kemeny": kemeny_ilp,
    "Squared Kemeny": squared_kemeny_ilp,
    "SCR": scr_rule,
    "Reverse Sequential EAR": rev_seq_EAR,
    "PSE": standard_pse_rule,
    "Factorial PSE": factorial_pse_rule,
}

SCORING_VARIANTS = {
    "static": static_scoring_rule,
    "seq_winner": seq_winner_scoring_rule,
    "seq_loser": seq_loser_scoring_rule,
    "prop_seq": prop_seq_scoring_rule,
}


def build_custom_rule(family: str, params: dict, candidate_count: int, *, time_limit: float | None = None):
    """Build a rule callable for a custom (parameterized) rule spec.

    Raises ValueError with a user-facing message on invalid parameters.
    Returns a callable (profile) -> list[str].
    """
    allowed = {
        "pse": {"weights"},
        "scoring": {"variant", "score_mode", "scores", "score_matrix", "round_weights"},
        "kemeny_power": {"p"},
    }
    if family not in allowed:
        raise ValueError(f"Unknown rule family: {family}")
    if set(params) - allowed[family]:
        raise ValueError(f"Unknown parameters: {', '.join(sorted(set(params) - allowed[family]))}")

    def numeric_vector(values, name, nonnegative=False):
        if not isinstance(values, (list, tuple)):
            raise ValueError(f"{name} must be a numeric vector")
        try:
            converted = [float(value) for value in values]
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError(f"{name} must contain finite numbers") from error
        if any(not math.isfinite(value) or (nonnegative and value < 0) for value in converted):
            raise ValueError(f"{name} must contain finite {'nonnegative ' if nonnegative else ''}numbers")
        return converted

    params = dict(params)
    for name in ("weights", "round_weights", "scores"):
        if name in params:
            params[name] = numeric_vector(params[name], name, name != "scores" or params.get("variant") == "prop_seq")
    if "score_matrix" in params:
        if not isinstance(params["score_matrix"], (list, tuple)):
            raise ValueError("score_matrix must be a list of rows")
        params["score_matrix"] = [numeric_vector(row, "score_matrix row", params.get("variant") == "prop_seq") for row in params["score_matrix"]]

    if family == "pse":
        weights = params.get("weights")
        if not isinstance(weights, list) or len(weights) != candidate_count:
            raise ValueError(f"PSE weight vector must have exactly {candidate_count} entries")
        weights_tuple = tuple(float(w) for w in weights)
        return lambda profile: pse_rule(profile, weights_tuple)

    if family == "scoring":
        rule_fn = SCORING_VARIANTS.get(params.get("variant", "static"))
        if rule_fn is None:
            raise ValueError(f"Unknown scoring variant: {params.get('variant')}")

        score_mode = params.get("score_mode", "chop_bottom")
        if score_mode not in ("full", "chop_top", "chop_bottom"):
            raise ValueError(f"Unknown score mode: {score_mode}")
        m = candidate_count

        # "Full score system": frontend sends matrix[k-1] = length-k score vector
        # for the round with k candidates remaining. Convert to our m×m format
        # where score_matrix[i] is the row for round i (m-i candidates remain).
        if score_mode == "full":
            raw = params.get("score_matrix")
            if not isinstance(raw, list) or len(raw) != m:
                raise ValueError(f"Score matrix must have exactly {m} rows")
            score_matrix = [[0.0] * m for _ in range(m)]
            for k, row in enumerate(raw, start=1):
                if not isinstance(row, list) or len(row) != k:
                    raise ValueError(f"Score matrix row for {k} remaining candidate(s) must have exactly {k} entries")
                round_idx = m - k
                for j, s in enumerate(row):
                    score_matrix[round_idx][j] = float(s)
            return lambda profile: rule_fn(profile, score_matrix)

        scores = params.get("scores")
        if not isinstance(scores, list) or len(scores) != m:
            raise ValueError(f"Score vector must have exactly {m} entries")

        if params.get("variant") == "prop_seq" and score_mode in ("chop_top", "chop_bottom"):
            round_weights = params.get("round_weights")
            if round_weights is None:
                round_weights = [1.0] * m
            if not isinstance(round_weights, list) or len(round_weights) != m:
                raise ValueError(f"Round weight vector must have exactly {m} entries")
            if score_mode == "chop_top":
                score_matrix = [
                    [round_weights[i] * scores[i + j] if j < m - i else 0.0 for j in range(m)]
                    for i in range(m)
                ]
            else:  # chop_bottom
                score_matrix = [
                    [round_weights[i] * scores[j] if j < m - i else 0.0 for j in range(m)]
                    for i in range(m)
                ]
            return lambda profile: rule_fn(profile, score_matrix)

        if score_mode == "chop_top":
            score_matrix = [
                [float(scores[i + j]) if j < m - i else 0.0 for j in range(m)]
                for i in range(m)
            ]
        else:  # chop_bottom (default)
            score_matrix = [
                [float(scores[j]) if j < m - i else 0.0 for j in range(m)]
                for i in range(m)
            ]
        return lambda profile: rule_fn(profile, score_matrix)

    if family == "kemeny_power":
        p = float(params.get("p", 1))
        if not math.isfinite(p) or p < 1 or p > 5:
            raise ValueError("p must be between 1 and 5")
        return lambda profile: p_kemeny_ilp(profile, p, time_limit=time_limit)

    raise ValueError(f"Unknown rule family: {family}")

