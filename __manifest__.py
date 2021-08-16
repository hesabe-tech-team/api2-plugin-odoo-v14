# -*- coding: utf-8 -*-

{
    'name': 'Hesabe Payment Acquirer',
    'category': 'Payment Acquirer',
    'summary': 'Payment Acquirer: Hesabe Implementation',
    'description': """

    Hesabe Payment Gateway.
    """,
    'depends': ['payment'],
    'data': [
        'views/payment_views.xml',
        'views/payment_hesabe_templates.xml',
        'data/payment_acquirer_data.xml',
    ],
    "external_dependencies": {
        "python" : ["pycryptodome"],
    },
    'post_init_hook': 'create_missing_journal_for_acquirers',
}
