# -*- coding: utf-8 -*-
{
    'name': "Dynamic logistic platform",

    'summary': """
        Intelligence Logistic Business """,

    'description': """
        Long description of module's purpose
    """,

    'author': "Next Solutions",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources/Share Van Order',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'web_google_maps',
        'base_next',
        'multiple_datepicker_widget',
    ],

    # always loaded
    'data': [
        'security/share_van_order_security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/product_type_sequence.xml',
        'views/bill_lading_views.xml',
        'views/product_sequence.xml',
        'views/bidding_package_views.xml',
        'views/bill_lading_sequence.xml',
        'views/bidding_order_views.xml',
        'views/cargo_price_views.xml',
        'views/bill_lading_detail_sequence.xml',
        'views/bill_cycle_sequence.xml',
        'data/sequence.xml',
        'views/warehouse_sequence.xml',
        'views/res_config_settings_views.xml',
        'views/templates.xml',
        'views/zone_views.xml',
        'views/company_views.xml',
        'views/service_distance_fee_views.xml',
        'views/service_weight_fee_views.xml',
        'views/common_views.xml',
        'views/measure_unit_views.xml',
        'views/depot_view.xml',
        'views/driver_license_views.xml',
        'views/tonnage_vehicle_views.xml',
        'views/driver_sos_views.xml',
        'views/driver_rating_views.xml',
        'views/rating_badges_sequence.xml',
        'views/fleet_bidding_driver_views.xml',
        'views/fleet_bidding_vehicle_views.xml',
        'views/res_company_seq.xml',
        'views/hub_view.xml',
        'views/bidding_notification_views.xml',
        'views/bidding_order_returns_views.xml',
        'views/bidding_order_receive_views.xml',
        'views/cargo_sequence_views.xml',
        'views/bidding_order_return_sequence_views.xml',
        'views/bidding_order_recieve_sequence_views.xml',
        'views/bidding_package_sequence_views.xml',
        'views/bidding_vehicle_views.xml',
        'views/size_standard_views.xml',
        'views/size_standard_sequence.xml',
        'views/bidding_sequence.xml',
        'views/tree_view_asset.xml',
        'views/depot_goods_views.xml',
    ],
    'qweb': [
        "static/src/xml/tree_view_button.xml",
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
        'demo/staff_type_demo.xml'
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
}
