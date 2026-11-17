from __future__ import annotations
from ..profile import RankingProfile

# score_matrix[i][j] = score for position j (0-indexed) in round i (0-indexed).
# Round i has m-i candidates remaining. Entries with j >= m-i are unused (should be 0).
ScoreMatrix = list[list[float]]



def _make_borda_matrix(m: int) -> ScoreMatrix:
    matrix = []
    for i in range(m):
        k = m - i  # candidates remaining in round i
        row = [float(k - 1 - j) for j in range(k)] + [0.0] * (m - k)
        matrix.append(row)
    return matrix


def _make_plurality_matrix(m: int) -> ScoreMatrix:
    return [[1.0] + [0.0] * (m - 1) for _ in range(m)]


def _make_veto_matrix(m: int) -> ScoreMatrix:
    matrix = []
    for i in range(m):
        k = m - i  # candidates remaining in round i
        row = [1.0] * (k - 1) + [0.0] * (m - k + 1)
        matrix.append(row)
    return matrix


def _compute_scores(profile: RankingProfile, score_matrix: ScoreMatrix, round_index: int) -> dict[str, float]:
    scores: dict[str, float] = {c: 0.0 for c in profile.get_candidates()}
    for ranking in profile.get_rankings():
        weight = profile.get_weight(ranking)
        for j in range(len(ranking)):
            scores[ranking[j]] += weight * score_matrix[round_index][j]
    return scores


def static_scoring_rule(profile: RankingProfile, score_matrix: ScoreMatrix) -> list[str]:
    scores = _compute_scores(profile, score_matrix, 0)
    tie_break = profile.candidate_order()
    return sorted(
        profile.candidates,
        key=lambda c: (round(scores[c],9), -tie_break[c]),
        reverse=True,
    )


def seq_winner_scoring_rule(profile: RankingProfile, score_matrix: ScoreMatrix) -> list[str]:
    tie_break = profile.candidate_order()
    output: list[str] = []
    round_index = 0
    while len(profile.get_candidates())>0:
        scores = _compute_scores(profile, score_matrix, round_index)
        winner = max(profile.get_candidates(), key=lambda c: (round(scores[c],9), -tie_break[c]))
        output.append(winner)
        profile.delete_candidate(winner)
        round_index += 1
    return output


def seq_loser_scoring_rule(profile: RankingProfile, score_matrix: ScoreMatrix) -> list[str]:
    tie_break = profile.candidate_order()
    output: list[str] = []
    round_index = 0
    while len(profile.get_candidates())>0:
        scores = _compute_scores(profile, score_matrix, round_index)
        loser = min(profile.get_candidates(), key=lambda c: (round(scores[c],9), tie_break[c]))
        output.append(loser)
        profile.delete_candidate(loser)
        round_index += 1
    output.reverse()
    return output


def prop_seq_scoring_rule(profile: RankingProfile, score_matrix: ScoreMatrix) -> list[str]:
    m = len(profile.candidates)
    S = sum(score_matrix[i][0] for i in range(m - 1))
    tie_break = profile.candidate_order()

    rankings = profile.get_rankings()
    total_w = sum([profile.get_weight(r) for r in rankings])
    if total_w == 0 or S == 0:
        return sorted(profile.get_candidates(), key=lambda c: tie_break[c])

    for ranking in rankings:
        profile_weight = profile.get_weight(ranking)
        profile.update_weight(ranking,profile_weight * S / total_w)

    output: list[str] = []
    round_index = 0

    while len(profile.get_candidates()) > 0:
        rankings = profile.get_rankings()
        cost = score_matrix[round_index][0]
        scores = _compute_scores(profile, score_matrix, round_index)
        winner = max(profile.get_candidates(), key=lambda c: (round(scores[c],9), -tie_break[c]))
        winner_score = scores[winner]
        output.append(winner)

        if winner_score > 0:
            for ranking in rankings:
                weight = profile.get_weight(ranking)
                score_contr = score_matrix[round_index][ranking.index(winner)]
                payment = cost * weight * score_contr / winner_score
                profile.update_weight(ranking, max(weight-payment, 0))

        profile.delete_candidate(winner)
        round_index += 1

    return output


# Named rule functions

def plurality_rule(profile: RankingProfile) -> list[str]:
    return static_scoring_rule(profile, _make_plurality_matrix(len(profile.candidates)))


def borda_rule(profile: RankingProfile) -> list[str]:
    return static_scoring_rule(profile, _make_borda_matrix(len(profile.candidates)))


def veto_rule(profile: RankingProfile) -> list[str]:
    return static_scoring_rule(profile, _make_veto_matrix(len(profile.candidates)))


def seq_winner_plurality_rule(profile: RankingProfile) -> list[str]:
    return seq_winner_scoring_rule(profile, _make_plurality_matrix(len(profile.candidates)))


def seq_winner_borda_rule(profile: RankingProfile) -> list[str]:
    return seq_winner_scoring_rule(profile, _make_borda_matrix(len(profile.candidates)))


def seq_winner_veto_rule(profile: RankingProfile) -> list[str]:
    return seq_winner_scoring_rule(profile, _make_veto_matrix(len(profile.candidates)))


def seq_loser_plurality_rule(profile: RankingProfile) -> list[str]:
    return seq_loser_scoring_rule(profile, _make_plurality_matrix(len(profile.candidates)))


def seq_loser_borda_rule(profile: RankingProfile) -> list[str]:
    return seq_loser_scoring_rule(profile, _make_borda_matrix(len(profile.candidates)))


def seq_loser_veto_rule(profile: RankingProfile) -> list[str]:
    return seq_loser_scoring_rule(profile, _make_veto_matrix(len(profile.candidates)))


def prop_seq_plurality_rule(profile: RankingProfile) -> list[str]:
    return prop_seq_scoring_rule(profile, _make_plurality_matrix(len(profile.candidates)))


def prop_seq_borda_rule(profile: RankingProfile) -> list[str]:
    return prop_seq_scoring_rule(profile, _make_borda_matrix(len(profile.candidates)))


def prop_seq_veto_rule(profile: RankingProfile) -> list[str]:
    return prop_seq_scoring_rule(profile, _make_veto_matrix(len(profile.candidates)))
