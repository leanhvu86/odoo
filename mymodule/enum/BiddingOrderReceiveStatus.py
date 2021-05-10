from enum import Enum


# status Biding
class BiddingOrderReceivedStatus(Enum):
    cancel = '-1'
    not_confirm = '0'
    received = '1'
