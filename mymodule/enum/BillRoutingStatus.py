from enum import Enum


# status BillRoutingStatus
class BillRoutingStatus(Enum):
    Cancel = '-1'
    InClaim = '0'
    Shipping = '1'
    Success = '2'
    Waiting = '3'
    All = '6'
