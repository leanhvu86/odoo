from enum import Enum
#status cargo
class CargoStatus (Enum):
    NotBidding = '0'
    Confirmed = '1'
    Waiting = '2'