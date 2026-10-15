# Copyright 2026
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class TierDefinition(models.Model):
    _inherit = "tier.definition"

    @api.model
    def _get_tier_validation_model_names(self):
        result = super()._get_tier_validation_model_names()
        if "account.move" not in result:
            result.append("account.move")
        return result
