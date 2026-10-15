# Copyright 2026
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError

# Campos que no se pueden cambiar mientras el pago está en aprobación (ni
# después de aprobado): cambiarlos invalidaría lo que se aprobó. Para tocarlos
# hay que reiniciar la validación o volver la factura a borrador.
_PROTECTED_FIELDS = frozenset(
    {
        "partner_id",
        "partner_bank_id",
        "payment_approver_id",
        "payment_reference",
        "currency_id",
        "invoice_payment_term_id",
        "invoice_date_due",
        "line_ids",
        "invoice_line_ids",
    }
)


class AccountMove(models.Model):
    """Aprobación por niveles del pago (no de la confirmación) de la factura.

    `base_tier_validation` está pensado para frenar una transición de estado.
    Acá la factura se confirma normalmente (entra al Libro IVA en su fecha
    contable) y la validación se pide al confirmar: mientras no esté aprobada,
    el pago queda bloqueado con el bloqueo nativo de Odoo (`payment_state =
    'blocked'`). Al aprobarse, se desbloquea solo.

    Por eso `_state_from` es `posted` (las revisiones viven sobre la factura
    confirmada) y `_state_to` queda vacío: ningún cambio de `state` exige la
    validación; lo que se frena es la conciliación con un pago
    (ver `account.move.line._reconcile_plan`).
    """

    _name = "account.move"
    _inherit = ["account.move", "tier.validation"]
    _state_from = ["posted"]
    _state_to = []

    _tier_validation_manual_config = False

    payment_approver_id = fields.Many2one(
        comodel_name="res.users",
        string="Aprobador del pago",
        compute="_compute_payment_approver_id",
        store=True,
        readonly=False,
        precompute=True,
        tracking=True,
        domain=[("share", "=", False)],
        help="Se completa con el aprobador de pagos del proveedor. Mientras no "
        "apruebe, la factura no se puede pagar.",
    )
    payment_approval_blocked = fields.Boolean(
        string="Pago bloqueado por aprobación",
        copy=False,
        readonly=True,
        help="El bloqueo de pago lo puso la aprobación (no un usuario a mano): "
        "se levanta solo cuando se aprueba.",
    )

    @api.depends("partner_id", "company_id")
    def _compute_payment_approver_id(self):
        for move in self:
            partner = move.partner_id.commercial_partner_id.with_company(
                move.company_id
            )
            move.payment_approver_id = partner.payment_approver_id

    # ------------------------------------------------------------------
    # Pedido de aprobación y bloqueo
    # ------------------------------------------------------------------

    def _post(self, soft=True):
        self._payment_approval_fill_approver()
        posted = super()._post(soft=soft)
        posted._payment_approval_request()
        return posted

    def _payment_approval_fill_approver(self):
        """Tomar el aprobador del proveedor al confirmar, si la factura no tiene.

        El aprobador se calcula al elegir el proveedor: un borrador cargado
        antes de definirle aprobador al proveedor quedaría sin aprobación.
        """
        for move in self.filtered(
            lambda m: not m.payment_approver_id
            and m.is_purchase_document(include_receipts=True)
        ):
            partner = move.partner_id.commercial_partner_id.with_company(
                move.company_id
            )
            if partner.payment_approver_id:
                move.payment_approver_id = partner.payment_approver_id

    def _payment_approval_request(self):
        """Pedir la aprobación de las facturas recién confirmadas que la requieren."""
        if not self.env["tier.definition"].search_count(
            [("model", "=", self._name)], limit=1
        ):
            return
        to_request = self.filtered(
            lambda m: m.state == "posted"
            and m.is_invoice(include_receipts=True)
            and not m.review_ids
            and m.need_validation
        )
        if to_request:
            to_request.request_validation()

    def request_validation(self):
        reviews = super().request_validation()
        self._payment_approval_block()
        return reviews

    def _payment_approval_pending(self):
        """La aprobación está abierta o rechazada, o se reinició y falta volver
        a pedirla: en esos casos el pago no se puede desbloquear a mano."""
        self.ensure_one()
        if self.validation_status in ("waiting", "pending", "rejected"):
            return True
        return bool(
            self.payment_approval_blocked
            and not self.review_ids
            and self.need_validation
        )

    def _payment_approval_block(self):
        to_block = self.filtered(
            lambda m: m.validation_status in ("waiting", "pending", "rejected")
            and m.payment_state in ("not_paid", "partial")
        )
        if to_block:
            to_block.write(
                {"payment_state": "blocked", "payment_approval_blocked": True}
            )

    def _payment_approval_unblock(self):
        """Levantar el bloqueo puesto por la aprobación.

        Lo hace el sistema como consecuencia de una aprobación válida: el
        aprobador puede no tener permiso de escritura sobre facturas.
        """
        to_unblock = self.sudo().filtered("payment_approval_blocked")
        if not to_unblock:
            return
        blocked = to_unblock.filtered(lambda m: m.payment_state == "blocked")
        to_unblock.write({"payment_approval_blocked": False})
        if blocked:
            # Igual que action_toggle_block_payment: liberar y recalcular.
            blocked.write({"payment_state": "not_paid"})
            self.env.add_to_compute(self._fields["payment_state"], blocked)

    def _validate_tier(self, tiers=False):
        res = super()._validate_tier(tiers=tiers)
        if self.validation_status == "validated":
            self._payment_approval_unblock()
        return res

    def action_toggle_block_payment(self):
        for move in self:
            if move.payment_state == "blocked" and move._payment_approval_pending():
                raise UserError(
                    self.env._(
                        "El pago de %(move)s está pendiente de aprobación de "
                        "%(approver)s: se desbloquea solo al aprobarse.",
                        move=move.display_name,
                        approver=move.payment_approver_id.name or "-",
                    )
                )
        res = super().action_toggle_block_payment()
        self.filtered(lambda m: m.payment_state != "blocked").write(
            {"payment_approval_blocked": False}
        )
        return res

    def restart_validation(self):
        """Reiniciar vuelve a pedir la aprobación en el acto.

        Sin esto la factura quedaba con el pago bloqueado y sin nadie que la
        apruebe hasta que alguien tocara «Solicitar validación». Si ya estaba
        aprobada, se vuelve a bloquear. Solo para administradores de
        contabilidad: reiniciar descarta lo aprobado o rechazado.
        """
        if not self.env.su and not self.env.user.has_group(
            "account.group_account_manager"
        ):
            raise UserError(
                self.env._(
                    "Solo un administrador de contabilidad puede reiniciar la "
                    "aprobación del pago."
                )
            )
        restarted = self.filtered("review_ids")
        res = super().restart_validation()
        restarted._payment_approval_request()
        return res

    def _add_tier_validation_buttons(self, node, params):
        # Los botones se inyectan después de que Odoo filtra los `groups` de la
        # vista: el atributo no tendría efecto, se saca el botón a mano.
        new_node = super()._add_tier_validation_buttons(node, params)
        if not self.env.user.has_group("account.group_account_manager"):
            for button in new_node.xpath("//button[@name='restart_validation']"):
                button.getparent().remove(button)
        return new_node

    def button_draft(self):
        res = super().button_draft()
        # Las revisiones se borran al pasar a borrador (_allow_to_remove_reviews);
        # al volver a confirmar se pide la aprobación de nuevo.
        self._payment_approval_unblock()
        return res

    # ------------------------------------------------------------------
    # Ajustes al mixin de tier validation
    # ------------------------------------------------------------------

    def _allow_to_remove_reviews(self, values):
        if values.get(self._state_field) == "draft":
            return True
        return super()._allow_to_remove_reviews(values)

    def _check_allow_write_under_validation(self, vals):
        """Una factura confirmada se sigue escribiendo (conciliaciones, envío,
        adjuntos, campos de otros módulos): solo se frenan los campos que
        cambian qué se paga y a quién."""
        if not _PROTECTED_FIELDS.intersection(vals):
            return True
        return super()._check_allow_write_under_validation(vals)

    def _get_tier_validation_readonly_domain(self):
        # El mixin pondría en solo lectura todo el formulario mientras haya
        # revisiones; acá el control es del lado servidor y solo sobre
        # _PROTECTED_FIELDS.
        return "False"

    def _get_to_validate_message_name(self):
        if self.move_type in ("in_invoice", "in_receipt"):
            return self.env._("pago de factura")
        return super()._get_to_validate_message_name()

    # ------------------------------------------------------------------
    # Aprobación masiva
    # ------------------------------------------------------------------

    def action_payment_approval_validate(self):
        """Aprobar en lote las facturas seleccionadas que el usuario puede aprobar.

        Se omiten las que no le corresponden (o no le toca todavía) y las que
        exigen comentario: esas se aprueban de a una desde el formulario.
        """
        approved = self.browse()
        need_comment = self.browse()
        for move in self:
            if not move.can_review:
                continue
            if move.has_comment:
                need_comment |= move
                continue
            move.validate_tier()
            approved |= move
        skipped = self - approved - need_comment
        lines = [self.env._("Aprobadas: %s.", len(approved))]
        if need_comment:
            lines.append(
                self.env._(
                    "Requieren comentario (aprobar desde la factura): %s.",
                    ", ".join(need_comment.mapped("display_name")),
                )
            )
        if skipped:
            lines.append(
                self.env._("Sin aprobación pendiente suya: %s.", len(skipped))
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("Aprobación de pagos"),
                "message": " ".join(lines),
                "type": "success" if approved else "warning",
                "sticky": bool(need_comment),
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }
