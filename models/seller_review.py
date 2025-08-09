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
from odoo.exceptions import UserError, ValidationError
from random import randint
import logging
_logger = logging.getLogger(__name__)

color_count = 10
colors_dict = {0: "#EF5350", 1: "#4CAF50", 2: "#7E57C2", 3: "#FF7043", 4: "#FF4081", 5: "#5fcbef", 6: "#63d6d1", 7: "#fba565", 8: "#8064fa", 9: "#daab85", 10: "#e06a6e",
               11: "#EC407A", 12: "#AB47BC", 13: "#42A5F5", 14: "#5C6BC0", 15: "#DCE775", 16: "#66BB6A", 17: "#9CCC65", 18: "#40C4FF", 19: "#8D6E63", 20: "#B0BEC5", }


class SellerReview(models.Model):
    _name = "seller.review"
    _rec_name = 'title'
    _description = "Seller Review"
    _inherit = ['website.published.mixin','mail.thread']

    _order = "is_published desc, create_date desc"
    _mail_post_access = 'read'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('rating', False):
                if vals['rating'] <= 0:
                    raise UserError('Warning Rating must be more than zero')
                if vals['rating'] > 5:
                    raise UserError('Warning Rating can not be more than 5')
        return super(SellerReview, self).create(vals_list)

    def write(self, vals):
        if vals.get('rating', False):
            if vals['rating'] <= 0:
                raise UserError('Warning Rating must be more than zero')
            if vals['rating'] > 5:
                raise UserError('Warning Rating can not be more than 5')
        return super(SellerReview, self).write(vals)

    @api.model
    def _get_mail(self):
        """ Return user mail"""
        res_obj = self.env['res.users'].browse(self._uid)
        email = res_obj.email
        return email

    @api.model
    def _get_image(self):
        """ Return user image"""
        res_obj = self.env['res.users'].browse(self._uid)
        image = res_obj.image
        return image

    @api.depends("review_help_ids")
    def _set_total_helpful(self):
        """Compute count for helpful reviews """
        for obj in self:
            review_help_ids = obj.env["review.help"].search(
                [('review_help', '=', "yes"), ('seller_review_id', '=', obj.id)])
            obj.helpful = len(review_help_ids)

    def _get_rating(self):
        """Compute ratings"""
        for obj in self:
            obj.rating2 = obj.rating

    @api.depends("review_help_ids")
    def _set_total_not_helpful(self):
        """ Compute count for not helpful reviews"""
        for obj in self:
            review_help_ids = obj.env["review.help"].search(
                [('review_help', '=', "no"), ('seller_review_id', '=', obj.id)])
            obj.not_helpful = len(review_help_ids)

    def _set_total_votes(self):
        """ Compute total votes"""
        for obj in self:
            review_help_ids = obj.env["review.help"].search(
                [('seller_review_id', '=', obj.id)])
            obj.total_votes = len(review_help_ids)

    @api.depends('website_published')
    def _get_value_website_published(self):
        """ Compute publish/unpublish status"""
        for record in self:
            if record.website_published:
                record.state = 'pub'
            else:
                record.state = 'unpub'

    @api.model
    def _get_default_color(self):
        color_index = randint(0, 20)
        return colors_dict[color_index]

    title = fields.Char(string='Title', translate=True, required=True)
    active = fields.Boolean(string="Active", default=True)
    msg = fields.Text(string='Message', translate=True, copy=False)
    rating = fields.Integer(string='Rating', default=1, copy=False)
    rating2 = fields.Integer(compute="_get_rating", string="Rating2", copy=False)
    email = fields.Char(string='Email', default=_get_mail, copy=False)
    marketplace_seller_id = fields.Many2one('res.partner', string='Seller', domain=[('seller', '=', True),('state', '=', 'approved')])
    create_date = fields.Datetime(string='Created Date')
    helpful = fields.Integer(compute='_set_total_helpful',
                             string='Helpful', store=True)
    not_helpful = fields.Integer(
        compute='_set_total_not_helpful', string='Not Helpful', store=True)
    total_votes = fields.Integer(
        compute='_set_total_votes', string='Lotal Votes')
    review_help_ids = fields.One2many(
        'review.help', 'seller_review_id', string="Helpful/Not Helpful")
    state = fields.Selection([('pub', 'Published'), ('unpub', 'Unpublished')],
                             compute='_get_value_website_published', store=True, copy=False)
    partner_id = fields.Many2one(
        "res.partner", string="Customer", default=lambda self: self.env.user.partner_id)
    color = fields.Char(string="Color", default=_get_default_color)
    website_message_ids = fields.One2many(
        'mail.message', 'res_id',
        domain=lambda self: ['&', ('model', '=', self._name), ('message_type', '=', 'comment')],
        string='Website Seller Review Comments',
    )

    @api.model
    def _read_group_fill_results( self, domain, groupby, remaining_groupbys,
        aggregated_fields, read_group_order=None):

        if groupby == 'state':
            for result in aggregated_fields:
                state = result['state']
                if state in ['pub']:
                    result['__fold'] = True
        return super(SellerReview, self)._read_group_fill_results(domain, groupby, remaining_groupbys,
            aggregated_fields, read_group_order)

    #Onchange function
    @api.onchange("partner_id")
    def on_change_customer(self):
        """ Change email on changing seller"""
        if self.partner_id:
            self.email = self.partner_id.email

    def toggle_website_published(self):
        """ Inverse the value of the field ``website_published`` on the records in ``self``. """
        for record in self:
            record.website_published = not record.website_published

    def action_open_seller_rating(self, partnerId=None, **post):
        name = _("Seller Ratings")
        res_model = "seller.review"
        user = self.env.user
        domain = [("state", "=", "pub")]
        filter_data = post.get("params")

        ctx = {}
        if filter_data:
            domain += (self.env["marketplace.dashboard"].get_filtered_domain(filter_data) or [])
            additional_ctx = self.env['marketplace.dashboard'].prepare_filter_context(filter_data)
            ctx.update(additional_ctx)
            context = ctx
        else:
            context = {"search_default_marketplace_seller_id": partnerId}

        if not user._is_admin():
            domain += [("marketplace_seller_id", "=", user.partner_id.id)]
        action = {
            "name": name,
            "type": "ir.actions.act_window",
            "view_mode": "kanban",
            "views": [
                (self.env.ref("odoo_marketplace.mp_seller_review_kanban_view_webkul").id, "kanban",),
                (self.env.ref("odoo_marketplace.mp_seller_review_tree_view_webkul").id,"tree",),
                (self.env.ref("odoo_marketplace.mp_seller_review_form_view_webkul2").id,"form",),
            ],
            "res_model": res_model,
            "domain": domain,
            "target": "current",
            "context": context,
        }
        return action
    
    
