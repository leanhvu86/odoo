# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Fleet',
    'version': '0.1',
    'sequence': 165,
    'category': 'Human Resources/Fleet',
    'website': 'https://www.odoo.com/page/fleet',
    'summary': 'Manage your fleet and track car costs',
    'description': """
Vehicle, leasing, insurances, cost
==================================
With this module, Odoo helps you managing all your vehicles, the
contracts associated to those vehicle as well as services, fuel log
entries, costs and many other features necessary to the management 
of your fleet of vehicle(s)

Main Features
-------------
* Add vehicles to your fleet
* Manage contracts for vehicles
* Reminder when a contract reach its expiration date
* Add services, fuel log entry, odometer values for all vehicles
* Show all costs associated to a vehicle or to a type of service
* Analysis graph for costs
""",
    'depends': [
        'base',
        'mail',
        'web_google_maps',
        'base_next'
    ],
    'data': [
        'security/fleet_security.xml',
        'security/ir.model.access.csv',
        'views/fleet_vehicle_model_views.xml',
        'views/fleet_vehicle_views.xml',
        'views/parking_point_sequence.xml',
        'views/fleet_vehicle_cost_views.xml',
        'views/fleet_ir_model_fields.xml',
        'views/fleet_management_views.xml',
        'views/fleet_management_driver_temp_views.xml',
        'views/fleet_board_view.xml',
        'views/fleet_management_vehicle_temp_views.xml',
        'views/fleet_vehicle_status_view.xml',
        'views/mail_activity_views.xml',
        'views/driver_sequence.xml',
        'views/res_config_settings_views.xml',
        'views/fleet_app_param_views.xml',
        'views/fleet_parking_point_view.xml',
        'views/fleet_vehicle_bill_lading_view.xml',
        'views/fleet_vehicle_driver_views.xml',
        'views/maintenance/maintenance_view.xml',
        'views/fleet_driver_views.xml',
        'data/fleet_cars_data.xml',
        'data/fleet_data.xml',
        'views/tc_positions_views.xml',
        'data/mail_data.xml',
        'views/request_time_off.xml',
    ],

    'demo': ['data/fleet_demo.xml', 'data/automate_action_data.xml'],

    'installable': True,
    'application': True,
}
