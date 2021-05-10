from enum import Enum


class StaffType(Enum):
    FLEET_MANAGER = 'FLEET_MANAGER'
    FLEET_DRIVER = 'FLEET_DRIVER'
    CUSTOMER_MANAGER = 'CUSTOMER_MANAGER'
    CUSTOMER_STOCKMAN = 'CUSTOMER_STOCKMAN'
    SHAREVAN_MANAGER = 'SHAREVAN_MANAGER'
    SHAREVAN_STOCKMAN = 'SHAREVAN_STOCKMAN'