class ReviewHelp(models.Model):
    _name = "review.help"
    _description = "Seller review help"
    _order = "create_date DESC"

    customer_id = fields.Many2one(
        'res.partner', string='Customer', required=True, default=lambda self: self.env.user.partner_id, domain="[('customer_rank','>', 0)]")
    review_help = fields.Selection(
        [("yes", "Helpful"), ("no", "Not Helpful")], string="Was this review helpful?", required=True)
    seller_review_id = fields.Many2one("seller.review")

    @api.constrains('customer_id', 'seller_review_id')
    def _single_user_per_product(self):
        """ User can vote once for a product"""
        for obj in self:
            x = self.search([('customer_id', '=', obj.customer_id.id),
                            ('seller_review_id', '=', obj.seller_review_id.id)])
            if len(x) > 1:
                raise ValidationError(_('Error ! This user have already voted for Helpful/not Helpful.'))

class SellerRecommendation(models.Model):
    _name = "seller.recommendation"
    _description = "Seller Recommendation"
    _rec_name = "customer_id"

    customer_id = fields.Many2one(
        'res.partner', string='Customer', required=True, default=lambda self: self.env.user.partner_id, domain="[('customer_rank','>', 0)]")
    recommend_state = fields.Selection(
        [('yes', 'YES'), ('no', 'NO')], string="Recommend", default="no")
    seller_id = fields.Many2one(
        "res.partner", string="Recommended Seller", required=True, domain=[('seller', '=', True)])
    state = fields.Selection(
        [('pub', 'Published'), ('unpub', 'Unpublished')], default="unpub")
    
    def toggle_website_published(self):
        for record in self:
            if record.state == "pub":
                record.state = "unpub"
            else:
                record.state = "pub"

    @api.model
    def _read_group_fill_results( self, domain, groupby, remaining_groupbys,
        aggregated_fields, read_group_order=None):

        if groupby == 'recommend_state':
            for result in aggregated_fields:
                state = result['recommend_state']
                if state in ['yes']:
                    result['__fold'] = True
        return super(SellerRecommendation, self)._read_group_fill_results(domain, groupby, remaining_groupbys,
            aggregated_fields, read_group_order)

    @api.constrains('customer_id', 'seller_id')
    def _single_user_per_seller(self):
        """ User can give one time recomendation for a seller"""
        x = self.search([('customer_id', '=', self.customer_id.id),
                         ('seller_id', '=', self.seller_id.id)])
        if len(x) > 1:
            raise ValidationError(_('Error ! This user have already voted for recommendation.'))

    def publish_unpublish_btn(self):
        for rec in self:
            if rec.state == "pub":
                rec.state = "unpub"
            else:
                rec.state = "pub"
