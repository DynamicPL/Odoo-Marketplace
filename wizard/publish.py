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
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PublishActionDetails(models.TransientModel):
    _name = "publish.action.details"
    _description = "Show Stats Details after mass publish"


    product_ids = fields.Many2many("product.template", string="Products")

    def publish_all_products(self):
        if self.product_ids:
            approved_products = self.product_ids.filtered(lambda o: o.status == "approved" and o.marketplace_seller_id and o.marketplace_seller_id.state == "approved")
            msg = "<p style='font-size: 15px'> " + _("Selected product(s) can't be publish, only approved product(s) will get publish") +"<p>"
            approved_products.auto_publish()
            approved_products = self.product_ids.filtered(lambda o: o.status == "approved" and o.marketplace_seller_id)
            if approved_products:
                p_list = (', ').join(approved_products.mapped('name'))
                msg = "<p style='font-size: 15px'>" + _("Product(s) published successfully:") + "<strong>" + p_list + "</strong></p>"
            return self.env["mp.wizard.message"].generated_message(msg, _("Published Status"))
