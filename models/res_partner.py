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

from odoo import SUPERUSER_ID, models, fields, api, _
from odoo.exceptions import MissingError, ValidationError
import decimal,re
from odoo.exceptions import UserError
import logging
from datetime import date
_logger = logging.getLogger(__name__)

manager_fields = []

class ResPartner(models.Model):
    _inherit = ['res.partner', 'website.seo.metadata']
    _name = 'res.partner'

    # Default methods

    STATES = [('new', 'New'), ('pending', 'Pending for Approval'), ('approved', 'Approved'), (
        'denied', 'Denied')]

    # Default methods


    @api.model
    def get_mention_suggestions(self, search, limit=8):
        """Suggestion list restriction for Sellers"""
        if self.env.user.check_user_is_draft_or_approved_seller():
           return []
        return super(ResPartner,self).get_mention_suggestions(search=search,limit=limit)

    @api.model
    def _set_payment_method(self):
        """ Set seller payment method"""
        return_list = []
        payment_method_cheque_id = None
        try:
            payment_method_cheque_id = self.env['ir.model.data'].sudo().check_object_reference(
                'odoo_marketplace', 'marketplace_seller_payment_method_data2')
            if payment_method_cheque_id:
                return_list.append(payment_method_cheque_id[1])
        except Exception as e:
            _logger.warning("Warning! cheque seller payment method not found~%r",e)
            pass
        try:
            payment_method_bank_transfer_id = self.env['ir.model.data'].sudo().check_object_reference(
                'odoo_marketplace', 'marketplace_seller_payment_method_data5')
            if payment_method_cheque_id:
                return_list.append(payment_method_bank_transfer_id[1])
        except Exception as e:
            _logger.warning("Warning! Bank Transfer seller payment not found~%r",e)
            pass
        return return_list if return_list else self.env['seller.payment.method'].sudo()

    def _default_website_sequence(self):
        self._cr.execute("SELECT MIN(website_sequence) FROM %s" % self._table)
        min_sequence = self._cr.fetchone()[0]
        return min_sequence and min_sequence - 1 or 10

    # marketplace related field declaration
    allow_min_qty_notification=fields.Boolean(string="Activate Inventory Notification")
    set_min_qty=fields.Float(string="Threshold Qty.")

    seller = fields.Boolean(string="Is a Seller", help="Check this box if the contact is marketplace seller.", copy=False, tracking=True)
    payment_method = fields.Many2many("seller.payment.method", string="Payment Methods",
                                      help="It's you're accepted payment method, which will be used by admin during sending the payment.", default=_set_payment_method)
    state = fields.Selection([('new', 'New'), ('pending', 'Pending for Approval'), ('approved', 'Approved'), (
        'denied', 'Denied')], string="Seller Status", default="new", copy=False, tracking=True)
    attachment_ids = fields.One2many('ir.attachment', 'res_id', domain=lambda self: [
                                     ('res_model', '=', self._name)], auto_join=True, string='Attachments')
    displayed_image_id = fields.Many2one(
        'ir.attachment', domain="[('res_model', '=', 'project.task'), ('res_id', '=', id), ('mimetype', 'ilike', 'image')]", string='Displayed Image')
    # Marketplace Seller Wise setting
    set_seller_wise_settings = fields.Boolean(
        string="Override default seller perameters", copy=False)
    commission = fields.Float(string="Default Sale Commission", default=lambda self: self.env['ir.default'].sudo()._get(
        'res.config.settings', 'mp_commission'), copy=False, tracking=True)
    warehouse_id = fields.Many2one(
        "stock.warehouse", string="MP Default Warehouse", copy=False)
    location_id = fields.Many2one("stock.location", string="Default Location", domain="[('usage', '=', 'internal')]", default=lambda self: self.env[
                                  'ir.default']._get('res.config.settings', 'mp_location_id', company_id=True) or self.env["stock.location"], copy=False)
    auto_product_approve = fields.Boolean(string="Auto Product Approve", default=lambda self: self.env[
                                          'ir.default']._get('res.config.settings', 'mp_auto_product_approve'), copy=False)
    seller_payment_limit = fields.Integer(string="Seller Payment Limit", default=lambda self: self.env['ir.default'].sudo()._get(
        'res.config.settings', 'mp_seller_payment_limit'), copy=False, tracking=True)
    next_payment_request = fields.Integer(string="Next Payment Request", default=lambda self: self.env['ir.default'].sudo()._get(
        'res.config.settings', 'mp_next_payment_request'), copy=False, tracking=True)
    auto_approve_qty = fields.Boolean(string="Auto Quantity Approve", default=lambda self: self.env[
                                      'ir.default']._get('res.config.settings', 'mp_auto_approve_qty'), copy=False)
    total_mp_payment = fields.Monetary(
        string="Total Amount", compute="_calculate_mp_related_payment", currency_field='seller_currency_id')
    paid_mp_payment = fields.Monetary(string="Paid Amount", compute="_calculate_mp_related_payment", currency_field='seller_currency_id')
    balance_mp_payment = fields.Monetary(string="Balance Amount", compute="_calculate_mp_related_payment", currency_field='seller_currency_id')
    available_amount = fields.Monetary(string="Avalibale Amount", compute="_calculate_mp_related_payment", currency_field='seller_currency_id')
    cashable_amount = fields.Monetary(string="Cashable Amount", compute="_calculate_mp_related_payment", currency_field='seller_currency_id')
    seller_currency_id = fields.Many2one('res.currency', compute='_get_seller_currency', string="Marketplace Currency", readonly=True)
    return_policy = fields.Html(string="Return Policy", default="Seller return policy is not defined.", copy=False, translate=True)
    shipping_policy = fields.Html(string="Shipping policy", default="Seller shipping policy is not defined.", copy=False, translate=True)
    profile_msg = fields.Html(string="Profile Message", copy=False, translate=True)
    profile_image = fields.Binary(string="Profile Image", copy=False)
    profile_banner = fields.Binary(string="Profile Banner", copy=False)
    # seller reviews fields
    seller_review_ids = fields.One2many(
        'seller.review', 'marketplace_seller_id', string='Review')
    average_rating = fields.Float(
        compute='_set_avg_rating', string="Average Rating")
    active_recommendation = fields.Float(
    compute='_set_active_recommendation', string="Recommend")

    sol_count = fields.Float(
        compute='_compute_sol_count', string="Sales Count")

    # shop related field
    seller_shop_id = fields.Many2one("seller.shop", string="Seller Shop", copy=False)
    seller_rejection_reason = fields.Char(string="Product rejection Reason")

    #seller List Fields
    website_size_x = fields.Integer('Size X', default=1)
    website_size_y = fields.Integer('Size Y', default=1)
    website_style_ids = fields.Many2many('seller.shop.style', string='Styles')
    website_sequence = fields.Integer('Website Sequence', help="Determine the display order in the Website E-commerce",
                                      default=lambda self: self._default_website_sequence())
    website_ribbon_id = fields.Many2one('product.ribbon', string='Ribbon')
    allow_product_variants = fields.Boolean(compute="_get_product_variant_group_info", string="Allow Product Variants", help="Allow for several product attributes, defining variants (Example: size, color,...)")
    social_media_link_ids = fields.One2many("seller.social.media.link", "seller_id", "Social Media")
    url = fields.Char(string="URL", compute="_get_page_url")
    url_handler = fields.Char("Url Handler", help="Seller URL handler", copy=False)

    #seller status message field
    status_msg = fields.Text(string="Account Status Message", compute="_get_seller_status_msg", translate=True)

    #show notebook logic
    hide_notebook = fields.Boolean(compute="_compute_hide_notebook")

    sale_order_line_ids = fields.One2many("sale.order.line", "marketplace_seller_id", "Seller Sale Order Lines")

    seller_partner_ids = fields.Many2many("res.partner", string="Seller Partners", compute="_compute_seller_partner_ids", search="_search_seller_partner_ids", compute_sudo=True, context={'active_test': False})

    def _init_column(self, column_name):
        '''
        Inherit this function to skip the default values for these fields,
        as these default values are not required to be set for older 
        res.partner records.
        '''
        
        special_columns = [
            "payment_method", "commission", "warehouse_id", "location_id", "seller_payment_limit",
            "next_payment_request", "website_size_x", "website_size_y", "website_sequence", "state",
            "set_min_qty", "auto_approve_qty", "auto_product_approve","return_policy", "shipping_policy"
        ]
        
        if column_name not in special_columns:
            super()._init_column(column_name)

    def _get_other_user_ids(self):
        "returns the other user ids i.e., admin-ids, officer-ids, public-user-ids, odoo-bot-user-ids"
        user_ids = []
        admin_settings_group = self.env.ref('base.group_system')
        admin_ids = [u.partner_id.id for u in admin_settings_group.with_context(active_test=False).users]
        if admin_ids:
            user_ids.extend(admin_ids)

        mp_officer_group = self.env.ref('odoo_marketplace.marketplace_officer_group')
        officer_ids = [u.partner_id.id for u in mp_officer_group.users]
        if officer_ids:
            user_ids.extend(officer_ids)

        public_user = self.env.ref('base.group_public')
        public_user_id = self.env['res.users'].with_context(active_test=False).search([('groups_id','in',public_user.ids)])
        if public_user_id:
            user_ids.extend([public_user.partner_id.id for public_user in public_user_id])
        return user_ids

    def _get_customer_ids(self):
        "returns the customer-ids of seller from sale-order-line"
        customer_ids = [o.order_partner_id.id for o in self.sale_order_line_ids]

        customer_parent_ids = [o.order_partner_id.parent_id.id for o in self.sale_order_line_ids if o.order_partner_id.parent_id]

        customer_child_ids = []
        for o in self.sale_order_line_ids:
            if o.order_partner_id.child_ids:
                customer_child_ids.extend(o.order_partner_id.child_ids.ids)

        if customer_parent_ids:
            customer_ids.extend(customer_parent_ids)
        if customer_child_ids:
            customer_ids.extend(customer_child_ids)

        return customer_ids

    def _search_seller_partner_ids(self, operator, value):
        if operator == 'in':
            partner = self.env['res.partner'].browse(value)
            for rec in partner:
                customer_ids = rec._get_customer_ids()
            user_ids = self._get_other_user_ids()
            if customer_ids:
                user_ids.extend(customer_ids)

            return [('id', 'in', list(set(user_ids)))]

    def _compute_seller_partner_ids(self):
        for rec in self:
            customer_ids = rec._get_customer_ids()
            user_ids = rec._get_other_user_ids()
            customer_ids.extend(user_ids)

            rec.seller_partner_ids = list(set(customer_ids))

    def _compute_hide_notebook(self):
        for rec in self:
            current_user = self.env.user
            if  current_user.seller and current_user.partner_id.id != rec.id:
                rec.hide_notebook = True
            else:
                rec.hide_notebook = False

    # SQL Constraints for unique seller shop.
    _sql_constraints = [
        ('seller_shop_id_uniq', 'unique(seller_shop_id)',
        _('This shop is already assign to another seller.'))
    ]

    manager_fields.extend(['commission','seller_payment_limit','next_payment_request','auto_product_approve',
        'auto_approve_qty','location_id','warehouse_id','allow_product_variants',
        'total_mp_payment','paid_mp_payment','balance_mp_payment', 'state'])

    @api.model
    def im_search(self, name, limit=20):
        """Mail Chatter Restriction for Sellers"""
        res = super(ResPartner, self).im_search(name, limit)
        if self.env.user.check_user_is_draft_or_approved_seller():
            users = [p['user_id'] for p in res if p.get('user_id')]
            users = self.env["res.users"].sudo().browse(users).exists()
            users = users.filtered(lambda r: r.check_user_is_mp_officer())
            res = [l for l in res if l.get('user_id') and l['user_id'] in users.ids]
        return res

    # compute and search field methods, in the same order of fields declaration
    @api.model
    def _read_group_fill_results( self, domain, groupby, remaining_groupbys,
        aggregated_fields, read_group_order=None):
        state_list= [None for rec in range(len(self.STATES))]
        list_state = [state[0] for state in self.STATES]
        if groupby == 'state':
            for result in aggregated_fields:
                state = result['state']
                state_list[list_state.index(state)]=result
                if state in ['approved','denied']:
                    result['__fold'] = True
            state_list = [result for result in state_list if result != None ]
            aggregated_fields = state_list
        return super(ResPartner, self)._read_group_fill_results(domain, groupby, remaining_groupbys,
            aggregated_fields, read_group_order)

    def _get_seller_status_msg(self):
        """ Compute status message for seller"""
        for obj in self:
            website_id = obj.website_id or self.env["website"].search([],limit=1)
            if obj.state == "pending":
                if website_id and website_id.mp_seller_pending_status_msg:
                    obj.status_msg = website_id.mp_seller_pending_status_msg
                else:
                    obj.status_msg = "Thank you for seller request, your request has been already sent for approval we'll process your request as soon as possible."
            elif website_id and website_id.mp_seller_new_status_msg:
                obj.status_msg = website_id.mp_seller_new_status_msg
            else:
                obj.status_msg = "Thank you for registering with us, to enjoy the benefits of our marketplace fill all your details and request for approval."

    def _get_seller_currency(self):
        """ Compute seller currency"""
        for obj in self:
            obj.seller_currency_id = self.env['ir.default'].sudo()._get('res.config.settings', 'mp_currency_id') or self.env.user.company_id.currency_id

    def _get_website_ribbon(self):
        return self.website_ribbon_id

    def _calculate_mp_related_payment(self):
        """ Calculate total_mp_payment,balance_mp_payment,cashable_amount,paid_mp_payment ,total_mp_payment for seller"""
        for obj in self:
            if obj.seller:
                total_mp_payment = paid_mp_payment = cashable_amount = 0
                seller_payment_objs = self.env["seller.payment"].search([("seller_id", "=", obj.id), ("state", "not in",["draft", "requested"])])
                for seller_payment in seller_payment_objs:
                    #Calculate total marketplace payment for seller
                    if seller_payment.state == 'confirm' and seller_payment.payment_mode == "order_paid":
                        total_mp_payment += abs(seller_payment.payable_amount)

                    #Calculate total paid marketplace payment for seller
                    if seller_payment.state == 'posted' and seller_payment.payment_mode == "seller_payment":
                        paid_mp_payment += abs(seller_payment.payable_amount)

                    #Calculate marketplace cashable payment for seller
                    if seller_payment.state == 'confirm' and seller_payment.payment_mode == "order_paid" and seller_payment.is_cashable and (seller_payment.cashable_date and seller_payment.cashable_date <= date.today()):
                        cashable_amount += abs(seller_payment.payable_amount)

                obj.total_mp_payment = total_mp_payment
                obj.paid_mp_payment = paid_mp_payment
                obj.cashable_amount = (round(decimal.Decimal(cashable_amount - obj.paid_mp_payment), 2))

                #Calculate total balanec marketplace payment for seller
                obj.balance_mp_payment = abs(obj.total_mp_payment) - abs(obj.paid_mp_payment)

                #Calculate marketplace available payment for seller
                obj.available_amount = (round(decimal.Decimal(obj.balance_mp_payment), 2))
            else:
                obj.total_mp_payment = 0
                obj.paid_mp_payment = 0
                obj.cashable_amount = 0
                obj.balance_mp_payment = 0
                obj.available_amount = 0

    def _compute_sol_count(self):
        """ Calculate sale order line count for seller"""
        for obj in self:
            obj.sol_count = len(self.env["sale.order.line"].search([("marketplace_seller_id", "=", obj.id),('state','in',['sale','done'])]))

    def _get_product_variant_group_info(self):
        """ Compute allow product variant field"""
        for obj in self:
            product_variant_group = self.env.ref('product.group_product_variant')
            user_obj = self.env["res.users"].sudo().search([('partner_id', '=', obj.id)])
            user_groups = user_obj.read(['groups_id'])
            if user_groups and user_groups[0].get("groups_id"):
                user_groups_ids = user_groups[0].get("groups_id")
                if product_variant_group.id in user_groups_ids:
                    obj.allow_product_variants = True
                else:
                    obj.allow_product_variants = False
            else:
                obj.allow_product_variants = False

    def _get_page_url(self):
        """ Compute seller page url"""
        for obj in self:
            if obj.seller:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                base_url = base_url + "/seller/profile/"
                url_handler = str(obj.id) if not obj.url_handler else obj.url_handler
                obj.url = base_url + url_handler
            else:
                obj.url = False

    # Constraints and onchanges
    @api.onchange('state_id')
    def on_change_state_id(self):
        if self.state_id and self.state_id.country_id:
            self.country_id = self.state_id.country_id.id
        else:
            self.country_id = False

    @api.onchange('commission', 'seller_payment_limit', 'next_payment_request')
    def on_change_payment_assest(self):
        if self.commission < 0 or self.commission >= 100:
            raise Warning(_("Commission should be greater than 0 and less than 100."))
        if self.seller_payment_limit < 0 :
            raise Warning(_("Amount Limit can't be negative."))
        if self.next_payment_request < 0:
            raise Warning(_("Minimum Gap can't be negative."))

    @api.onchange("location_id")
    def on_change_location_id(self):
        wl_obj = self.env["stock.location"].browse(self.location_id.id)
        wh_obj = self.env["stock.warehouse"]
        whs = wh_obj.search([('view_location_id', 'parent_of', wl_obj.ids)], limit=1)
        if whs:
            self.warehouse_id = whs.id
        else:
            self.warehouse_id = None

    @api.onchange("set_seller_wise_settings")
    def on_change_seller_wise_settings(self):
        if self.set_seller_wise_settings:
            vals = {}
            vals["commission"] = self.env['ir.default'].sudo()._get(
                'res.config.settings', 'mp_commission')
            vals["location_id"] = self.env['ir.default'].sudo()._get(
                'res.config.settings', 'mp_location_id', company_id=True)
            vals["auto_product_approve"] = self.env['ir.default'].sudo()._get(
                'res.config.settings', 'mp_auto_product_approve')
            vals["seller_payment_limit"] = self.env['ir.default'].sudo()._get(
                'res.config.settings', 'mp_seller_payment_limit')
            vals["next_payment_request"] = self.env['ir.default'].sudo()._get(
                'res.config.settings', 'mp_next_payment_request')
            vals["auto_approve_qty"] = self.env['ir.default'].sudo()._get(
                'res.config.settings', 'mp_auto_approve_qty')
            self.update(vals)

    @api.onchange("seller")
    def on_change_seller(self):
        return_list = []
        payment_method_cheque_id = None
        if self.seller:
            try:
                payment_method_cheque_id = self.env['ir.model.data'].check_object_reference(
                    'odoo_marketplace', 'marketplace_seller_payment_method_data2')
                if payment_method_cheque_id:
                    return_list.append(payment_method_cheque_id[1])
            except Exception as e:
                _logger.warning("Warning! cheque seller payment method not found~%r",e)
                pass
            try:
                payment_method_bank_transfer_id = self.env['ir.model.data'].check_object_reference(
                    'odoo_marketplace', 'marketplace_seller_payment_method_data5')
                if payment_method_cheque_id:
                    return_list.append(payment_method_bank_transfer_id[1])
            except Exception as e:
                _logger.warning("Warning! Bank transfer seller payment method not found~%r",e)
                pass
            resConfig = self.env['res.config.settings'].sudo()
            self.state = "new"
            self.commission = resConfig.get_mp_global_field_value("mp_commission")
            self.warehouse_id = resConfig.get_mp_global_field_value("mp_warehouse_id")
            self.location_id = resConfig.get_mp_global_field_value("mp_location_id")
            self.auto_product_approve = resConfig.get_mp_global_field_value("mp_auto_product_approve")
            self.seller_payment_limit = resConfig.get_mp_global_field_value("mp_seller_payment_limit") or 0
            self.next_payment_request = resConfig.get_mp_global_field_value("mp_next_payment_request") or 0
            self.auto_approve_qty = resConfig.get_mp_global_field_value("mp_auto_approve_qty")
            self.payment_method = return_list

    # CRUD methods (and name_get, name_search, ...) overrides
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('url_handler'):
                if not re.match('^[a-zA-Z0-9-_]+$', vals.get('url_handler')) or re.match('^[-_][a-zA-Z0-9-_]*$', vals.get('url_handler')) or re.match('^[a-zA-Z0-9-_]*[-_]$', vals.get('url_handler')):
                    raise UserError(_("Please enter URL handler correctly!"))
                if vals.get("url_handler").isdigit():
                    raise UserError(_("Please enter URL handler correctly!.\nURL handler must contain atleast 1 letter(a-z)."))
                sameurl = self.search([('url_handler', '=', vals.get('url_handler'))])
                if sameurl:
                    raise UserError(_("Url already registered!"))
                vals["url_handler"] = vals.get('url_handler').lower().replace(" ","-") or ""
        res = super(ResPartner, self).create(vals_list)
        return res

    def write(self, vals):
        new_seller = False
        if not self.env.user.has_group('odoo_marketplace.marketplace_manager_group'):
            for res in manager_fields:
                if res in vals:
                    vals.pop(res)
        change_state_to = False
        for rec in self:
            if rec.seller:
                if rec.state != "approved" and vals.get("state", "") == "approved":
                    change_state_to = vals.get("state", False)
                if vals.get("state", "") in ["denied", "pending"]:
                    if rec.state == "new":
                        new_seller = True
                    change_state_to = vals.get("state", False)
                if vals.get("commission", 0) < 0 or vals.get("commission", 0) >= 100:
                    raise Warning(_("Commission should be greater than 0 and less than 100."))
                if vals.get("seller_payment_limit", 0) < 0 :
                    raise Warning(_("Amount Limit can't be negative."))
                if vals.get("next_payment_request", 0) < 0:
                    raise Warning(_("Minimum Gap can't be negative."))
                if vals.get('url_handler'):
                    if not re.match('^[a-zA-Z0-9-_]+$', vals.get('url_handler')) or re.match('^[-_][a-zA-Z0-9-_]*$', vals.get('url_handler')) or re.match('^[a-zA-Z0-9-_]*[-_]$', vals.get('url_handler')):
                        raise UserError(_("Please enter URL handler correctly!"))
                    if vals.get("url_handler").isdigit():
                        raise UserError(_("Please enter URL handler correctly!.\nURL handler must contain atleast 1 letter(a-z)."))
                    sameurl = self.search([ ('url_handler', '=', vals['url_handler']) , ('id', '!=', rec.id)])
                    if sameurl:
                        raise UserError(_("Url already registered!"))
                    vals["url_handler"] = (vals.get('url_handler').lower().replace(" ","-") or rec.url_handler.lower().replace(" ","-") or "") if vals.get('url_handler') else ""
        res = super(ResPartner, self).write(vals)
        for rec in self:
            if rec.seller and change_state_to == "approved":
                rec.change_seller_group_and_send_mail()
            elif rec.seller and vals.get("state", "") in ["denied", "pending"]:
                if new_seller:
                    rec.with_context(new_to_pending=True).change_seller_group_and_send_mail()
                else:
                    rec.change_seller_group_and_send_mail()
        if vals.get('state'):
            for rec in self.filtered('seller_shop_id'):
                rec.seller_shop_id.state = rec.state
        return res

    def get_seller_global_fields(self, field_name):
        """ Get seller global setting field's value"""
        self.ensure_one()
        if not hasattr(self, field_name):
            MissingError(_("%s field doesn't exist in res.partner model." % field_name))
        if self.set_seller_wise_settings:
            field_type = self._fields[field_name].type
            field_value = getattr(self, field_name)
            if field_type == 'many2one':
                field_value = field_value.id
            if field_type in ('one2many', 'many2many'):
                field_value = field_value.ids
        else:
            field_key = 'mp_%s' % field_name
            field_value = self.env['res.config.settings'].get_mp_global_field_value(field_key)
        return field_value

    # Action methods

    def approve(self):
        """ Approve seller status"""
        self.ensure_one()
        if self.seller:
            self.state = "approved"

    def deny(self):
        """Change seller status to reject"""
        self.ensure_one()
        if self.seller:
            self.state = "denied"
            self.website_published = False

    def set_to_pending(self):
        """Change seller status to pending"""
        for rec in self.with_user(SUPERUSER_ID):
            if rec.seller:
                if self.env['res.config.settings'].get_mp_global_field_value("auto_approve_seller"):
                    rec.approve()
                else:
                    rec.state = "pending"                    

    def toggle_website_published(self):
        """ Inverse the value of the field ``website_published`` on the records in ``self``. """
        for record in self:
            record.website_published = not record.website_published

    def set_sequence_top(self):
        self.website_sequence = self.sudo().search([], order='website_sequence desc', limit=1).website_sequence + 1

    def set_sequence_bottom(self):
        self.website_sequence = self.sudo().search([], order='website_sequence', limit=1).website_sequence - 1

    def set_sequence_up(self):
        previous_seller = self.sudo().search(
            [('website_sequence', '>', self.website_sequence), ('website_published', '=', self.website_published)],
            order='website_sequence', limit=1)
        if previous_seller:
            previous_seller.website_sequence, self.website_sequence = self.website_sequence, previous_seller.website_sequence
        else:
            self.set_sequence_top()

    def set_sequence_down(self):
        next_seller = self.search([('website_sequence', '<', self.website_sequence), ('website_published', '=', self.website_published)], order='website_sequence desc', limit=1)
        if next_seller:
            next_seller.website_sequence, self.website_sequence = self.website_sequence, next_seller.website_sequence
        else:
            return self.set_sequence_bottom()

    def enable_product_variant_group(self):
        """Enable manage product variants group for user"""
        for obj in self:
            user = self.env["res.users"].sudo().search(
                [('partner_id', '=', obj.id)])
            if user:
                # Add user to product variant group
                group = self.env.ref('product.group_product_variant')
                if group:
                    group.sudo().write({"users": [(4, user.id, 0)]})

    def disable_product_variant_group(self):
        """Disable manage product variants group for user"""
        for obj in self:
            user = self.env["res.users"].sudo().search(
                [('partner_id', '=', obj.id)])
            if user:
                # Remove user from product variant group
                group = self.env.ref('product.group_product_variant')
                if group:
                    group.sudo().write({"users": [(3, user.id, 0)]})

    def action_seller_sol(self):
        """Change domain and show sale order line for sale/done state """
        self.ensure_one()
        action = self.env.ref('odoo_marketplace.wk_seller_slae_order_line_action')
        list_view_id = self.env['ir.model.data']._xmlid_to_res_id(
            'odoo_marketplace.wk_seller_product_order_line_tree_view')
        form_view_id = self.env['ir.model.data']._xmlid_to_res_id(
            'odoo_marketplace.wk_seller_product_order_line_form_view')
        return {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'binding_view_types': action.binding_view_types,
            'view_mode': action.view_mode,
            'target': action.target,
            'res_model': action.res_model,
            'domain': "[('marketplace_seller_id','=',%s), ('state','in',('sale','done'))]" % self._ids[0],
        }

    def action_seller_globel_settings(self):
        """ Action to show seller global settings"""
        self.ensure_one()
        form_view_id = self.env['ir.model.data']._xmlid_to_res_id(
            'odoo_marketplace.mp_seller_globel_config_form_view')
        return {
            'name': _('Seller Global Settings'),
            'type': 'ir.actions.act_window',
            'views': [[form_view_id, 'form']],
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'res.config.settings',
            'context' : {'module' : 'odoo_marketplace'},
        }

    def change_seller_group(self, set_to_group=None):
        """ Param: set_to_group should be string, value must be 'not_seller' or 'seller' only. """

        if not set_to_group:
            return
        login_user_obj = self.env.user
        if not login_user_obj.has_group('odoo_marketplace.marketplace_officer_group'):
            raise UserError(_("You are not an autorized user to change seller account access. Please contact your administrator. "))
        for seller in self.filtered(lambda o: o.seller == True):
            seller_user = self.env["res.users"].sudo().search([('partner_id', '=', seller.id)])
            pending_seller_group_obj = self.env.ref('odoo_marketplace.marketplace_draft_seller_group')
            seller_group_obj = self.env.ref('odoo_marketplace.marketplace_seller_group')
            if set_to_group == "seller":
                #First check seller user realy belongs to draft seller group(marketplace_draft_seller_group) or not
                if seller_user.has_group("odoo_marketplace.marketplace_draft_seller_group"):
                    # Remove seller user from draft seller group(marketplace_draft_seller_group)
                    pending_seller_group_obj.sudo().write({"users": [(3, seller_user.id, 0)]})
                    # Add seller user to seller group(marketplace_seller_group)
                    seller_group_obj.sudo().write({"users": [(4, seller_user.id, 0)]})
                else:
                    _logger.warning(_("Warning!! Seller does not belongs to draft seller group. So you can't change seller group to seller group."))
            elif set_to_group == "not_seller":
                #First check seller user realy belongs to seller group(marketplace_seller_group) or not
                if seller_user.has_group("odoo_marketplace.marketplace_seller_group"):
                    # Remove seller user from seller group(marketplace_seller_group)
                    seller_group_obj.write({"users": [(3, seller_user.id, 0)]})
                    # Add seller user to draft seller group(marketplace_draft_seller_group)
                    pending_seller_group_obj.write({"users": [(4, seller_user.id, 0)]})

    def notify_via_mail_to_seller(self, mail_templ_id):
        """ Send mail to seller """
        if not mail_templ_id:
            return False
        template_obj = self.env['mail.template'].browse(mail_templ_id)
        try:
            action = self.env.ref('odoo_marketplace.wk_seller_action').id
            dashboard_action = self.env.ref('odoo_marketplace.wk_dashboard_action').id
            new_context = dict(self.env.context or {})
            new_context['action_id'] = str(action) 
            new_context['dashboard_action_id'] = str(dashboard_action)
            template_obj.with_company(self.env.company).with_context(new_context).send_mail(self.id, True,email_layout_xmlid='mail.mail_notification_light')
        except Exception as e:
            _logger.warning("Warning! Not able to send mail to seller(Exception ~~%r)",e)

    def change_seller_group_and_send_mail(self):
        """ Call this method to change seller group and send mail to seller when state has been set to 'approved'.
            param: string value can be ('pending', 'denied', 'approved'). Action will be performed for 'pending', 'denied', 'approved' values by asuming that one of the these value has been set current state.
        """
        if not self.user_ids:
            raise ValidationError(_('This seller has no user linked.'))

        resConfig = self.env['res.config.settings']

        if self.seller and self.state == "approved":
            #Change seller to approve seller group(marketplace_seller_group)
            self.change_seller_group(set_to_group="seller")

            #Send mail to admin/seller on seller approval
            if resConfig.get_mp_global_field_value("enable_notify_admin_on_seller_approve_reject"):
                # Notify to admin by admin on new seller approval
                temp_id = resConfig.get_mp_global_field_value("notify_admin_on_seller_approve_reject_m_tmpl_id")
                if temp_id:
                    self.notify_via_mail_to_seller(temp_id)
            if resConfig.get_mp_global_field_value("enable_notify_seller_on_approve_reject"):
                # Notify to Seller by admin on new seller approval
                temp_id = resConfig.get_mp_global_field_value("notify_seller_on_approve_reject_m_tmpl_id")
                if temp_id:
                    self.notify_via_mail_to_seller(temp_id)
        elif self.seller and self.state in ["pending", "denied"]:
            #Change seller to draft seller group(marketplace_draft_seller_group)
            self.env["product.template"].disable_seller_all_products(self.id)
            self.env["marketplace.stock"].disable_seller_all_inventory_requests(self.id)
            self.change_seller_group(set_to_group="not_seller")

            if self._context.get("new_to_pending", False):
                #Send mail to admin/seller on seller approval
                if resConfig.get_mp_global_field_value("enable_notify_admin_4_new_seller"):
                    # Notify to admin by admin on new seller creation
                    temp_id = resConfig.get_mp_global_field_value("notify_admin_4_new_seller_m_tmpl_id")
                    if temp_id:
                        self.notify_via_mail_to_seller(temp_id)
                if resConfig.get_mp_global_field_value("enable_notify_seller_4_new_seller"):
                    # Notify to Seller by admin on new seller creation
                    temp_id = resConfig.get_mp_global_field_value("notify_seller_4_new_seller_m_tmpl_id")
                    if temp_id:
                        self.notify_via_mail_to_seller(temp_id)
            else:
                #Send mail to admin/seller on seller reject
                if resConfig.get_mp_global_field_value("enable_notify_admin_on_seller_approve_reject"):
                    # Notify to admin by admin on new seller reject
                    temp_id = resConfig.get_mp_global_field_value("notify_admin_on_seller_approve_reject_m_tmpl_id")
                    if temp_id:
                        self.notify_via_mail_to_seller(temp_id)
                if resConfig.get_mp_global_field_value("enable_notify_seller_on_approve_reject"):
                    # Notify to Seller by admin on new seller reject
                    temp_id = resConfig.get_mp_global_field_value("notify_seller_on_approve_reject_m_tmpl_id")
                    if temp_id:
                        self.notify_via_mail_to_seller(temp_id)
        else:
            _logger.warning(_("Seller is not in approved, denied, pending state. So you can't change seller group and notify to seller"))
        return True

    # Methods used in seller review process
    def _set_avg_rating(self):
        """ Calculating seller average ratings """
        add = 0.0
        avg = 0.0
        for obj in self:
            if obj.seller_review_ids:
                for reviews_obj in obj.seller_review_ids:
                    add += reviews_obj.rating
                avg = add / len(obj.seller_review_ids)
            obj.average_rating = (round(decimal.Decimal(abs(avg)), 2))

    def fetch_active_review(self, seller_id):
        """ Fetch seller active reviews """
        if seller_id:
            review_ids = self.env["seller.review"].search(
                [('marketplace_seller_id', '=', seller_id), ('website_published', '=', True)])
            return review_ids
        else:
            return []

    def fetch_active_review2(self, seller_id, offset=0, limit=False, sort_by="recent", filter_by=-1):
        """Fetching seller active reviews on the basis of rating"""

        if filter_by == -1:
            review_ids = self.env["seller.review"].search([('marketplace_seller_id', '=', seller_id), (
                'website_published', '=', True)], order="helpful desc" if sort_by == "most_helpful" else "create_date desc")
        if filter_by == 1:
            review_ids = self.env["seller.review"].search([('marketplace_seller_id', '=', seller_id), ('website_published', '=', True), (
                'rating', '=', 1)], order="helpful desc" if sort_by == "most_helpful" else "create_date desc")
        if filter_by == 2:
            review_ids = self.env["seller.review"].search([('marketplace_seller_id', '=', seller_id), ('website_published', '=', True), (
                'rating', '=', 2)], order="helpful desc" if sort_by == "most_helpful" else "create_date desc")
        if filter_by == 3:
            review_ids = self.env["seller.review"].search([('marketplace_seller_id', '=', seller_id), ('website_published', '=', True), (
                'rating', '=', 3)], order="helpful desc" if sort_by == "most_helpful" else "create_date desc")
        if filter_by == 4:
            review_ids = self.env["seller.review"].search([('marketplace_seller_id', '=', seller_id), ('website_published', '=', True), (
                'rating', '=', 4)], order="helpful desc" if sort_by == "most_helpful" else "create_date desc")
        if filter_by == 5:
            review_ids = self.env["seller.review"].search([('marketplace_seller_id', '=', seller_id), ('website_published', '=', True), (
                'rating', '=', 5)], order="helpful desc" if sort_by == "most_helpful" else "create_date desc")
        return_obj = []
        if review_ids and offset < len(review_ids):
            while offset < len(review_ids) and limit != 0:
                return_obj.append(review_ids[offset])
                offset += 1
                limit -= 1
            return return_obj
        else:
            return []

    def avg_review(self):
        """ Calculate seller average reviews"""
        val = 0.0
        length = 0.0
        if self._ids:
            reviews_obj = self.fetch_active_review(self._ids[0])
            if reviews_obj:
                for obj in reviews_obj:
                    val += float(obj.rating)
                    length = float(len(reviews_obj))
                return round((val / length), 1)
        return 0

    def fetch_user_vote(self, seller_review_id):
        """ Fetch seller Voting"""
        like_dislike = self.env["review.help"]
        review_help_ids = like_dislike.search(
            [('customer_id', '=', self._uid), ('seller_review_id', '=', seller_review_id)])
        if review_help_ids:
            result = [True if review_help_ids[0].review_help == "yes" else False,
                      True if review_help_ids[0].review_help == "no" else False]
            return result
        return [False, False]

    @api.model
    def get_review_current_time(self, seller_review_id):
        """ Calculate review current time"""
        review_pool = self.env["seller.review"]
        if seller_review_id:
            seller_review_obj = review_pool.browse(seller_review_id)
            iso_format = seller_review_obj.create_date.strftime('%Y-%m-%dT%H:%M:%SZ')
            return iso_format

    def action_avg_seller_review_fun(self):
        """Method to show seller average reviews"""
        self.ensure_one()
        action = self.env.ref('odoo_marketplace.action_seller_review')
        list_view_id = self.env['ir.model.data']._xmlid_to_res_id(
            'odoo_marketplace.mp_seller_review_tree_view_webkul2')
        form_view_id = self.env['ir.model.data']._xmlid_to_res_id(
            'odoo_marketplace.mp_seller_review_form_view_webkul2')
        return {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'binding_view_types': action.binding_view_types,
            'view_mode': action.view_mode,
            'target': action.target,
            'res_model': action.res_model,
            'domain': "[('marketplace_seller_id','=',%s)]" % self._ids[0],
        }

    def total_star_count(self, no_of_star):
        """ Calculate count of seller reviews on the basis of no_of_star"""
        if not no_of_star:
            return 0
        review_ids = self.env["seller.review"].search(
            [('marketplace_seller_id', '=', self.id), ('website_published', '=', True), ("rating", "=", no_of_star)])
        return len(review_ids.ids) if review_ids else 0

    def total_active_recommendation(self):
        """ calculate count of seller active recommendation"""
        return_list = []
        recommendation_ids = self.env[
            "seller.recommendation"].search([('state', '=', "pub"),("seller_id","=",self.id)])
        recommendation_yes_ids = self.env["seller.recommendation"].search(
            [('state', '=', "pub"), ("recommend_state", "=", "yes"),("seller_id","=",self.id)])
        yes_percentage = len(recommendation_yes_ids.ids) * 100 / \
            len(recommendation_ids.ids) if recommendation_ids else 0
        return_list.append(len(recommendation_ids.ids)
                           if recommendation_ids else 0)
        return_list.append(yes_percentage)
        return return_list

    def _set_active_recommendation(self):
        """ Set active recommendation"""
        for obj in self:
            obj.active_recommendation = obj.total_active_recommendation()[1]

    def action_active_recommendation_fun(self):
        """Method to show seller active recommendation"""
        self.ensure_one()
        action = self.env.ref('odoo_marketplace.action_seller_review')
        list_view_id = self.env['ir.model.data']._xmlid_to_res_id(
            'odoo_marketplace.mp_seller_review_tree_view_webkul2')
        form_view_id = self.env['ir.model.data']._xmlid_to_res_id(
            'odoo_marketplace.mp_seller_review_form_view_webkul2')
        return {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'views': [[list_view_id, 'tree'], [form_view_id, 'form']],
            'binding_view_types': action.binding_view_types,
            'view_mode': action.view_mode,
            'target': action.target,
            'res_model': action.res_model,
            'domain': "[('marketplace_seller_id','=',%s)]" % self._ids[0],
        }

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id, view_type, **options)
        manager_group = self.env['ir.model.data'].check_object_reference(
            'odoo_marketplace', 'marketplace_officer_group')[1]
        groups_ids = self.env.user.sudo().groups_id.ids

        if manager_group not in groups_ids and result.get("toolbar", False):
            result["toolbar"] = {}
        return result

    def seller_sales_count(self):
        """Calculate seller total sales count"""
        sales_count = 0
        all_products = self.env['product.template'].sudo().search(
            [("marketplace_seller_id", "=", self.sudo().id)])
        for prod in all_products.with_user(SUPERUSER_ID):
            sales_count += prod.sales_count
        return sales_count

    def seller_products_count(self):
        """Calculate seller total product count"""
        sales_count = 0
        all_products = self.env['product.template'].sudo().search(
            [("marketplace_seller_id", "=", self.sudo().id), ("status",'=','approved'),('website_published', '=', True)])
        return len(all_products)

    def register_partner_as_a_seller(self):
        """ Register partner as a seller"""
        for rec in self:
            current_user = rec.env['res.users'].search([('partner_id','=',rec.id)])
            context = dict(rec._context) or {}
            context['active_id'] = rec.id
            if not current_user:
                if not rec.email:
                    raise UserError(_("Email is mandatory for the registration, Please add a valid email to proceed further."))
                else:
                    existing_users = rec.env['res.users'].search([('login','=',rec.email)])
                    if existing_users:
                        raise UserError(_("The email address you have entered is already registered."))
            if current_user:
                if current_user.has_group("odoo_marketplace.marketplace_officer_group"):
                    grp_name = "Manager" if current_user.has_group("odoo_marketplace.marketplace_manager_group") else "Officer"
                    raise ValidationError(_("The user %s already has Marketplace %s group. Please remove it first to proceed further.",current_user.name,grp_name))
                context['user_id'] = current_user.id
            return {
                'name':_('Register Partner As a Seller'),
                'type':'ir.actions.act_window',
                'res_model':'seller.resistration.wizard',
                'view_mode':'form',
                'binding_view_types':'form',
                'view_id':rec.env.ref('odoo_marketplace.seller_registration_wizard_form').id,
                'context' : context,
                'target':'new',
            }

    def action_open_sellers(self, **post):
        action = self.env.ref('odoo_marketplace.wk_seller_action')
        search_view_id = [self.env.ref('odoo_marketplace.wk_seller_view_filter').id]        
        domain = [('seller', '=', True)]
        filter_data = post.get('params')
        context = {}
        if filter_data:
            domain += self.env['marketplace.dashboard'].get_filtered_domain(filter_data) or []
            additional_ctx = self.env['marketplace.dashboard'].prepare_filter_context(filter_data)
            context.update(additional_ctx)
        if filter_data.get('seller_ids'):
            seller_ids = filter_data['seller_ids']
            sellers_list = tuple(map(int, seller_ids.split(',')))
            domain += [('id', 'in', sellers_list)]

        action = {
            'name': action.name,
            'type': action.type,
            'binding_view_types': action.binding_view_types,
            'search_view_id': search_view_id,
            'views': action.views,
            'view_mode': action.view_mode,
            'target': action.target,
            'res_model': action.res_model,
            'domain': domain,
            'context': context
        }
        return action
    

