from enum import Enum


class VehicleStateStatus(Enum):
    Waiting = 'WAITING'
    Available = 'AVAILABLE'
    Ordered = 'ORDERED'
    Downgraded = 'DOWNGRADED'
    Shipping = 'SHIPPING'
    Maintenance = 'MAINTENANCE'
    WAITING = 'Waiting'
    AVAILABLE = 'Available'
    ORDERED = 'Ordered'
    DOWNGRADED = 'Downgraded'
    SHIPPING = 'Shipping'
    MAINTENANCE = 'Maintenance'
    CONFIRMTAKE = 'ConfirmTake'
    CONFIRMRETURN = 'ConfirmReturn'

class VehicleEquipmentPart(Enum):
    IOT = '0'
    VEHICLE = '1'

class CompanyName(Enum):
    MFUNCTIONS = 'mFunctions'
