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


class SellerRejectReason(models.Model):
    _name = 'marketplace.reject.reason'
    _description = "Seller Reject Reasons"

    name = fields.Char(string="Reason Name")
    reason_type = fields.Selection([('product_reason', 'Product'), ('seller_profile_reason', 'Seller Profile'), ('seller_payment_reason', 'Seller Payment'), ('inventory_reason', 'Inventory')])