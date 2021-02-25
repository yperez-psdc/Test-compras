# -*- coding: utf-8 -*-
{
    'name': "Purchase Requisitions Extend",
    'summary': """ """,
    'description': """ """,
    'author': "Abhay Singh Rathore",
    'website': "http://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '0.6',
    'depends': ['base','bi_material_purchase_requisitions','analytic','account_analytic_default_purchase'],
    'data': [
        # 'security/ir.model.access.csv',
        'security/purchase_requisition_security.xml',
        'views/views.xml',
    ],
}