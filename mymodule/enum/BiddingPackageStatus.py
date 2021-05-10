from enum import Enum


# status Biding
class BiddingPackageStatus(Enum):
    OverTimeBidding = '-1'
    NotBidding = '0'
    BiddingAlready = '1'
    WaitingAccept = '2'
    # ('-1', 'Quá hạn bidding'),
    # ('0', 'Chưa bidding'),
    # ('1', 'Đã được bid'),
    # ('2', 'Chờ xác nhận')

class OrderPackage(Enum):
    Express = 'express'
    Economy = 'economy'
    JustInTime = 'just_in_time'
    Normal = 'normal'
