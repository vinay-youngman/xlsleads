{
    'name' : 'Excel Leads',
    'version' : '2.0.0',
    'summary': 'Excel Leads',
    'sequence': -100,
    'description': """Generate python leads""",
    'category': 'Spreadsheet',
    'data': [
        'data/cron.xml',
        'views/views.xml',
        'views/crm_lead.xml'
    ],

    'depends': ['base', 'crm'],

    'demo': [],

    'installable': True,
    'application': True,

    'license': 'LGPL-3',
}