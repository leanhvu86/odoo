from enum import Enum


# status PackageCargoStatus
class PackageCargoStatus(Enum):
    NotReady = '0'
    UnPacked = '1'
    Packed = '2'
