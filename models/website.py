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
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from lxml import etree
import urllib.parse as urlparse
import json

import logging
_logger = logging.getLogger(__name__)


class Website(models.Model):
    _inherit = 'website'

    mp_product_count = fields.Boolean(
        string="Show seller's product count on website.")
    mp_sale_count = fields.Boolean(string="Show seller's sales count on website.")
    mp_shipping_address = fields.Boolean(
        string="Show seller's shipping address on website.")
    mp_seller_since = fields.Boolean(string="Show seller since Date on website.")
    mp_seller_t_c = fields.Boolean(
        string="Show seller shop Terms & Conditions on website.")
    mp_seller_contact_btn = fields.Boolean(
        string='Show "Contact Seller" Button on website.')
    mp_seller_review = fields.Boolean(
        string='Show Seller Review on website.')
    mp_return_policy = fields.Boolean(
        string="Show seller's Retrun Policy on website.")
    mp_shipping_policy = fields.Boolean(
        string="Show Seller's Shipping Policy on website.")
    mp_recently_product = fields.Integer(
        string="# of products for recently added products menu. ", default=10)
    mp_review_load_no = fields.Integer(
        string="No. of Reviews to load", help="Set default numbers of review to show on website.", default=10)
    mp_review_auto_publish = fields.Boolean(
        string="Auto Publish", help="Publish Customer's review automatically.")
    mp_show_seller_list = fields.Boolean(
        string='Show Sellers List on website.')
    mp_show_seller_shop_list = fields.Boolean(
        string='Show Seller Shop List on website.')
    mp_show_become_a_seller = fields.Boolean("Show Become a Seller button on Account Home Page")
    mp_term_and_condition = fields.Html(string="Terms & Conditions", translate=True)
    mp_message_to_publish = fields.Text(
        string="Review feedback message", help="Message to Customer on review publish.", translate=True)
    mp_sell_page_label = fields.Char(
        string="Sell Link Label", default="Sell", translate=True)
    mp_sellers_list_label = fields.Char(
        string="Seller List Link Label", default="Sellers List", translate=True)
    mp_seller_shop_list_label = fields.Char(
        string="Seller Shop List Link Label", default="Seller Shop List", translate=True)
    mp_landing_page_banner = fields.Binary(string="Landing Page Banner")
    mp_seller_new_status_msg = fields.Text(
        string="For New Status", default="Thank you for registering with us, to enjoy the benefits of our marketplace fill all your details and request for approval.", translate=True)
    mp_seller_pending_status_msg = fields.Text(
        string="For Pending Status", default="Thank you for seller request, your request has been already sent for approval we'll process your request as soon as possible.", translate=True)
    mp_show_sell_menu_header = fields.Boolean(string="Show Sell menu in header")
    mp_show_sell_menu_footer = fields.Boolean(string="Show Sell menu in footer")
    mp_marketplace_t_c = fields.Boolean(string="Show Marketplace Terms & Conditions on website.")
    enable_marketplace = fields.Boolean("Marketplace", readonly=False)

    @api.constrains('mp_sell_page_label')
    def _check_sell_page_menu_length(self):
        """Check sell link label length"""
        for rec in self:
            if len(rec.mp_sell_page_label)>30:
                raise ValidationError(_('The length of Sell Link Label is cannot be more than 30 characters.'))

    @api.constrains('mp_sellers_list_label')
    def _check_seller_list_menu_length(self):
        """ Check seller list label length"""
        for rec in self:
            if len(rec.mp_sellers_list_label)>30:
                raise ValidationError(_('The length of Seller List Link Label is cannot be more than 30 characters.'))

    @api.model
    def get_group_mp_shop_allow(self):
        """ Get group_mp_shop_allow field """
        return self.env['ir.default'].sudo()._get('res.config.settings', 'group_mp_shop_allow')

    @api.model
    def get_mp_ajax_seller_countries(self):
        countries = self.env['res.country'].sudo().search([])
        return  countries

    def validate_mp_config_data(self, vals):
        """ Validate recently added product range and review load count"""

        recently_product = vals.get('mp_recently_product')
        if recently_product != None and (recently_product < 1 or recently_product > 20):
            raise UserError(_("Recently Added Products count should be in range 1 to 20."))
        review_load_no = vals.get('mp_review_load_no')
        if review_load_no != None and review_load_no < 1:
            raise UserError(_("Display Seller Reviews count should be more than 0."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self.validate_mp_config_data(vals)
        return super(Website, self).create(vals_list)

    def write(self, vals):
        self.validate_mp_config_data(vals)
        return super(Website, self).write(vals)
    
    def _search_with_fuzzy(self, search_type, search, limit, order, options):
        """Update searching data for seller/shop"""
        res = super()._search_with_fuzzy(search_type, search, limit, order, options)
        self.env.registry.clear_cache()
        url = request.httprequest.referrer
        url2 = request.httprequest.path

        url_parts = list(urlparse.urlparse(url))
        if url_parts and url_parts[2] and '/seller/shop/' in url_parts[2] and url2 != "/shop":
                url_handler = url_parts[2].split("/seller/shop/",1)[1]
                shop = request.env['seller.shop'].sudo().search([('url_handler','=',url_handler)], limit=1)
                seller_id = shop.seller_id and shop.seller_id.id
                if res[1]:
                    if seller_id and res[1][1].get('results'):
                        prod_list = []
                        for product in range(len(res[1][1].get('results'))):
                            product_tmpl_id = res[1][1].get('results')[product]
                            prod_obj = product_tmpl_id
                            if prod_obj and prod_obj.marketplace_seller_id and prod_obj.marketplace_seller_id.id == seller_id :
                                prod_list.append(res[1][1].get('results')[product].id)

                        templ= self.env['product.template'].browse(prod_list)
                        res[1].pop(0)
                        res[1][0].update({'results': templ})

        return res
    
    def mp_get_footer_links(self):
        '''
        Inheriting this core function to add extra links in footer.
        '''
        links = []
        if self.enable_marketplace:
            if self.env.user and not self.env.user.partner_id.seller and self.mp_show_sell_menu_footer:
                links.append({'text': _(self.mp_sell_page_label or "Sell"), 'href': '/seller'})
            if self.mp_show_seller_list:
                links.append({'text': _(self.mp_sellers_list_label or "Sellers List"), 'href': '/sellers/list'})
            if self.mp_show_seller_shop_list and self.sudo().get_group_mp_shop_allow():
                links.append({'text': _(self.mp_seller_shop_list_label or "Seller Shop List"), 'href': '/seller/shops/list'})
        return links

    def add_mp_footer_links(self):
        footer_links = []
        if self.enable_marketplace:
            footer_links = self.mp_get_footer_links()
        footer_ids = [
            'website.template_footer_contact', 'website.template_footer_headline',
            'website.footer_custom', 'website.template_footer_links',
            'website.template_footer_minimalist', 'website.template_footer_centered',
        ]
        for footer in footer_ids:
            view_id = self.env['website'].viewref(footer)
            if view_id and len(view_id) >= 1:
                view_id = view_id[0]
                arch_string = etree.fromstring(view_id.arch_db)
                elem = arch_string.xpath("//t[@t-set='configurator_footer_links']")
                if elem:
                    elem[0].attrib['t-value'] = json.dumps(footer_links if self.enable_marketplace else [])
                    view_id.write({'arch_db': etree.tostring(arch_string, pretty_print=True).decode()})
            else:
                _logger.warning(f"View ID of the footer `{footer}` not found.")

class IrQweb(models.AbstractModel):
    _inherit = "ir.qweb"

    def _prepare_frontend_environment(self, values):
        res = super()._prepare_frontend_environment(values)
        website = self.env['website'].get_current_website()
        if website:
            website.add_mp_footer_links()

        return res
