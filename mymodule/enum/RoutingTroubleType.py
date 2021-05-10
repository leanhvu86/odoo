from enum import Enum


class RoutingTroubleType(Enum):
    Normal = '0'
    Sos = '1'
    Retry = '2'
    Return = '3'
    PickUpFail = '4'
    WaitingConfirm = '5'
