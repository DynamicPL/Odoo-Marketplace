from odoo import api, fields, models, _
from odoo.exceptions import UserError


class UnpublishActionDetails(models.TransientModel):
    _name = "unpublish.action.details"
    _description = "Show Stats Details after mass publish"

    product_ids = fields.Many2many("product.template", string="Products")

    def unpublish_all_products(self):
        if self.product_ids:
            approved_products = self.product_ids.filtered(lambda o: o.status == "approved" and o.marketplace_seller_id and o.marketplace_seller_id.state == "approved")
            msg = "<p style='font-size: 15px'>" + _("Selected product(s) can't be unpublish, only approved product(s) will get unpublish.") + "<p>"
            approved_products.auto_unpublish()
            approved_products = self.product_ids.filtered(lambda o: o.status == "approved" and o.marketplace_seller_id)
            if approved_products:
                p_list = (', ').join(approved_products.mapped('name'))
                msg = "<p style='font-size: 15px'>" + _("Product(s) unpublished successfully:") +"<strong>" + p_list + "</strong></p>"
            return self.env["mp.wizard.message"].generated_message(msg, _("Unpublished Status"))
