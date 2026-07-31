{
    "name": "UAH to currencies",
    "summary": "UAH parcing",
    "version": "19.0.0.0.0",
    "license":"OEEL-1",
    "depends": ["base", "accountant"],
    "author": "GeerBeen",
    "category": "Accounting",
    "description": """
    Parces UAH value.
    """,
    "data": [
        "security/ir.model.access.csv",
        "data/cron.xml",
        "wizard/fetch_history_wizard_views.xml",
        "views/res_currency_views.xml",
        
    ],
    "application": False,
}