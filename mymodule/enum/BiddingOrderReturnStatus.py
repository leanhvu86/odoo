from enum import Enum


# status Biding
class BiddingOrderReturnStatus(Enum):
    cancel = '-1'
    not_comfirn= '0'
    has_returned_the_item = '2'
