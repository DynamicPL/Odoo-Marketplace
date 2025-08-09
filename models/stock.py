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

from odoo import models, fields, api, _, SUPERUSER_ID
from lxml import etree
from datetime import datetime
from odoo.tools.translate import _
from odoo.exceptions import ValidationError
from .mp_tools import *
import logging
_logger = logging.getLogger(__name__)
from odoo.tools.sql import column_exists, create_column

class MarketplaceStock(models.Model):
    _name = "marketplace.stock"
    _inherit = ['mail.thread']
    _description = "Marketplace Stock"
    _rec_name = "product_id"

    @api.model
    def _set_product_template(self):
        """ Set default value for product template """
        if self._context.get('active_model') in ['product.template','product.product']:
            if self._context.get('active_model') == 'product.template':
                product_id = self.env['product.template'].browse(
                    self._context.get('active_id'))
                return product_id.id
            else:
                product_id = self.env['product.product'].browse(
                    self._context.get('active_id'))
                return product_id.product_tmpl_id.id if product_id else False
        return None

    @api.model
    def _set_product_id(self):
        """ Set default value for product"""
        if self._context.get('active_model') in ['product.template','product.product']:
            if self._context.get('active_model') == 'product.template':
                product_ids = self.env['product.product'].search(
                    [('product_tmpl_id', '=', self._context.get('active_id'))])
                return self.env['product.product'].browse(product_ids.ids[0]).id if product_ids else None
            else:
                product_obj = self.env['product.product'].search([('id', '=', self._context.get('active_id'))])
                if product_obj:
                    return product_obj.id
        return None


    @api.model
    def _get_product_location(self):
        """ Set default value for stock location"""
        if self._context.get('active_model') in ['product.template','product.product']:
            if self._context.get('active_model') == 'product.template':
                product_ids = self.env['product.product'].search(
                    [('product_tmpl_id', '=', self._context.get('active_id'))])
                product_obj = product_ids[0] if product_ids else None
            else:
                product_obj = self.env['product.product'].search([('id', '=', self._context.get('active_id'))])
            if product_obj:
                if product_obj.location_id:
                    return product_obj.location_id.id
                else:
                    return product_obj.marketplace_seller_id.get_seller_global_fields('location_id')
        return None
   
    product_temp_id = fields.Many2one(
        'product.template', string='Product Template', default=_set_product_template)
    product_id = fields.Many2one(
        'product.product', string='Product', default=_set_product_id)
    marketplace_seller_id = fields.Many2one(
        "res.partner", related="product_id.marketplace_seller_id", string="Seller", store=True)
    new_quantity = fields.Float('New Quantity on Hand', default=1, digits='Product Unit of Measure', required=True, help='This quantity is expressed in the Default Unit of Measure of the product.', copy=False)
    location_id = fields.Many2one(
        'stock.location', 'Location', required=True, default=_get_product_location)
    state = fields.Selection([("draft", "Draft"), ("requested", "Requested"), (
        "approved", "Approved"), ("rejected", "Rejected")], string="Status", default="draft", copy=False, tracking=True)
    note = fields.Text("Notes",  translate=True)
    product_variant_count = fields.Integer('Variant Count', related='product_temp_id.product_variant_count')

    @api.model
    def _read_group_fill_results( self, domain, groupby, remaining_groupbys,
        aggregated_fields, read_group_order=None):

        if groupby == 'state':
            for result in aggregated_fields:
                state = result['state']
                if state in ["approved", "rejected"]:
                    result['__fold'] = True
        return super(MarketplaceStock, self)._read_group_fill_results(domain, groupby, remaining_groupbys,
            aggregated_fields, read_group_order)

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id, view_type, **options)
        seller_group = self.env['ir.model.data'].check_object_reference(
            'odoo_marketplace', 'marketplace_seller_group')[1]
        officer_group = self.env['ir.model.data'].check_object_reference(
            'odoo_marketplace', 'marketplace_officer_group')[1]
        groups_ids = self.env.user.sudo().groups_id.ids
        if seller_group in groups_ids and officer_group not in groups_ids:
            marketplace_seller_id = self.env.user.sudo().partner_id.id

            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='product_temp_id']"):
                node.set(
                    'domain', "[('type', '=', 'product'), ('status','=','approved'),('marketplace_seller_id', '=', %s)]" % marketplace_seller_id)
            for node in doc.xpath("//field[@name='product_id']"):
                node.set(
                    'domain', "[('type', '=', 'product'), ('status','=','approved'),('marketplace_seller_id', '=', %s)]" % marketplace_seller_id)
            res['arch'] = etree.tostring(doc)
        return res


    @api.onchange('product_id')
    def onchange_product_id(self):
        """ Change location and product template on changing product"""
        self.ensure_one()
        if self.product_id:
            self.product_temp_id = self.product_id.product_tmpl_id.id
            self.location_id = self.product_id.marketplace_seller_id.get_seller_global_fields('location_id') or False,

    @check_mp_officer
    def approve(self):
        self._approve()

    def _approve(self):
        """ Approve inventory request"""
        for obj in self:
            if obj.state == "requested" and obj.product_id.status == "approved" and obj.product_id.marketplace_seller_id.state == "approved":
                obj.change_product_qty()
                obj.write({"state": "approved"})
            else:
                _logger.warning("warning !!MP inventory request can not be approved. Inventory request not in requested state or product is not approved or product seller is not approved.-")

    @check_mp_officer
    def reject(self):
        """ Reject inventory request"""
        for obj in self:
            if obj.state == "requested":
                obj.write({"state": "rejected"})

    @check_mp_officer
    def reject_wizard(self):
        for obj in self:
            return {
                'name': _('Inventory Request Reject'),
                'type': 'ir.actions.act_window',
                'binding_view_types': 'form',
                'context': {'default_mp_reason_type': 'inventory_reason'},
                'view_mode': 'form',
                'res_model': 'seller.status.reason.wizard',
                'target': 'new',
            }

    def set_2_draft(self):
        """ Set inventory state to draft"""
        for obj in self:
            obj.write({"state": "draft"})

    def request(self):
        """ Change inventory state to requested """
        for obj in self:
            if obj.new_quantity < 0:
                raise ValidationError(_("Quantity cannot be negative."))
            obj.state = "requested"
            obj.auto_approve()

    def auto_approve(self):
        """ Approve inventory state if auto_approve_qty field is true"""
        for obj in self:
            if obj.marketplace_seller_id.get_seller_global_fields('auto_approve_qty'):
                obj.with_user(SUPERUSER_ID)._approve()

    def change_product_qty(self):
        """ Create stock.quant record and change product quantity"""
        for template_obj in self:
            if not self.user_has_groups('stock.group_stock_manager'):
                raise UserError(_('Only inventory administrator has access to update the quantity.'))
            if template_obj.new_quantity < 0:
                raise ValidationError(_('Initial Quantity can not be negative'))
            vals = {
                'product_id': template_obj.product_id.id,
                'inventory_quantity' : template_obj.new_quantity,
                'location_id': template_obj.location_id.id,
            }
            self.env['stock.quant'].with_context(inventory_mode=True).create(vals).action_apply_inventory()

    def disable_seller_all_inventory_requests(self, seller_id):
        """ Reject seller all inventory requests"""
        if seller_id:
            inventory_obj = self.search(
                [("marketplace_seller_id", "=", seller_id), ('state', '!=', 'approved')])
            inventory_obj.reject()


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    marketplace_seller_id = fields.Many2one("res.partner", string="Seller")

    @api.model
    def _read_group_fill_results( self, domain, groupby, remaining_groupbys,
        aggregated_fields, read_group_order=None):

        if groupby == 'state':
            for result in aggregated_fields:
                state = result['state']
                if state in ["done", "cancel"]:
                    result['__fold'] = True
        return super(StockPicking, self)._read_group_fill_results(domain, groupby, remaining_groupbys,
            aggregated_fields, read_group_order)

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id, view_type, **options)
        is_seller = self.env.user.check_user_is_seller()
        if is_seller and result.get("toolbar", False):
            toolbar_dict = result.get("toolbar", {})
            if toolbar_dict.get("action"):
                toolbar_dict["action"] = []
            if toolbar_dict.get("relate"):
                toolbar_dict["relate"] = []
            for key in toolbar_dict:
                # Remove options from Print menu for seller
                if key == "print":
                    print_list = toolbar_dict[key]
                    action_id = self.env.ref('stock.action_report_delivery').id
                    for print_list_item in print_list:
                        if print_list_item["id"] != action_id:
                            print_list.remove(print_list_item)
            result["toolbar"] = toolbar_dict
        return result
    

    def get_pending_sale_order_line(self):
        sale_list = []
        for order in self.move_ids_without_package:
            if order.sale_line_id.marketplace_state == 'pending':
                sale_list.append(order.sale_line_id.id)
                
        if sale_list == []:
            raise ValidationError(_('All Sale Order Lines are approved.'))

        tree_view_id=self.env.ref('odoo_marketplace.wk_seller_product_order_line_tree_view').id
        return {
                    'name':_('Sale Order Line'),
                    'type':'ir.actions.act_window',
                    'res_model':'sale.order.line',
                    'domain':[('id','in',sale_list)],
                    'view_mode':'tree',
                    'views':[(tree_view_id,'tree')],
                    'res_id':False,
        }
            
           

    def button_validate(self):
        if self.marketplace_seller_id:
            for order in self.move_ids_without_package:
                if order.sale_line_id.marketplace_state == 'pending':
                    raise ValidationError(_('All sale order lines linked with this delivery order should be approved first.'))
        res = super().button_validate()
        return res

    # Replace the core method to resolved the ir.attachment modal create issue
    def _send_confirmation_email(self):
        for stock_pick in self.filtered(lambda p: p.company_id.stock_move_email_validation and p.picking_type_id.code == 'outgoing'):
            delivery_template_id = stock_pick.company_id.stock_mail_confirmation_template_id
            if stock_pick.marketplace_seller_id:
                stock_pick.sudo().with_context(force_send=True).message_post_with_source(delivery_template_id, email_layout_xmlid='mail.mail_notification_light')
            else:
                return super()._send_confirmation_email()
    
    def _put_in_pack(self, move_line_ids):
        res = super()._put_in_pack(move_line_ids)
        picking = move_line_ids.picking_id if move_line_ids else False
        if res and picking and picking.marketplace_seller_id:
            res.marketplace_seller_id = picking.marketplace_seller_id.id
        return res
    
    def action_see_packages(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_package_view")
        if self.env.user.check_user_is_seller():
            action = self.env["ir.actions.actions"]._for_xml_id("odoo_marketplace.mp_action_package_view_seller")
            form_view_id = self.env['ir.model.data']._xmlid_to_res_id(
            'odoo_marketplace.mp_view_quant_package_form')
            action['views'] = [(False, 'kanban'), (False, 'tree'), (form_view_id, 'form')]
        packages = self.move_line_ids.mapped('result_package_id')
        action['domain'] = [('id', 'in', packages.ids)]
        action['context'] = {'picking_id': self.id}
        return action


class StockMove(models.Model):
    _inherit = 'stock.move'

    marketplace_seller_id = fields.Many2one("res.partner", related="product_id.marketplace_seller_id", string="Seller", store=True)

    def _auto_init(self):
        if not column_exists(self.env.cr, "stock_move", "marketplace_seller_id"):
            create_column(self.env.cr, "stock_move", "marketplace_seller_id", "int4")
        return super()._auto_init()

    def _key_assign_picking(self):
        self.ensure_one()
        res = super(StockMove, self)._key_assign_picking()
        res = res + (self.product_id.marketplace_seller_id, )
        return res

    def _search_picking_for_assignation(self):
        """ Add marketplace seller id in search domain """
        self.ensure_one()
        picking = self.env['stock.picking'].search([
                ('group_id', '=', self.group_id.id),
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_dest_id.id),
                ('picking_type_id', '=', self.picking_type_id.id),
                ('marketplace_seller_id', '=', self.product_id.marketplace_seller_id.id),
                ('printed', '=', False),
                ('state', 'in', ['draft', 'confirmed', 'waiting', 'partially_available', 'assigned'])], limit=1)
        return picking

    def _get_new_picking_values(self):
        """ Return create values for new picking that will be linked with group
        of moves in self.
        """
        values = super(StockMove, self)._get_new_picking_values()
        sellers = self.mapped('marketplace_seller_id')
        seller = len(sellers) == 1 and sellers.id or False
        values.update({
            "marketplace_seller_id" : seller
        })
        return values

    def write(self, values):
        result = super(StockMove, self).write(values)
        for rec in self:
            if rec.state == "cancel":
                sol_obj = self.env["sale.order.line"].sudo().search([('order_id.name', '=', rec.origin), ('product_id', '=', rec.product_id.id)], limit=1)
                if sol_obj:
                    sol_obj.marketplace_state = "cancel"
            if rec.state == "done" and rec.sale_line_id:
                if rec.sale_line_id.qty_delivered == rec.sale_line_id.product_uom_qty:
                    rec.sale_line_id.sudo().marketplace_state = 'shipped'
                else:
                    rec.sale_line_id.sudo().marketplace_state = 'approved'
        return result
    
class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    marketplace_seller_id = fields.Many2one('res.partner', string="Marketplace Seller Id")
    

