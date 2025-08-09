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
import logging
_logger = logging.getLogger(__name__)

class MpWizardMessage(models.TransientModel):
    _name = "mp.wizard.message"
    _description = "MpWizardMessage"

    text = fields.Html(string='Message')

    def generated_message(self,message,name='Message/Summary'):
        """ Open message wizard and show message"""
        partial_id = self.create({'text':message}).id
        return {
            'name':name,
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'mp.wizard.message',
            'res_id': partial_id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
        }


class ServerActionWizard(models.TransientModel):
    _name = 'server.action.wizard'
    _description = "Server Action Wizard"

    product_ids = fields.Many2many("product.template", string="Products")

    def approve_all_products(self):
        """ Approve product if product is in pending state """
        if self.product_ids:
            pending_products = self.product_ids.filtered(lambda o: o.status == "pending" and o.marketplace_seller_id and o.marketplace_seller_id.state == "approved")
            msg = "<p style='font-size: 15px'>" + _("Selected product(s) can't be approve, only pending product(s) will get approve.") + "<p>"
            pending_products.auto_approve()
            approved_products = self.product_ids.filtered(lambda o: o.status == "approved" and o.marketplace_seller_id)
            if approved_products:
                p_list = (', ').join(approved_products.mapped('name'))
                msg = "<p style='font-size: 15px'>" + _("Product(s) approved successfully:") + "<strong>" + p_list + "</strong></p>"
            return self.env["mp.wizard.message"].generated_message(msg, _("Approved Status"))

    def reject_all_products(self):
        """ Reject selected products"""
        if self.product_ids:
            all_rejected = [True if prod.status == "rejected" else False for prod in self.product_ids]
            if all(all_rejected):
                msg = "<p style='font-size: 15px'>" + _("Selected product(s) were already rejected.") + "<p>"
                return self.env["mp.wizard.message"].generated_message(msg, _("Rejected Status"))

            non_rejected_products = self.product_ids.filtered(lambda o: o.status != "rejected" and o.marketplace_seller_id)
            partial_id = self.env["seller.status.reason.wizard"].create({
                'mp_reason_type': 'product_reason',
                'product_ids': non_rejected_products.ids
            })
            return {
                'name': _('Product Reject Bulk'),
                'type': 'ir.actions.act_window',
                'res_id': partial_id.id,
                'view_mode': 'form',
                'res_model': 'seller.status.reason.wizard',
                'target': 'new',
            }


class ServerActionWizardStock(models.TransientModel):
    _name = 'server.action.wizard.mp.stock'
    _description = "Server Action Wizard Mp Stock"

    @api.model
    def _get_marketplace_stocks(self):
        result = self.env['marketplace.stock'].browse(
            self._context['active_ids'])
        return result.ids

    marketplace_stock_ids = fields.Many2many("marketplace.stock", string="Products", default=_get_marketplace_stocks)

    def approve_marketplace_stocks(self):
        """Approve selected records in bulk"""
        if self.marketplace_stock_ids:
            msg = "<p style='font-size: 15px'>" + _("Inventory for selected product(s) can't be approve, only pending inventory request(s) will get approve.") + "<p>"
            self.marketplace_stock_ids.approve()
            approved_inventory = self.marketplace_stock_ids.filtered(lambda o: o.state == "approved")
            if approved_inventory:
                prod_id = (', ').join(approved_inventory.mapped('product_temp_id.name'))
                msg = "<p style='font-size: 15px'>" + _("Inventory request for product(s) approved successfully:") + "<strong>" + prod_id + "</strong></p>"
            return self.env["mp.wizard.message"].generated_message(msg, _("Approved Status"))


    def reject_marketplace_stocks(self):
        """Reject selected records in bulk"""
        if self.marketplace_stock_ids:
            all_rejected = [True if stock.state == "rejected" else False for stock in self.marketplace_stock_ids]
            if all(all_rejected):
                msg = "<p style='font-size: 15px'>" + _("Selected inventory(s) were already rejected.") + "<p>"
                return self.env["mp.wizard.message"].generated_message(msg, _("Rejected Status"))

            non_rejected_inventory = self.marketplace_stock_ids.filtered(lambda o: o.state != "rejected" and o.marketplace_seller_id)
            partial_id = self.env["seller.status.reason.wizard"].create({
                'mp_reason_type': 'inventory_reason',
                'marketplace_stock_ids': non_rejected_inventory.ids
            })
            return {
                'name': _('Inventory Reject Bulk'),
                'type': 'ir.actions.act_window',
                'res_id': partial_id.id,
                'view_mode': 'form',
                'res_model': 'seller.status.reason.wizard',
                'target': 'new',
            }


class SellerReviewActionWizard(models.TransientModel):
    _name = 'seller.review.action.wizard'
    _description = "Seller Review Action Wizard"

    @api.model
    def _get_reviews(self):
        """ Set default value for seller_review_ids"""
        result = self.env['seller.review'].browse(
            self._context['active_ids'])
        return result.ids

    seller_review_ids = fields.Many2many(
        "seller.review", string="Reviews", default=_get_reviews)

    def publish_all_reviews(self):
        """ Publish reviews"""
        if self.seller_review_ids:
            self.seller_review_ids.toggle_website_published()

    def unpublish_all_reviews(self):
        """ Unpublish reviews"""
        if self.seller_review_ids:
            self.seller_review_ids.toggle_website_published()

class SellerRecommendationActionWizard(models.TransientModel):
    _name = 'seller.recommendation.action.wizard'
    _description = "Seller Recommendation Action Wizard"

    @api.model
    def _get_recommendations(self):
        result = self.env['seller.review'].browse(
            self._context['active_ids'])
        return result.ids

    seller_recommendation_ids = fields.Many2many("seller.recommendation", "wizard_id", "recommendation_id", string="Recommendations", default=_get_recommendations)

    def publish_all_recommendations(self):
        """Publish recommendations"""
        self.ensure_one()
        if self.seller_recommendation_ids:
            self.seller_recommendation_ids.write({"state" : 'pub'})

    def unpublish_all_recommendations(self):
        """Unpublish recommendations"""
        self.ensure_one()
        if self.seller_recommendation_ids:
            self.seller_recommendation_ids.write({"state" : 'unpub'})
