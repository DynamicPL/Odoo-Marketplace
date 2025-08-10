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
import logging
_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    STATES = [('draft', 'Draft'), ('pending', 'Pending'), (
        'approved', 'Approved'), ('rejected', 'Rejected')]
    # Default methods
    def _get_default_category_id(self):
        """ Set default value in category """
        if self.marketplace_seller_id:
            mp_categ = self.env['res.config.settings'].get_mp_global_field_value('internal_categ')
            if mp_categ:
                return mp_categ.id
        elif self._context.get("pass_default_categ"):
            return False
        return super(ProductTemplate, self)._get_default_category_id()

    # Fields declaration
    categ_id = fields.Many2one(
        'product.category', 'Internal Category',
        change_default=True, default=_get_default_category_id,
        required=True, help="Select category for the current product")
    status = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), (
        'approved', 'Approved'), ('rejected', 'Rejected')], "Marketplace Status", default="draft", copy=False, tracking=True)
    mp_qty = fields.Float(string="Initial Quantity",
                       help="Initial quantity of the product which you want to update in warehouse for inventory purpose.", copy=False)
    marketplace_seller_id = fields.Many2one(
        "res.partner", string="Seller", default=lambda self: self.env.user.partner_id.id if self.env.user.partner_id and self.env.user.partner_id.seller else self.env['res.partner'], copy=False, tracking=True, help="If product has seller then it will consider as marketplace product else it will consider as simple product.")
    color = fields.Integer('Color Index')
    is_initinal_qty_set = fields.Boolean("Initial Qty Set")
    # activity_date_deadline = fields.Date(
    #     'Next Activity Deadline', related='activity_ids.date_deadline',
    #     readonly=True, store=True,
    #     groups="base.group_user,odoo_marketplace.marketplace_seller_group")
    item_ids = fields.One2many('product.pricelist.item', 'product_tmpl_id', 'Pricelist Items')
    rejection_reason = fields.Char(string="Product rejection Reason")


    def _check_record_mp_access(self, user):
        '''
        This method check record access for seller
        '''
        if self.exists() and self.marketplace_seller_id.id != user.partner_id.id:
            raise self.env['ir.rule']._make_access_error('read', self)

    def read(self, fields=None, load='_classic_read'):
        user = self.env.user
        super_access = self.env.su
        seller = user.check_user_is_draft_or_approved_seller()
        other_cond = self._context.get('params',{}).get('view_type','') == 'form' or len(self)==1
        if not super_access and seller and other_cond:
            for rec in self:
                rec._check_record_mp_access(user)
        res =  super().read(fields=fields, load=load)
        return res

    @api.model
    def _read_group_fill_results( self, domain, groupby, remaining_groupbys,
        aggregated_fields, read_group_order=None):
        state_list= [None for rec in range(len(self.STATES))]
        list_state = [state[0] for state in self.STATES]
        if groupby == 'status':
            for result in aggregated_fields:
                state = result['status']
                state_list[list_state.index(state)]=result
                if state in ['rejected']:
                    result['__fold'] = True

            state_list = [result for result in state_list if result != None ]
            aggregated_fields = state_list
        return super(ProductTemplate, self)._read_group_fill_results(domain, groupby, remaining_groupbys,
            aggregated_fields, read_group_order)

    # SQL Constraints

    # Constraints and onchanges
    @api.onchange("marketplace_seller_id")
    def onchange_seller_id(self):
        self.status = "draft" if self.marketplace_seller_id and not self.status else False
        self.categ_id = self.env['res.config.settings'].get_mp_global_field_value('internal_categ')

    # CRUD methods (and name_get, name_search, ...) overrides

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner = self.env["res.partner"].sudo().browse(
                vals.get("marketplace_seller_id", False)) or self.env.user.partner_id
            if partner and partner.sudo().seller:
                if not vals.get("sale_ok", False):
                    vals["sale_ok"] = False
                if not vals.get("purchase_ok", False):
                    vals["purchase_ok"] = False
                if not vals.get("status", False):
                    vals["status"] = "draft"
                # if vals.get('type', False) and vals['type'] != 'service' and not vals.get("invoice_policy", False):
                #     vals["invoice_policy"] = "delivery"
                mp_categ = self.env['res.config.settings'].get_mp_global_field_value(
                    'internal_categ')
                if mp_categ:
                    vals["categ_id"] = mp_categ
        return super(ProductTemplate, self).create(vals_list)

    # Action methods

    def toggle_website_published(self):
        """ Inverse the value of the field ``website_published`` on the records in ``self``. """
        for record in self:
            if record.marketplace_seller_id and record.status != 'approved' and not record.website_published:
                raise UserError(_("You cannot publish unapproved products."))
            record.website_published = not record.website_published

    def mp_action_view_sales(self):
        self.ensure_one()
        action = self.env.ref('odoo_marketplace.wk_seller_slae_order_line_action')
        product_ids = self.product_variant_ids.ids
        tree_view_id = self.env.ref('odoo_marketplace.wk_seller_product_order_line_tree_view')
        form_view_id = self.env.ref('odoo_marketplace.wk_seller_product_order_line_form_view')
        return {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'binding_view_types': action.binding_view_types,
            'view_mode': action.view_mode,
            'views': [(tree_view_id.id, 'tree'), (form_view_id.id, 'form')],
            'target': action.target,
            'context': "{'default_product_id': " + str(product_ids[0]) + "}",
            'res_model': action.res_model,
            'domain': [('state', 'in', ['sale', 'done']), ('product_id.product_tmpl_id', '=', self.id)],
        }

    def get_product_approval_wizard_action(self):
        """ Server Action to approve selected records """

        record = self.env["server.action.wizard"].create({
            'product_ids': self.ids
        })
        return {
            'name':_('Approve Products'),
            'type':'ir.actions.act_window',
            'res_model':'server.action.wizard',
            'view_mode':'form',
            'domain': [('marketplace_seller_id','!=',False),('status','=','pending')],
            'context': {'only_approve': True},
            'res_id' : record.id,
            'target':'new',
        }
    
    def get_publish_wizard_action(self):
        """ Server Action to publish selected records """
        record = self.env["publish.action.details"].create({
            'product_ids': self.ids
        })
        return {
            'name':_('Publish Products'),
            'type':'ir.actions.act_window',
            'res_model':'publish.action.details',
            'view_mode':'form',
            'domain': [('marketplace_seller_id','!=',False)],
            'res_id' : record.id,
            'target':'new',
        }

    def get_unpublish_wizard_action(self):
        """ Server Action to Unpublish selected records """

        record = self.env["unpublish.action.details"].create({
            'product_ids': self.ids
        })
        return {
            'name':_('UnPublish Products'),
            'type':'ir.actions.act_window',
            'res_model':'unpublish.action.details',
            'view_mode':'form',
            'domain': [('marketplace_seller_id','!=',False)],
            'res_id' : record.id,
            'target':'new',
        }

    def get_product_reject_wizard_action(self):
        """ Server Action to Reject selected records """

        record = self.env["server.action.wizard"].create({
            'product_ids': self.ids
        })
        return {
            'name':_('Reject Products'),
            'type':'ir.actions.act_window',
            'res_model':'server.action.wizard',
            'view_mode':'form',
            'domain': [('marketplace_seller_id','!=',False),('status','in',['approved','pending'])],
            'context': {'only_reject': True},
            'res_id' : record.id,
            'target':'new',
        }

    def send_mail_to_seller(self, mail_templ_id):
        """ Send mail to seller """
        if not mail_templ_id:
            return False
        template_obj = self.env['mail.template'].browse(mail_templ_id)
        action = self.env.ref('odoo_marketplace.wk_seller_product_template_action').id
        new_context = dict(self.env.context or {})
        new_context['action_id'] = action  # Add action_id to 
        new_context['company'] = self.env.company
        template_obj.with_company(self.env.company).with_context(new_context).send_mail(self.id, True,email_layout_xmlid='mail.mail_notification_light')

    def auto_approve(self):
        """Method to Approve product """
        for obj in self:
            if obj.marketplace_seller_id:
                obj.product_variant_ids.set_to_approved()
                obj.sudo().write({"status": "approved", "sale_ok": True})
                obj.check_state_send_mail()
                if not obj.is_initinal_qty_set and len(obj.product_variant_ids) == 1:
                    obj.set_initial_qty()
     

    def auto_publish(self):
        """Method to publish product """
        for record in self:
            if record.marketplace_seller_id and record.status == 'approved' and not record.website_published:
               record.website_published = not record.website_published
       

    def auto_unpublish(self):
        """Method to unpublish product """
        for record in self:
            if record.marketplace_seller_id and record.status == 'approved' and  record.website_published:
               record.website_published = not record.website_published


    def check_state_send_mail(self):
        """ Notify to Seller by admin  when product approved/reject"""
        resConfig = self.env['res.config.settings']
        for obj in self.filtered(lambda o: o.status in ["approved", "rejected"]):
            # Notify to Seller by admin  when product approved/reject
            if resConfig.get_mp_global_field_value("enable_notify_seller_on_product_approve_reject"):
                temp_id = resConfig.get_mp_global_field_value("notify_seller_on_product_approve_reject_m_tmpl_id")
                if temp_id:
                    self.send_mail_to_seller(temp_id)

    def approved(self):
        """Method to approve product"""

        for obj in self:
            if not obj.marketplace_seller_id:
                raise Warning(_("Marketplace seller id is not assign to this product."))
            if obj.marketplace_seller_id.state != "approved":
                raise Warning(_("Marketplace seller of this product is not approved."))
            if obj.marketplace_seller_id.get_seller_global_fields('auto_product_approve') or obj.product_variant_count <= 1:
                obj.auto_approve()
            else:
                form_view_ref = self.env.ref('odoo_marketplace.wk_product_variant_wizard_view')
                return {
                    'name':_('Product Variant Approval') ,
                    'type': 'ir.actions.act_window',
                    'binding_view_types': 'form',
                    'view_id': form_view_ref.id,
                    'view_mode': 'form',
                    'res_model': 'variant.approval.wizard',
                    'nodestroy': True,
                    'target': 'new',
                }
        return True

    def reject(self):
        """Method to reject product"""

        for product_obj in self:
            if product_obj.status in ("draft", "pending", "approved") and product_obj.marketplace_seller_id:
                product_obj.write({
                    "sale_ok": False,
                    "website_published": False,
                    "status": "rejected"
                })
                for variant in product_obj.product_variant_ids:
                    variant.set_to_rejected()
                product_obj.check_state_send_mail()

    def reject_product_template(self):
        for product in self:
            if product.status in ("draft", "pending", "approved") and product.marketplace_seller_id:
                return {
                    'name': _('Product Reject'),
                    'type': 'ir.actions.act_window',
                    'binding_view_types': 'form',
                    'context': {'default_mp_reason_type': 'product_reason'},
                    'view_mode': 'form',
                    'res_model': 'seller.status.reason.wizard',
                    'target': 'new',
                }

    def update_quantity(self):
        for product in self:
            product_stock = self.env['marketplace.stock'].search([('product_temp_id','=',product.id),('state','=','requested')])
            if product_stock:
                raise ValidationError(_('Your inventory request is already in a pending state.'))
            else:
                return {
                    'name': _("Marketplace Stock"),
                    'type': 'ir.actions.act_window',
                    'res_model': 'marketplace.stock',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'target': 'new',
                }

    # Called in server action
    def approve_product(self):
        self.filtered(lambda o: o.status == "pending" and o.marketplace_seller_id).approved()

    def set_initial_qty(self):
        """ Create marketplace.stock record and set mp_qty to new_quantity"""

        for template_obj in self:
            location_id = template_obj.marketplace_seller_id.get_seller_global_fields('location_id')
            if len(self) == 1:
                if template_obj.mp_qty < 0:
                    raise Warning(_('Initial Quantity can not be negative'))
            if not location_id:
                raise Warning(_("Product seller has no location/warehouse."))
            if template_obj.mp_qty > 0:
                vals = {
                    'product_id': template_obj.product_variant_ids[0].id,
                    'product_temp_id': template_obj.id,
                    'new_quantity': template_obj.mp_qty,
                    'location_id': location_id or False,  # Phase 2
                    'note': _("Initial Quantity."),
                    'state': "requested",
                }
                mp_product_stock = self.env['marketplace.stock'].create(vals)
                template_obj.is_initinal_qty_set = True
                mp_product_stock.auto_approve()

    def disable_seller_all_products(self, seller_id):
        """ Method to disable seller's all products"""

        if seller_id:
            product_objs = self.search(
                [("marketplace_seller_id", "=", seller_id), ("status", "not in", ["draft", "rejected"])])
            product_objs.reject()

    def set_pending(self):
        """ Method to change product status to pending"""
        for rec in self:
            rec.product_variant_ids.set_to_pending()
            rec.write({"status": "pending"})
            resConfig = self.env['res.config.settings']
            if resConfig.get_mp_global_field_value("enable_notify_admin_on_product_approve_reject"):
                temp_id = resConfig.get_mp_global_field_value("notify_admin_on_product_approve_reject_m_tmpl_id")
                if temp_id:
                    # Notify to admin by admin when seller request for product approval
                    rec.sudo().send_mail_to_seller(temp_id)
            if rec.marketplace_seller_id and rec.marketplace_seller_id.get_seller_global_fields('auto_product_approve'):
                rec.auto_approve()

    def send_to_draft(self):
        """ Method to change product status to Draft"""
        for rec in self:
            rec.product_variant_ids.set_to_draft()
            rec.write({"status": "draft"})

    def write(self, vals):
        if vals.get("marketplace_seller_id", False):
            for rec in self:
                if rec.marketplace_seller_id and rec.status not in ["draft", "pending"]:
                    raise UserError(_('You cannot change the seller of the product that already contains seller.'))
        return super(ProductTemplate, self).write(vals)

    def _get_combination_info(self, combination=False, product_id=False, add_qty=1, parent_combination=False, only_template=False):
        combination_info = super(ProductTemplate, self)._get_combination_info(
            combination=combination, product_id=product_id, add_qty=add_qty,
            parent_combination=parent_combination, only_template=only_template)

        if not self.env.context.get('website_sale_stock_get_quantity'):
            return combination_info

        if combination_info['product_id']:
            product = self.env['product.product'].sudo().browse(combination_info['product_id'])
            seller_obj = product.marketplace_seller_id
            if seller_obj and seller_obj.seller:
                warehouse_id = seller_obj.get_seller_global_fields("warehouse_id")
                if warehouse_id:
                    virtual_available = product.with_context(warehouse=warehouse_id).virtual_available
                    combination_info.update({
                        'virtual_available': virtual_available,
                        'free_qty': virtual_available,
                    })
        return combination_info

    def _get_variant_for_combination(self, combination):
        """Return approved seller product variants."""
        variant = super()._get_variant_for_combination(combination)
        if variant and variant.marketplace_seller_id:
            if variant.marketplace_status == 'approved':
                return variant
            else:
                return self.env['product.product']
        else:
            return variant

    def action_open_product_template(self, **post):
        # self.ensure_one()
        action = self.env.ref('odoo_marketplace.wk_seller_product_template_action')
        search_view_id = [self.env.ref('odoo_marketplace.wk_product_template_seller_filter').id]        
        views = [
            (self.env.ref('odoo_marketplace.wk_seller_product_template_kanban_view').id, 'kanban'),
            (self.env.ref('odoo_marketplace.wk_seller_product_template_tree_view').id, 'tree'),
            (self.env.ref('odoo_marketplace.wk_seller_product_template_form_view').id, 'form')
        ]
        user = self.env.user
        domain = [('status', '=', 'approved')]
        filter_data = post.get('params')

        if filter_data:
            if filter_data.get('best_selling_prod_ids'):
                product_ids = filter_data['best_selling_prod_ids']
                products_list = tuple(map(int, product_ids.split(',')))
                domain += [('id', 'in', products_list)]
            else:
                domain += self.env['marketplace.dashboard'].get_filtered_domain(filter_data) or []

        if not user._is_admin():
            domain += [('marketplace_seller_id', '=', user.partner_id.id)]

        action = {
            'name': action.name,
            'type': action.type,
            'binding_view_types': action.binding_view_types,
            'search_view_id': search_view_id,
            'views': views,
            'view_mode': action.view_mode,
            'target': action.target,
            'res_model': action.res_model,
            'domain': domain,
        }
        return action
    
