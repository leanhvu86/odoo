from enum import Enum


# type Notification
class NotificationType(Enum):
    RoutingMessage = 'routing'
    OrderMessage = 'order'
    BiddingOrder = 'bidding_order'
    BiddingCompany = 'bidding_company'
    BiddingVehicle = 'bidding_vehicle'
    SystemMessage = 'system'
    SOS = 'sos'
