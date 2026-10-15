# Copyright 2026
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Facturas de proveedor - Aprobación de pago por niveles",
    "summary": "Bloquea el pago de las facturas de proveedor hasta que las apruebe "
    "el aprobador definido en el proveedor (tier validation).",
    "version": "18.0.1.2.0",
    "category": "Accounting",
    "website": "https://aceleradora.la",
    "author": "aceleradora.la",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "account",
        "base_tier_validation",
    ],
    "data": [
        "data/tier_definition_data.xml",
        "data/ir_actions_server_data.xml",
        "views/res_partner_views.xml",
        "views/account_move_views.xml",
        "views/payment_approval_menus.xml",
    ],
}
