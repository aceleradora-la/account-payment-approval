# Copyright 2026
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    payment_approver_id = fields.Many2one(
        comodel_name="res.users",
        string="Aprobador de pagos",
        company_dependent=True,
        domain=[("share", "=", False)],
        help="Usuario que debe aprobar las facturas de este proveedor antes de "
        "poder pagarlas. Se toma de la empresa comercial del contacto y puede "
        "variar por compañía.",
    )
