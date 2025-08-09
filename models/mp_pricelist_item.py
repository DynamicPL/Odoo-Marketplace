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

from odoo import api,models, fields, _
from odoo.tools import formatLang
import logging
_logger = logging.getLogger(__name__)

class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    mp_compute_price = fields.Selection([
        ('fixed', 'Fixed Price'),
        ('percentage', 'Percentage (discount)')],index=True, default='fixed', required=True)
    common_price = fields.Char(
        string="Common Price",
        compute='_compute_common_price',
        help="Explicit rule name for this pricelist line.")

    @api.onchange('mp_compute_price')
    def _onchange_mp_compute_price(self):
        if self.mp_compute_price:
            self.compute_price = self.mp_compute_price

    def _compute_common_price(self):
        """ Compute Common price on the basis of compute_price"""
        for item in self:
            if item.compute_price == 'fixed':
                item.common_price = formatLang(
                    item.env, item.fixed_price, monetary=True, dp="Product Price", currency_obj=item.currency_id)
            elif item.compute_price == 'percentage':
                item.common_price = _("%s %% discount", item.percent_price)
            else:
                item.common_price = _("%(percentage)s %% discount and %(price)s surcharge", percentage=item.price_discount, price=item.price_surcharge)
