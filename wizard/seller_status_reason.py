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
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class SellerStatusReasonWizard(models.TransientModel):
    _name = 'seller.status.reason.wizard'
    _description = "Seller Status Reason Wizard"

    reason = fields.Text(string="Comment")
    mp_reason_id = fields.Many2one("marketplace.reject.reason", string="Reason")
    mp_reason_type = fields.Selection([('product_reason', 'Product'), ('seller_profile_reason', 'Seller Profile'), ('seller_payment_reason', 'Seller Payment'), ('inventory_reason', 'Inventory')], default="seller_profile_reason")
    product_ids = fields.Many2many("product.template", string="Rejected Products")
    marketplace_stock_ids = fields.Many2many("marketplace.stock", string="Rejected Stocks")

    def do_denied(self):
        """ Check seller cashable amount and reject status """
        # for bulk product rejection
        if self.product_ids:
            for prod in self.product_ids:
                prod.rejection_reason = self.mp_reason_id.name + self.reason
                prod.reject()
                reason_title = _("Rejected Reason")
                reason_msg = f"{reason_title} : {self.mp_reason_id.name} - {self.reason if self.reason else ''}"
                prod.message_post(body=reason_msg)
            msg = "<p style='font-size: 15px'>" + _("Selected product(s) can't be rejected.") + "<p>"
            rejected_products = self.product_ids.filtered(lambda o: o.status == "rejected" and o.marketplace_seller_id)
            if rejected_products:
                p_list = (', ').join(rejected_products.mapped('name'))
                msg = "<p style='font-size: 15px'>" + _("Product(s) rejected successfully:") + "<strong>" + p_list + "</strong></p>"
            return self.env["mp.wizard.message"].generated_message(msg, _("Rejected Status"))
        # for bulk inventory rejection
        elif self.marketplace_stock_ids:
            for stock in self.marketplace_stock_ids:
                stock.reject()
                reason_title = _("Rejected Reason")
                reason_msg = f"{reason_title} : {self.mp_reason_id.name} - {self.reason if self.reason else ''}"
                stock.message_post(body=reason_msg)
            msg = "<p style='font-size: 15px'>" + _("Inventory for selected product(s) can't be reject.") + "<p>"
            rejected_inventory = self.marketplace_stock_ids.filtered(lambda o: o.state == "rejected")
            if rejected_inventory:
                prod_id = (', ').join(rejected_inventory.mapped('product_temp_id.name'))
                msg = "<p style='font-size: 15px'>" + _("Inventory request for product(s) rejected successfully:") + "<strong>" + prod_id + "</strong></p>"
            return self.env["mp.wizard.message"].generated_message(msg, _("Rejected Status"))
        # for normal rejection
        else:
            context = self._context
            active_id = context.get("active_id")
            active_obj = self.env[context.get("active_model", "")].browse(int(active_id))
            if active_obj:
                reason_title = ""
                if context.get("active_model", "") == "res.partner":
                    seller_id = active_obj
                    if seller_id.cashable_amount:
                        raise ValidationError(_('You have to clear the dues to this seller before denying.'))
                    seller_id.seller_rejection_reason = self.mp_reason_id.name
                    seller_id.deny()
                    seller_id.status_msg = self.reason
                    reason_title = _("Denied Reason")
                elif context.get("active_model", "") == "product.template":
                    product_obj = active_obj
                    product_obj.rejection_reason = self.mp_reason_id.name
                    product_obj.reject()
                    reason_title = _("Rejected Reason")
                elif context.get("active_model", "") == "product.product":
                    prod_var_obj = active_obj
                    prod_var_obj.set_to_rejected()
                    reason_title = _("Rejected Reason")
                elif context.get("active_model", "") == "seller.payment":
                    seller_pay_obj = active_obj
                    seller_pay_obj.do_cancel()
                    reason_title = _("Canceled Reason")
                elif context.get("active_model", "") == "marketplace.stock":
                    stock_obj = active_obj
                    stock_obj.reject()
                    reason_title = _("Rejected Reason")

                reason_msg = f"{reason_title} : {self.mp_reason_id.name} {self.reason if self.reason else ''}"
                active_obj.message_post(body=reason_msg)
