# -*- coding: utf-8 -*-
{
    'name': "Website Long Haul",

    'summary': 'Long Haul',

    'description': '',

    'author': "AC",
    'website': "http://www.long-haul.com",

    # for the full list
    'category': 'Website/Website',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['web', 'website'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
