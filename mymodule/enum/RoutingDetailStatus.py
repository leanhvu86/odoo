from enum import Enum


class RoutingDetailStatus(Enum):
    Unconfimred = '0'
    Driver_confirm = '1'
    Done = '2'
    Cancel = '3'
    WaitingApprove = '4'
    AssignCarWorking = '5'
    # đối với routing là trạng thái dự thảo = 5
    ManagerApprovedCar = '6'
