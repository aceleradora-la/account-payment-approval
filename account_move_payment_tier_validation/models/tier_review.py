# Copyright 2026
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class TierReview(models.Model):
    _inherit = "tier.review"

    def action_payment_approval_validate(self):
        """Aprobar en lote, desde la lista de validaciones, los pagos de facturas."""
        moves = (
            self.env["account.move"]
            .browse(self.filtered(lambda r: r.model == "account.move").mapped("res_id"))
            .exists()
        )
        return moves.action_payment_approval_validate()
