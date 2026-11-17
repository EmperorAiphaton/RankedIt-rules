from __future__ import annotations
from typing import Callable

#from ..profile import RankingProfile
from ..profile import RankingProfile

EPS = 1e-9  # tolerance for floating-point comparisons


def rev_seq(profile: RankingProfile, find_loser: Callable[[RankingProfile], str]) -> list[str]:
    output = []
    while len(profile.get_candidates())>0:
        copy = profile.copy()
        loser = find_loser(copy)
        output.append(loser)
        profile.delete_candidate(loser)
    output.reverse()
    return output

def Plurality_scores(profile: RankingProfile) -> dict[str, float]:
    totals: dict[str, float] = {c: 0.0 for c in profile.get_candidates()}
    for ranking in profile.get_rankings():
        totals[ranking[0]]+=profile.get_weight(ranking)
    return totals


def STV_loser(profile: RankingProfile) -> str:
    total_weight = sum([profile.get_weight(ranking) for ranking in profile.get_rankings()])
    quota = total_weight/len(profile.get_candidates()) #Droop quota for k=m-1
    tie_break = profile.candidate_order()
    while len(profile.get_candidates()) > 1:
        scores = Plurality_scores(profile)
        winner = max(profile.get_candidates(), key=lambda c: (round(scores[c], 9), -tie_break[c]))
        loser =  min(profile.get_candidates(), key=lambda c: (round(scores[c],9), tie_break[c]))
        if scores[winner]>quota+EPS:
            for ranking in profile.get_rankings():
                if ranking[0] == winner:
                    weight = profile.get_weight(ranking)
                    profile.update_weight(ranking, weight - quota * weight/ scores[winner])
            profile.delete_candidate(winner)
        else:
            return loser
    return profile.get_candidates().pop()


def rev_seq_stv(profile: RankingProfile) -> list[str]:
    return rev_seq(profile, STV_loser)


def jApproval_scores(profile: RankingProfile, j:int) -> dict[str, float]:
    totals: dict[str, float] = {c: 0.0 for c in profile.get_candidates()}
    for ranking in profile.get_rankings():
        for i in range(0,j):
            totals[ranking[i]]+=profile.get_weight(ranking)
    return totals


def EAR_loser(profile: RankingProfile) -> str:
    total_weight = sum([profile.get_weight(ranking) for ranking in profile.get_rankings()])
    quota = total_weight / len(profile.get_candidates()) #Droop quota for k=m-1
    tie_break = profile.candidate_order()
    approval_depth = 1
    committee = set()
    while len(profile.get_candidates().difference(committee)) > 1:
        scores = jApproval_scores(profile, approval_depth)
        winner = max(profile.get_candidates().difference(committee), key=lambda c: (round(scores[c], 9), -tie_break[c]))
        if scores[winner] > quota + EPS:
            committee.add(winner)
            for ranking in profile.get_rankings():
                if ranking.index(winner)<approval_depth:
                    weight = profile.get_weight(ranking)
                    profile.update_weight(ranking, weight - quota * weight/ scores[winner])
        else:
            approval_depth += 1
    loser = profile.get_candidates().difference(committee).pop()
    return loser


def rev_seq_EAR(profile: RankingProfile) -> list[str]:
    return rev_seq(profile, EAR_loser)


#print(rev_seq_EAR(profile))
