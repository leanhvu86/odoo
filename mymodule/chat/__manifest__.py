# -*- coding: utf-8 -*-
{
    'name': "Chat",

    'summary': """
        Mingalaba Chat""",

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
        'multiple_datepicker_widget'
    ],

    # always loaded
    'data': [
        'views/views.xml',
    ],
    'qweb': [
        "static/src/xml/tree_view_button.xml",
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
}
