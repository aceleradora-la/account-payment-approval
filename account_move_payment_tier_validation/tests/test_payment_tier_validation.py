# Copyright 2026
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPaymentTierValidation(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.approver = new_test_user(
            cls.env,
            login="payment_approver",
            groups="base.group_user,account.group_account_readonly",
            company_id=cls.env.company.id,
        )
        cls.other_user = new_test_user(
            cls.env,
            login="payment_other",
            groups="base.group_user,account.group_account_readonly",
            company_id=cls.env.company.id,
        )
        cls.partner_a.payment_approver_id = cls.approver

    def _bill(self, partner=None, post=True):
        return self.init_invoice(
            "in_invoice",
            partner=partner or self.partner_a,
            amounts=[100.0],
            post=post,
        )

    def _pay(self, bills):
        return (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=bills.ids)
            .create({})
            ._create_payments()
        )

    def test_post_blocks_payment(self):
        bill = self._bill()
        self.assertEqual(bill.state, "posted")
        self.assertEqual(bill.payment_approver_id, self.approver)
        self.assertEqual(bill.validation_status, "pending")
        self.assertEqual(bill.payment_state, "blocked")
        self.assertTrue(bill.payment_approval_blocked)
        with self.assertRaises(UserError):
            self._pay(bill)

    def test_approval_unblocks_and_allows_payment(self):
        bill = self._bill()
        bill.with_user(self.approver).validate_tier()
        self.assertEqual(bill.validation_status, "validated")
        self.assertEqual(bill.payment_state, "not_paid")
        self.assertFalse(bill.payment_approval_blocked)
        self._pay(bill)
        self.assertIn(bill.payment_state, ("paid", "in_payment"))

    def test_other_user_cannot_approve(self):
        bill = self._bill()
        self.assertFalse(bill.with_user(self.other_user).can_review)
        bill.with_user(self.other_user).action_payment_approval_validate()
        self.assertEqual(bill.payment_state, "blocked")

    def test_manual_unblock_refused_while_pending(self):
        bill = self._bill()
        with self.assertRaises(UserError):
            bill.action_toggle_block_payment()
        bill.restart_validation()
        with self.assertRaises(UserError):
            bill.action_toggle_block_payment()

    def test_rejected_stays_blocked(self):
        bill = self._bill()
        bill.with_user(self.approver).reject_tier()
        self.assertEqual(bill.validation_status, "rejected")
        self.assertEqual(bill.payment_state, "blocked")
        with self.assertRaises(UserError):
            self._pay(bill)

    def test_bulk_approval(self):
        bills = self._bill() + self._bill()
        bills.with_user(self.approver).action_payment_approval_validate()
        self.assertEqual(set(bills.mapped("validation_status")), {"validated"})
        self.assertEqual(set(bills.mapped("payment_state")), {"not_paid"})

    def test_bulk_approval_from_reviews(self):
        bills = self._bill() + self._bill()
        bills.review_ids.with_user(self.approver).action_payment_approval_validate()
        self.assertEqual(set(bills.mapped("validation_status")), {"validated"})

    def test_partner_without_approver_not_blocked(self):
        bill = self._bill(partner=self.partner_b)
        self.assertFalse(bill.review_ids)
        self.assertEqual(bill.payment_state, "not_paid")
        self._pay(bill)

    def test_draft_resets_approval(self):
        bill = self._bill()
        bill.button_draft()
        self.assertFalse(bill.review_ids)
        self.assertEqual(bill.payment_state, "not_paid")
        self.assertFalse(bill.payment_approval_blocked)
        bill.action_post()
        self.assertEqual(bill.validation_status, "pending")
        self.assertEqual(bill.payment_state, "blocked")

    def test_protected_fields_locked_under_validation(self):
        bill = self._bill()
        with self.assertRaises(UserError):
            bill.payment_approver_id = self.other_user
        # Lo que no cambia qué se paga ni a quién se puede seguir escribiendo.
        bill.narration = "Nota"

    def test_credit_note_can_settle_blocked_bill(self):
        bill = self._bill()
        reversal = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=bill.ids)
            .create({"journal_id": bill.journal_id.id, "date": bill.date})
        )
        reversal.refund_moves()
        refund = bill.reversal_move_ids
        if refund.state == "draft":
            refund.action_post()
        payable = (bill + refund).line_ids.filtered(
            lambda line: line.account_type == "liability_payable"
            and not line.reconciled
        )
        if payable:
            payable.reconcile()
        self.assertEqual(bill.amount_residual, 0.0)

    def test_manual_block_is_enforced(self):
        bill = self._bill(partner=self.partner_b)
        bill.action_toggle_block_payment()
        self.assertEqual(bill.payment_state, "blocked")
        self.assertFalse(bill.payment_approval_blocked)
        with self.assertRaises(UserError):
            self._pay(bill)
        bill.action_toggle_block_payment()
        self._pay(bill)
