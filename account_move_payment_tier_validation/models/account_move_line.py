# Copyright 2026
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _reconcile_plan(self, reconciliation_plan):
        """No conciliar una factura con el pago bloqueado contra un pago.

        Odoo 18 solo oculta el botón «Pagar» de las facturas bloqueadas; el
        asistente de pagos desde la lista, la conciliación bancaria y la manual
        las pagan igual (Odoo 19 lo frena en el asistente). Todas pasan por
        acá. Se permite conciliar contra otras facturas o notas de crédito
        (reversión, compensación), que no son un pago.
        """
        self._payment_approval_check_reconcile(
            self._payment_approval_plan_lines(reconciliation_plan)
        )
        return super()._reconcile_plan(reconciliation_plan)

    def _payment_approval_plan_lines(self, plan):
        lines = self.browse()
        for item in plan:
            if isinstance(item, models.BaseModel):
                lines |= item
            else:
                lines |= self._payment_approval_plan_lines(item)
        return lines

    def _payment_approval_check_reconcile(self, lines):
        moves = lines.move_id
        blocked = moves.filtered(
            lambda m: m.payment_state == "blocked"
            and m.is_invoice(include_receipts=True)
        )
        if not blocked:
            return
        if not (moves - blocked).filtered(
            lambda m: not m.is_invoice(include_receipts=True)
        ):
            return
        details = []
        for move in blocked:
            if move.payment_approval_blocked and move.payment_approver_id:
                details.append(
                    self.env._(
                        "- %(move)s (aprueba: %(approver)s)",
                        move=move.display_name,
                        approver=move.payment_approver_id.name,
                    )
                )
            else:
                details.append(f"- {move.display_name}")
        raise UserError(
            self.env._(
                "No se puede pagar una factura con el pago bloqueado:\n%s",
                "\n".join(details),
            )
        )
