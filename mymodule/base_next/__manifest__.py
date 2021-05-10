# -*- coding: utf-8 -*-
{
    'name': "Base Next Solutions",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Next Solutions",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/base_next_security.xml',
        'views/vendor_sequence_views.xml',
        'views/base_sequence.xml',
        'views/vendor_views.xml',
        'views/fleet_views.xml',
        'views/res_employee_seq.xml',
        'views/warehouse_view.xml',
        'views/notification_views.xml',
        'views/ir_config_parameter_data.xml',
        'views/asset_widget.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
    "qweb": [
        'static/src/xml/widget.xml',
    ],
}