class SellerSocialMedia(models.Model):
    _description = " Model to manage sellers social media links."
    _name = "seller.social.media.link"
    _rec_name = "social_media_id"

    # marketplace related field declaration

    social_media_id = fields.Many2one("marketplace.social.media", "Profile Name", required=True)
    social_profile_id = fields.Char("Profile Id", required=True, help="Social media profile id.")
    seller_id = fields.Many2one("res.partner")
    wk_website_published = fields.Boolean("Published")
    complete_url = fields.Char(compute="_get_complete_profile_url", string="Profile URL")

    # compute and search field methods, in the same order of fields declaration
    @api.depends("social_media_id", "social_media_id.base_url", "social_profile_id")
    def _get_complete_profile_url(self):
        """ Compute complete profile url"""
        for obj in self:
            url = False
            if obj.social_media_id.base_url:
                if obj.social_media_id.base_url.endswith('/'):
                    url = obj.social_media_id.base_url + str(obj.social_profile_id) if obj.social_profile_id else ""
                else:
                    url = obj.social_media_id.base_url + '/' + str(obj.social_profile_id) if obj.social_profile_id else ""
            obj.complete_url = url

    # Constraints and onchanges
    @api.onchange("social_media_id")
    def onchange_profile_id(self):
        if self.social_media_id:
            self._get_complete_profile_url()

    # Action methods
    def toggle_website_published(self):
        """ Inverse the value of the field ``wk_website_published`` on the records in ``self``. """
        for record in self:
            record.wk_website_published = not record.wk_website_published


class MarketplaceSocialMedia(models.Model):
    _name = "marketplace.social.media"
    _description = " Model to manage social media."

    # Fields declaration
    name = fields.Char("Name", required=True)
    image = fields.Binary("Social Media Image")
    base_url = fields.Char("Base URL", required=True, help="Social media site complete url.")
