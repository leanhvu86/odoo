from enum import Enum


class AreaDistanceType(Enum):
    warehouse_to_hub = 1
    hub_to_hub = 2
    hub_to_depot = 3
    depot_to_depot = 4
    depot_to_hub = 5
    hub_to_warehouse = 6
