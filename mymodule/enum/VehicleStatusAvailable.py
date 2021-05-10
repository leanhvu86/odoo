from enum import Enum
class VehicleStatusAvailable(Enum):
    Unavailable = 'unavailable'
    Available = 'available'
    Maintenance = 'maintenance'

class RoutingPlanDay(Enum):
    CancelSo = '-1'
    Unconfimred = '0'
    DriverConfirm = '1'
    Confirmed = '2'
    Cancelled = '3'
    Pending = '4'
    Draft = '5'
    SoType = True

class ProductType(Enum):
    Electronic = 'PT000001'
    FrozenProducts = 'PT000002'
    CommonGoods = 'PT000003'
    LiquidGoods = 'PT000004'
    ToxicGoods = 'PT000005'
    Fragile = 'PT000006'
    HighGoods = 'PT000007'
    HeavyGoods = 'PT000008'