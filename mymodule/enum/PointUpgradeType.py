from enum import Enum


# status PointUpgrageType
class PointUpgradeType(Enum):
    Order = 'order'
    Routing = 'routing'
    RankingSilver = 'ranking_silver'
    RankingGold = 'ranking_gold'
    RankingDiamond = 'ranking_platinum'
