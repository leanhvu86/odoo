from enum import Enum


class ClickActionType(Enum):
    routing_plan_day_driver = 'com.ts.sharevandriver.TARGET_ROUTING_PLAN_DAY'
    routing_plan_day_customer = 'com.nextsolutions.sharevancustomer.TARGET_ROUTING_PLAN_DAY'
    # chưa có detail hiện có routing_plan_day thôi
    routing_plan_day_detail = 'com.ts.sharevandriver.TARGET_ROUTING_DETAIL'
    share_van_inbox = 'com.nextsolutions.sharevancustomer.TARGET_NOTIFICATION_SYSTEM'
    share_van_inbox_driver = 'com.ts.sharevandriver.TARGET_NOTIFICATION_SYSTEM'
    bill_lading = 'com.nextsolutions.sharevancustomer.TARGET_EDIT_BILL_LADING'
    bill_lading_detail = 'bill_lading_detail'
    customer_bill_lading_detail = 'com.nextsolutions.sharevancustomer.TARGET_BILL_LADDING_INFO_ACTIVITY'
    notification_driver = 'com.ts.sharevandriver.TARGET_ROUTING_DETAIL'
    driver_vehicle_check_point  ='com.ts.sharevandriver.TARGET_VEHICLE_INFO'
    driver_main_activity  ='com.ts.sharevandriver.TARGET_MAIN_ACTIVITY'
    driver_history_activity  ='com.ts.sharevandriver.TARGET_ROUTING_HISTORY'
    bill_routing_detail = 'com.nextsolutions.sharevancustomer.TARGET_BILL_ROUTING_DETAIL'
    customer_rating_driver = 'com.ts.sharevandriver.TARGET_CUSTOMER_RATED_TO_DRIVER'
    # biding enum driver
    driver_confirm_order = 'bidding_order_detail'

    # bidding enum company

    bidding_company = 'enterprise_application_bidding_order_detail'
    driver_vehicle = 'driver_application_bidding_order_detail'
    requesttime_off_type = "com.ts.sharevandriver.TARGET_WORKING_SCHEDULE"