class ProductProduct(models.Model):
    _inherit = 'product.product'

    # activity_date_deadline = fields.Date(
    #     'Next Activity Deadline', related='activity_ids.date_deadline',
    #     readonly=True, store=True,
    #     groups="base.group_user,odoo_marketplace.marketplace_seller_group")
    mp_var_qty = fields.Float(string="Initial Variant Quantity",
                       help="Initial quantity of the product which you want to update in warehouse for inventory purpose.", copy=False)
    is_var_initinal_qty_set = fields.Boolean("Initial Variant Qty Set")
    marketplace_status = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), (
        'approved', 'Approved'), ('rejected', 'Rejected')], "Marketplace Variant Status", default="draft", copy=False)
    item_ids = fields.One2many('product.pricelist.item', 'product_id', string='Pricelist Items')

    # Action methods

    def set_var_initial_qty(self):
        """ Create marketplace.stock record and set mp_qty to new_quantity """
        for var_obj in self:
            location_id = var_obj.marketplace_seller_id.get_seller_global_fields('location_id') or False
            if var_obj.mp_var_qty < 0:
                raise Warning(_('Initial Quantity can not be negative'))
            if not location_id:
                raise Warning(_("Product seller has no location/warehouse."))
            if var_obj.mp_var_qty > 0:
                vals = {
                    'product_id': var_obj.id,
                    'product_temp_id': var_obj.product_tmpl_id.id,
                    'new_quantity': var_obj.mp_var_qty,
                    'location_id': location_id or False,  # Phase 2
                    'note': _("Initial Quantity."),
                    'state': "requested",
                }
                mp_product_stock = self.env['marketplace.stock'].create(vals)
                var_obj.is_var_initinal_qty_set = True
                mp_product_stock.auto_approve()

    def set_to_approved(self):
        """ Method to approve product variant"""
        for obj in self:
            obj.marketplace_status = "approved"
            obj.status = "approved"
            if not obj.is_var_initinal_qty_set and len(obj.product_variant_ids) > 1:
                obj.set_var_initial_qty()
        return True

    def set_to_pending(self):
        """ Method to change product variant status to pending"""
        for obj in self:
            if obj.marketplace_seller_id.auto_product_approve:
                obj.marketplace_status = "approved"
            else:
                obj.marketplace_status = "pending"
        return True

    def set_to_draft(self):
        """ Method to change product variant status to Draft"""
        for obj in self:
            obj.marketplace_status = "draft"
        return True

    def set_variant_to_rejected(self):
        for obj in self:
            if obj.marketplace_status in "approved":
                return {
                    'name': _('Product Variant Reject'),
                    'type': 'ir.actions.act_window',
                    'binding_view_types': 'form',
                    'context': {'default_mp_reason_type': 'product_reason'},
                    'view_mode': 'form',
                    'res_model': 'seller.status.reason.wizard',
                    'target': 'new',
                }

    def set_to_rejected(self):
        """ Method to change product variant status to Reject"""
        for obj in self:
            obj.marketplace_status = "rejected"
        return True

    @api.model_create_multi
    def create(self, vals_list):
        product_variant_ids = super(ProductProduct, self).create(vals_list)
        for product_variant in product_variant_ids:
            if product_variant.product_tmpl_id.marketplace_seller_id:
                if product_variant.product_tmpl_id.status != 'approved':
                    product_variant.sudo().write({'marketplace_status':product_variant.product_tmpl_id.status})
                else:
                    if product_variant.product_tmpl_id.marketplace_seller_id.auto_product_approve:
                        product_variant.sudo().write({'marketplace_status':'approved'})
                    else:
                        product_variant.sudo().write({'marketplace_status':'pending'})
        return product_variant_ids

    def toggle_website_published(self):
        """ Inverse the value of the field ``website_published`` on the records in ``self``. """
        for record in self:
            record.product_tmpl_id.toggle_website_published()

    def mp_action_view_sales(self):
        self.ensure_one()
        action = self.env.ref('odoo_marketplace.wk_seller_slae_order_line_action')
        tree_view_id = self.env.ref('odoo_marketplace.wk_seller_product_order_line_tree_view')
        form_view_id = self.env.ref('odoo_marketplace.wk_seller_product_order_line_form_view')
        return {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'binding_view_types': action.binding_view_types,
            'view_mode': action.view_mode,
            'views': [(tree_view_id.id, 'tree'), (form_view_id.id, 'form')],
            'target': action.target,
            'context': "{'default_product_id': " + str(self.id) + "}",
            'res_model': action.res_model,
            'domain': [('state', 'in', ['sale', 'done']), ('product_id', '=', self.id)],
        }

    def product_update_quantity(self):
        for product in self:
            product_stock = self.env['marketplace.stock'].search([('product_id','=',product.id),('state','=','requested')])
            if product_stock:
                raise ValidationError(_('Your inventory request is already in a pending state.'))
            else:
                return {
                    'name': _("Marketplace Stock"),
                    'type': 'ir.actions.act_window',
                    'res_model': 'marketplace.stock',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'target': 'new',
                }

    def _check_record_mp_access(self, user):
        '''
        This method check record access for seller
        '''
        # self.ensure_one()
        if self.exists() and self.marketplace_seller_id.id != user.partner_id.id:
            raise self.env['ir.rule']._make_access_error('read', self)


    def read(self, fields=None, load='_classic_read'):
        user = self.env.user
        super_access = self.env.su
        seller = user.check_user_is_draft_or_approved_seller()
        other_cond = self._context.get('params',{}).get('view_type','') == 'form' or len(self)==1
        if not super_access and seller and other_cond:
            for rec in self:
                rec._check_record_mp_access(user)
        res =  super().read(fields=fields, load=load)
        return res

    def action_open_product(self, productId):
        name = _("Product")
        res_model = 'product.product'
        view_mode = 'form'
        views = [
            (self.env.ref('odoo_marketplace.wk_seller_product_template_form_view').id, 'form'),
        ]
        action = {
            'name': name,
            'type': 'ir.actions.act_window',
            'view_mode': view_mode,
            'views': views, 
            'res_model': res_model,
            'res_id': productId,
            'target': 'current',
        }
        return action
