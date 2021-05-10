from enum import Enum


# status Biding
class BiddingStatus(Enum):
    Cancel = '-1'
    NotConfirm = '0'
    Received = '1'
    Returned = '2'
