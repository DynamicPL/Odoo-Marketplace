# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# License URL : https://store.webkul.com/license.html/
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################


from odoo import models, fields, api, _
import datetime
# from odoo.exceptions import Warning, RedirectWarning

import logging
_logger = logging.getLogger(__name__)


class SellerPaymentWizard(models.TransientModel):
    _name = 'seller.payment.wizard'
    _description = "Seller Payment Wizard"

    @api.model
    def _get_seller(self):
        """ Get active seller id"""
        if self._context.get('active_model', False) and self._context.get('active_model') == 'res.partner':
            result = self.env['res.partner'].browse(
                self._context.get('active_id', False)).id
        else:
            partner_id = self.env.user.partner_id
            result = partner_id.id if partner_id.seller and partner_id.state == 'approved' else False
        return result

    @api.model
    def _get_payment_method(self):
        seller_id = self.env['res.partner'].browse(
            self._context.get('active_id', False)).sudo()
        if seller_id and seller_id.payment_method:
            payment_method = seller_id.payment_method.ids[0]
        else:
            try:
                payment_method_cheque_id = self.env['ir.model.data'].check_object_reference(
                    'odoo_marketplace', 'marketplace_seller_payment_method_data1')
                if payment_method_cheque_id:
                    payment_method = payment_method_cheque_id[1]
            except Exception as e:
                _logger.warning(
                    "Warning! Cash seller payment method not found (%r)", e)
                pass
        return payment_method if payment_method else False

    @api.depends('seller_id')
    def get_cashable_amount(self):
        """ Get cashable amount on the basis of seller"""
        if self._context.get('active_id', False):
            seller_obj = self.env['res.partner'].browse(
                self._context.get('active_id', False))
        else:
            seller_obj = self.seller_id
        self.cashable_amount = seller_obj.cashable_amount
        self.currency_id = seller_obj.seller_currency_id

    @api.depends('seller_id', 'credit_payment_ids')
    def _compute_amount(self):
        """ Compute amount as sum of selected credit payments for the chosen seller """
        for record in self:
            if record.seller_id:
                record.amount = round(sum(record.credit_payment_ids.filtered(
                    lambda p: p.seller_id == record.seller_id).mapped('payable_amount')), 2)
            else:
                record.amount = 0

    @api.depends('seller_id')
    def _compute_has_pending_debit(self):
        debit_records = self.env['seller.payment'].search(
            [('seller_id', '=', self.seller_id.id), ('payment_type', '=', 'dr')])
        if any(p.state in ['draft', 'requested', 'confirm'] for p in debit_records):
            self.has_pending_debit = True
        else:
            self.has_pending_debit = False

    seller_id = fields.Many2one(
        "res.partner", string="Seller", default=_get_seller, domain=[("seller", "=", True), ("state", "=", "approved")])
    amount = fields.Float(string="Payment Amount",
                          compute="_compute_amount", store=True)
    cashable_amount = fields.Float(
        string="Cashable Amount", compute="get_cashable_amount")
    payment_method_id = fields.Many2one("seller.payment.method", string="Payment Method",
                                        help="Select payment method in which you have paid payment to seller.", copy=False, default=_get_payment_method)
    memo = fields.Char(string="Memo", copy=False)
    description = fields.Text(
        string="Payment Description",  translate=True, copy=False)
    date = fields.Date(string="Date", default=fields.Date.context_today)
    currency_id = fields.Many2one(
        "res.currency", "Marketplace Currency", compute="get_cashable_amount")
    credit_payment_ids = fields.Many2many(
        "seller.payment",
        domain="[('seller_id', '=', seller_id), ('payment_type', '=', 'cr'), ('is_allowed_to_debit', '=', True)]",
        help="Select the creadit seller payment to be paid"
    )
    has_pending_debit = fields.Boolean(
        string="Has Pending Debit", compute="_compute_has_pending_debit")

    def validate_payment_request(self):
        """ Validate payment request on the basis of seller_payment_limit and next payment request limit"""
        if len(self) > 1:
            self.ensure_one()
        seller_payment_obj = self.env["seller.payment"].search(
            [("seller_id", "=", self.seller_id.id), ("payment_type", "=", "dr"), ("state", "in", ['draft', 'requested', 'confirm', 'posted'])], limit=1)
        seller_payment_limit = self.seller_id.get_seller_global_fields(
            'seller_payment_limit')
        response = {"is_valid": False, "message": ""}

        if seller_payment_obj:
            last_payment_date = seller_payment_obj.date.date()
            today_date = datetime.datetime.today().date()
            days_diff = today_date - last_payment_date

            if days_diff.days >= self.seller_id.get_seller_global_fields('next_payment_request'):
                if self.amount >= seller_payment_limit and self.amount <= self.seller_id.cashable_amount:
                    response["is_valid"] = True
                else:
                    response["message"] = _("Minimum payment amount limit is set to {seller_payment_limit}.").format(
                        seller_payment_limit=seller_payment_limit)
            else:
                response["message"] = _(
                    " Minimum gap for next payment is not followed.")
        else:
            if self.amount >= seller_payment_limit and self.amount <= self.seller_id.cashable_amount:
                response["is_valid"] = True
            else:
                response["message"] = _("Minimum payment amount limit is set to {seller_payment_limit}.").format(
                    seller_payment_limit=seller_payment_limit)

        return response

    def is_payment_request_pending(self):
        """This method checks wheather any seller payment request is pending"""
        if len(self) > 1:
            self.ensure_one()
        seller_payment_obj = self.env["seller.payment"].search([("seller_id", "=", self.seller_id.id), (
            "state", "in", ["requested", "confirm"]), ("payment_mode", "=", "seller_payment")], limit=1)
        if seller_payment_obj:
            return True
        return False

    def do_request(self):
        """ Create seller payment request"""
        msg = False
        self.ensure_one()
        if self.cashable_amount < 0:
            if self._context.get("by_seller", False):
                msg = _(
                    "You can't request for payment now, due to insufficient amount.")
            else:
                msg = _(
                    "You can't payment now to this seller, due to insufficient amount.")
        if self.amount > self.cashable_amount:
            if self._context.get("by_seller", False):
                msg = _("You can't request amount more than cashable amount.")
            else:
                msg = _("You can't pay amount more than cashable amount.")
        if round(self.amount, 2) <= 0:
            if self._context.get("by_seller", False):
                msg = _("Requested amount should be greater than 0. ")
            else:
                msg = _("Paying amount should be greater than 0. ")
        result = self.validate_payment_request()
        if not msg and result.get('is_valid', False):
            vals = {
                "date": self.date,
                "seller_id": self.seller_id.id,
                "payment_method": self.payment_method_id.id or self.seller_id.payment_method.ids[0] if self.seller_id.payment_method else False,
                "payment_mode": "seller_payment",
                "description": self.description or _("Seller requested for payment..."),
                "payment_type": "dr",
                "state": "draft",
                "memo": self.memo,
                "payable_amount": self.amount,
                "linked_payment_ids": [(6, 0, self.credit_payment_ids.ids)],
            }
            debit_seller_payment = self.env["seller.payment"].sudo().create(
                vals)

            if self.credit_payment_ids:
                for cr_payment in self.credit_payment_ids:
                    # To link the created debit to the credits
                    cr_payment.sudo().linked_payment_ids = [
                        (4, debit_seller_payment.id)]

            return {
                'name': _('Sellers Payment'),
                'view_mode': 'tree',
                'res_model': 'seller.payment',
                'type': 'ir.actions.act_window',
                'views': [(False, 'list'), (False, 'form')],
                'context': "{'search_default_on_going_payments_filter': 1, 'search_default_seller_filter': 1}",
            }
        elif not msg and result.get('message'):
            if self._context.get("by_seller", False):
                msg = _("You can't make request: {message}").format(
                    message=result.get('message', ''))
            else:
                msg = _("You can't pay to this seller: {message}").format(
                    message=result.get('message', ''))
        msg = "<p style='font-size: 15px'>" + msg + "</p>"
        return self.env["mp.wizard.message"].generated_message(msg, "Warning")

    @api.onchange('seller_id')
    def onchange_seller(self):
        if self.seller_id:
            payment_methods = self.seller_id.payment_method
            self.payment_method_id = payment_methods and payment_methods[0].id
            domain = {'domain': {'payment_method_id': [
                ('id', 'in', payment_methods.ids)]}}

            # Auto populate seller's all credit payments
            self.credit_payment_ids = self.env['seller.payment'].search([
                ('seller_id', '=', self.seller_id.id),
                ('payment_type', '=', 'cr'),
                ('is_allowed_to_debit', '=', True),
            ])
            return domain
        else:
            self.credit_payment_ids = [(5, 0, 0)]
