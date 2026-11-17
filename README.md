# RankedIt Rules

RankedIt Rules aggregates weighted, complete, strict rankings into one output
ranking. Use it to compare aggregation methods on the same preferences, compute
an aggregate ranking for an application, or experiment with custom scoring
systems. These are the implementations used by
[RankedIt.org](https://www.rankedit.org). The package contains no website
frontend or datasets.

Create a `RankingProfile`, then pass it to a static method on `RankAggregator`.
Every aggregation method returns a list of candidate IDs from highest to lowest
rank and leaves the input profile unchanged. No aggregator instance is needed.

## Installation

Requires Python 3.10 or newer. From this package's directory:

```bash
python -m pip install .
```

PuLP 3.3.2 is installed as a dependency and includes the CBC solver used by the
Kemeny methods. Its bundled macOS binary may require Rosetta on Apple Silicon.
Other aggregation methods do not invoke the solver.

## Create a profile and compute a ranking

The basic use case of our package is the computation of the implemented rules.
To this end, a user should first create a ranking profile by specifying the available candidates as well as the input rankings with their weights.
Input rankings are written from best (left) to worst (right).
Such a ranking profile can then be handed to any of our rank aggregation methods.

```python
from rankedit_rules import RankAggregator, RankingProfile

profile = RankingProfile(
    candidates=["A", "B", "C"],
    rankings={("A", "B", "C"): 3, ("B", "C", "A"): 2}
)

ranking = RankAggregator.compute_borda(profile)
print(ranking)  # ['B', 'A', 'C']
```

Here, the input consists of two rankings: the first one ranks A ahead of B ahead of C and has weight 3; the second one ranks B ahead of C ahead of A and has weight 2.
Weights need not be integers or sum to one, but must be finite and non-negative, and their sum must be finite and larger than 0.
Input rankings with weight 0 are effectively ignored.
The names of candidates must be distinct strings. Each input ranking must contain every candidate exactly once.

## Guide to all aggregation methods

The following sections cover the 19 rank aggregation methods implemented by the `RankAggregator` class, as well as 6 additional methods that can be customized. For further details, we refer to the papers cited below, which introduced these methods. 

### Static scoring rules

Static scoring rules are defined by a score vector `s`: each ranking assigns `s(i)` points to its i-th best candidate, and the total score of a candidate is the sum of the contributions of each ranking multiplied by its weight. A static scoring rule then arranges the candidates in decreasing order of their total score.
Three common scoring rules are the Plurality rule, which uses the vector `(1, 0, ..., 0)`, the Veto rule, which uses the vector `(1, ..., 1, 0)`, and the Borda rule, which uses the vector `(m-1, m-2, ..., 0)`, where `m` is the number of candidates. Moreover, our package also allows for custom scoring functions where the score vector is part of the input.

```python
plurality = RankAggregator.compute_plurality(profile)
borda = RankAggregator.compute_borda(profile)
veto = RankAggregator.compute_veto(profile)
custom = RankAggregator.compute_scoring(profile, scores=[3, 1, 0])
```

### Sequential-winner scoring rules

Sequential-winner scoring rules also work based on a score function. In each round, they choose the candidate with the highest total score, append it to the output ranking, remove it from the profile, and recompute the scores of the remaining candidates in the reduced profile. We implemented this approach again with Plurality, Borda, and Veto. Moreover, we again allow for custom score vectors. Specifically, there are three modes to input a custom scoring system, depending on how the score vector for fewer alternatives should be constructed:

- `chop_bottom`: deletes the last entry from the score vector: e.g., `[4, 3, 1, 0]` first becomes `[4, 3, 1]` and then `[4, 3]`.
- `chop_top`: deletes the first entry from the score vector: e.g., `[4, 3, 1, 0]` first becomes `[3, 1, 0]` and then `[1, 0]`.
- `full`: specifies a list of score vectors, where the i-th vector contains i entries and is used when i alternatives remain. The last vector is therefore used in the first round.

```python
seqw_plurality = RankAggregator.compute_seq_winner_plurality(profile)
seqw_borda = RankAggregator.compute_seq_winner_borda(profile)
seqw_veto = RankAggregator.compute_seq_winner_veto(profile)
seqw_chop_top = RankAggregator.compute_seq_winner_scoring(profile, score_mode="chop_top", scores=[3, 1, 0])
seqw_chop_bottom = RankAggregator.compute_seq_winner_scoring(profile, score_mode="chop_bottom", scores=[3, 1, 0])
seqw_full = RankAggregator.compute_seq_winner_scoring(profile, score_mode="full", score_matrix=[[0], [1, 0], [3, 2, 0]])
```

### Sequential-loser scoring rules

Sequential-loser scoring rules work analogously to sequential-winner scoring rules, except that they pick the candidate with the lowest score in each round and place it at the bottom of the output ranking. In more detail, in each round, these rules choose the candidate with the lowest total score, add it to the lowest available position of the output ranking, remove it from the profile, and recompute the scores of the remaining candidates in the reduced profile. We support this approach with our three default scoring rules as well as custom scoring rules with the same input format as for sequential-winner scoring rules.

```python
seql_plurality = RankAggregator.compute_seq_loser_plurality(profile)
seql_borda = RankAggregator.compute_seq_loser_borda(profile)
seql_veto = RankAggregator.compute_seq_loser_veto(profile)
seql_chop_top = RankAggregator.compute_seq_loser_scoring(profile, score_mode="chop_top", scores=[3, 1, 0])
seql_chop_bottom = RankAggregator.compute_seq_loser_scoring(profile, score_mode="chop_bottom", scores=[3, 1, 0])
seql_full = RankAggregator.compute_seq_loser_scoring(profile, score_mode="full", score_matrix=[[0], [1, 0], [3, 2, 0]])
```

### Proportional sequential scoring rules

Proportional sequential scoring rules are a variation of sequential winner scoring rules. In each round, after selecting a candidate, these rules reduce the weight of each input ranking in proportion to its contribution to the total score of the selected candidate. This balances the influence of each input ranking on the output ranking and, for suitable scoring systems, guarantees proportional representation. This class of functions again supports Plurality, Borda, and Veto, and the previous methods for inputting custom score systems. Moreover, for the `chop_bottom` and `chop_top` modes, we allow users to specify weights for each round. The score vector is multiplied by the weight of the current round to get the final vector. While positive scaling does not affect score comparisons within a round for fixed input weights, it can be used to express how important a position of the output ranking is (higher weight means intuitively more important).

```python
proportional_plurality = RankAggregator.compute_prop_seq_plurality(profile)
proportional_borda = RankAggregator.compute_prop_seq_borda(profile)
proportional_veto = RankAggregator.compute_prop_seq_veto(profile)
proportional_chop_top = RankAggregator.compute_prop_seq_scoring(profile, score_mode="chop_top", scores=[3, 1, 0], round_weights=[2, 1, 0])
proportional_chop_bottom = RankAggregator.compute_prop_seq_scoring(profile, score_mode="chop_bottom", scores=[3, 1, 0], round_weights=[2, 1, 0])
proportional_full = RankAggregator.compute_prop_seq_scoring(profile, score_mode="full", score_matrix=[[0], [1, 0], [6, 4, 0]])
```


The `round_weights` parameter is used in the chop modes. In `full` mode,
include the scaling directly in the rows of `score_matrix`. Custom scoring
systems do not automatically inherit the proportionality guarantees; these
require the conditions on scoring systems given in the referenced papers.

### Proportional sequential eating rule (PSE)

PSE constructs a ranking sequentially through an eating process. In particular, in each round, the input rankings eat their bottom-ranked candidates at a rate proportional to their remaining weight, fully eaten candidates are removed, and the last fully eaten candidate is selected and appended to the output ranking. Moreover, similar to the proportional sequential scoring rules, we update the weights of the input rankings based on their eating shares to balance the eating process. PSE can take weights as input, which capture the importance of a position of the output ranking. Higher weights mean that a position is more important. We have implemented two such methods: the standard PSE method, where each round has weight 1, and the factorial PSE method, where the weight of the i-th round is (m-i)!. Moreover, weights can also be specified by the user.

```python
standard_pse = RankAggregator.compute_standard_PSE(profile)
factorial_pse = RankAggregator.compute_factorial_pse(profile)
custom_pse = RankAggregator.compute_pse(profile, weights=[2, 1, 0])
```

### Solid coalition refinement rule (SCR) and reverse sequential rules

These methods construct a ranking using committee-based procedures. Specifically, reverse sequential rules repeatedly eliminate the candidate that is unchosen when asking the committee rule for a committee that contains all but one candidate, bottom-rank that candidate, remove it from the profile and repeat. We have implemented this approach with two well-known committee voting rules called single transferable vote (STV) and the expanding approvals rule (EAR). By contrast, the solid coalition refinement rule computes the winning ranking top-down. In each round, it identifies a candidate that helps the most underrepresented group of voters, where the exact candidate is determined by a process of refinement. These rules guarantee to select rankings whose prefixes satisfy proportionality axioms.

```python
scr = RankAggregator.compute_scr(profile)
reverse_stv = RankAggregator.compute_reverse_sequential_stv(profile)
reverse_ear = RankAggregator.compute_reverse_sequential_ear(profile)
```

### Kemeny, Squared Kemeny, and powered Kemeny rules.

Lastly, the Kemeny rule chooses the ranking that minimizes the sum of weighted
swap distances to the input rankings. Moreover, the Squared Kemeny rule chooses
the ranking that minimizes the sum of weighted squared swap distances, which
yields a more proportional rule. We also provide a class of powered
Kemeny rules, which take a power `p` as input and compute the ranking minimizing
the sum of weighted swap distances raised to the power of `p`. These methods
rely on a mixed-integer program and are computationally expensive if there are
many candidates or input rankings. We thus allow a `time_limit` to be provided
for them, measured in seconds. If the solver reaches this `time_limit` before certifying optimality,
a feasible ranking, if available, is provided through `PartialResult`; this
ranking may be suboptimal. If no feasible ranking is available, an error is
raised. The `time_limit` parameter is optional, and no time limit is used by
default.

```python
kemeny = RankAggregator.compute_kemeny(profile)
squared_kemeny = RankAggregator.compute_squared_kemeny(profile, time_limit=60)
powered_kemeny = RankAggregator.compute_kemeny_power(profile, p=1.5, time_limit=15)
```

## References

The methods implemented by this package have been suggested in the following papers. 

- Aziz, H., & Lee, B. E. (2020). [The expanding approvals rule: Improving proportional representation and monotonicity.](https://doi.org/10.1007/s00355-019-01208-3) *Social Choice and Welfare, 54*(1), pp. 1–45.
- Aziz, H., Lederer, P., Peters, D., Peters, J., & Ritossa, A. (2025). [Committee monotonicity and proportional representation for ranked preferences.](https://dl.acm.org/doi/10.1145/3736252.3742642) In *Proceedings of the 26th ACM Conference on Economics and Computation*, p. 896.
- Aziz, H., Lederer, P., & Sharara, M. [Proportional rank aggregation with generalized Kemeny utilities.](https://staff.fnwi.uva.nl/p.lederer/research/ToR.pdf) *Working paper.*
- Boehmer, N., Bredereck, R., & Peters, D. (2026). [Rank aggregation using scoring rules.](https://link.springer.com/article/10.1007/s11238-025-10120-5) *Theory and Decision.* Online first.
- Brandt, F., Conitzer, V., Endriss, U., Lang, J., & Procaccia A. D. (Ed.). (2016). [*Handbook of Computational Social Choice.*](https://www.cambridge.org/files/5015/1077/0783/9781107060432AR_final3.pdf) Cambridge University Press.
- Brandt, F. (2025). [*Social Choice Theory: A Modern Approach with Computational Aspects.*](https://social-choice-theory.com/book.pdf)
- Conitzer, V., Davenport, A., & Kalagnanam, J. (2006). [Improved bounds for computing Kemeny rankings.](https://cdn.aaai.org/AAAI/2006/AAAI06-099.pdf) In *Proceedings of the 21st AAAI Conference on Artificial Intelligence*, pp. 620–626.
- Faliszewski, P., Skowron, P., Slinko, A., & Talmon, N. (2017). [Multiwinner voting: A new challenge for social choice theory.](https://archive.illc.uva.nl/COST-IC1205/BookDocs/Chapters/TrendsCOMSOC-02.pdf) In U. Endriss (Ed.), *Trends in Computational Social Choice*, pp. 27–47. AI Access.
- Lederer, P. (2025). [Proportional representation in rank aggregation.](https://arxiv.org/abs/2508.16177) *arXiv:2508.16177.*
- Lederer, P., Peters, D., & Wąs, T. (2024). [The squared Kemeny rule for averaging rankings.](https://dl.acm.org/doi/10.1145/3670865.3673521) In *Proceedings of the 25th ACM Conference on Economics and Computation*, p. 755.

## Repository and licensing

The package is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE)
for the terms and [NOTICE](NOTICE) for attribution information. The license
permits use, modification, and redistribution, including commercially, subject
to its notice and other requirements. The paper citation below is requested
for academic use; it is not an additional license condition.

Preferred paper citation:

> Patrick Lederer. RankedIt.org: An open-access rank aggregation tool. Working paper, 2026.
