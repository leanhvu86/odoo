from enum import Enum


class ReasonType(Enum):
    CustomerNotFound = '1'
    OrderPackageChange = '2'
    CustomerCancel = '3'
    SystemNotSatisfy = '4'

