"""Weighted rank aggregation through profiles and named rule methods."""
from .aggregator import RankAggregator
from .profile import RankingProfile
from .rules.kemeny_ilp import PartialResult

__version__ = "0.1.0"
__all__ = ["RankAggregator", "RankingProfile", "PartialResult"]
