# -*- coding: utf-8 -*-
{
    'name': "Website Order Customer",

    'summary': 'Dat don',

    'description': 'hay dat don hang cua ban',

    'author': "AC",
    'website': "http://www.order-customer.com",

    # for the full list
    'category': 'Website/Website',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'website', 'web_google_maps'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/order_template.xml',
        'views/search_views.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
