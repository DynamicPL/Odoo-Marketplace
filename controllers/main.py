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

import werkzeug
from odoo.osv import expression
import odoo
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.addons.web.controllers.utils import ensure_db
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo import http
from odoo.http import request
import base64
from odoo.tools.translate import _
from odoo.exceptions import UserError
from odoo import SUPERUSER_ID
from odoo.addons.website_sale.controllers.main import TableCompute, QueryURL
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.website_mail.controllers.main import WebsiteMail
from odoo.addons.website.controllers.main import Website
from odoo.tools import lazy
from odoo.addons.web.controllers.action import Action
import logging
_logger = logging.getLogger(__name__)

PPG = 20  # Products Per Page
PPR = 4   # Products Per Row

SPG = 20  # Shops/sellers Per Page
SPR = 4   # Shops/sellers Per Row

marketplace_domain = [('sale_ok', '=', True), ('state', '=', "approved")]

class AuthSignupHome(Website):

    @http.route(website=True, auth="public", sitemap=False)
    def web_login(self, *args, **kw):
        """Redirect to dashboard if user has seller group or is already logged in"""
        ensure_db()
        response = super(AuthSignupHome, self).web_login(*args, **kw)
        if request.params['login_success']:
            current_user = request.env['res.users'].browse(request.uid)
            if not current_user.has_group('base.group_user') and current_user.has_group('odoo_marketplace.marketplace_draft_seller_group') and current_user.partner_id.seller:
                seller_dashboard_menu_id = request.env['ir.model.data'].check_object_reference('odoo_marketplace', 'wk_seller_dashboard')[1]
                redirect = "/web#menu_id=" + str(seller_dashboard_menu_id)
                return werkzeug.utils.redirect(redirect)
        return response

    def _signup_with_values(self, token, values):
        """Add extra data to signup values"""
        params = dict(request.params)
        is_seller = params.get('is_seller')
        country_id = params.get('country_id')
        if is_seller and is_seller == 'on':
            values.update({
                'is_seller' : True,
                'country_id' : int(country_id) if country_id else country_id,
                'url_handler' : params.get('url_handler'),
            })
        return super(AuthSignupHome, self)._signup_with_values(token, values)

    @http.route('/seller/signup', type='http', auth="public", website=True, sitemap=False)
    def seller_signup_form(self, *args, **kw):
        """Seller signup"""
        if not request.website.enable_marketplace:
            return request.render('http_routing.404')
        qcontext = self.get_auth_signup_qcontext()
        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()
        if kw.get("name", False):
            if 'error' not in qcontext and request.httprequest.method == 'POST':
                try:
                    self.do_signup(qcontext)
                    self.web_login(*args, **kw)
                    return website_marketplace_dashboard().account()
                except UserError as e:
                    qcontext['error'] = str(e)
                except (SignupError, AssertionError) as e:
                    if request.env["res.users"].sudo().search([("login", "=", qcontext.get("login"))]):
                        qcontext["error"] = _("Another user is already registered using this email address.")
                    else:
                        qcontext['error'] = _("Could not create a new account.")
            if kw.get("signup_from_seller_page", False) == "true":
                qcontext.pop("error")
                qcontext.update({"set_seller": True, 'hide_top_menu': True})
        return request.render('odoo_marketplace.mp_seller_signup', qcontext)


class website_marketplace_dashboard(http.Controller):

    @http.route(['/mp/terms/and/conditions'], type='json', auth="public", methods=['POST'], website=True)
    def mp_terms_and_conditions(self,**post):
        mp_t_and_c = post.get('mp_t_and_c',False)
        return request.env['ir.qweb']._render("odoo_marketplace.mp_t_and_c_modal_template", {'mp_t_and_c':mp_t_and_c,}, engine='ir.qweb')

    @http.route('/my/marketplace/become_seller', type='http', auth="public", website=True, sitemap=False)
    def become_seller(self, **post):
        """ Prepare values for become seller page"""
        if not request.website.enable_marketplace:
            return request.render('http_routing.404')
        partner = request.env.user.partner_id
        current_user = request.env.user
        if current_user.has_group("odoo_marketplace.marketplace_officer_group"):
            grp_name = "Manager" if current_user.has_group("odoo_marketplace.marketplace_manager_group") else "Officer"
            raise UserError(_("The user %s already has Marketplace %s group. Please remove it first to proceed further.",current_user.name,grp_name))
        if request.env.user.id == request.website.user_id.id:
            return request.redirect('/seller')
        if partner.user_id:
            sales_rep = partner.user_id
        else:
            sales_rep = False
        values = {
            'sales_rep': sales_rep,
            'company': request.website.company_id,
            'user': request.env.user,
            'countries': request.env['res.country'].sudo().search([]),
            'country' : partner.sudo().country_id if partner.sudo().country_id else partner.sudo().company_id.country_id,
        }
        if post.get('error'):
            values['error'] = "Could not create a new account."
        return request.render('odoo_marketplace.convert_user_into_seller',values)

    @http.route('/my/marketplace/seller', type='http', auth="public", website=True, sitemap=False)
    def submit_as_seller(self, **post):
        """Convert portal user to seller"""
        country_id = post.get('country_id',False)
        url_handler = post.get('url_handler',False)
        current_user = request.env.user
        seller_detail = request.env['res.partner'].sudo().search([('seller', '=', True),('url_handler','=',url_handler)])
        value ={}
        if not seller_detail and country_id and url_handler:
            value['error'] = False
            current_user.partner_id.write({
                'country_id': int(country_id),
                'url_handler':url_handler,
                'seller': True,
            })
            internal_group = request.env.ref('base.group_user')
            portal_group = request.env.ref('base.group_portal')
            if portal_group and internal_group:
                portal_group.sudo().write({"users": [(3, current_user.id, 0)]})
                internal_group.sudo().write({"users": [(4, current_user.id, 0)]})
            draft_seller_group_id = request.env['ir.model.data'].sudo().check_object_reference('odoo_marketplace', 'marketplace_draft_seller_group')[1]
            groups_obj = request.env["res.groups"].browse(draft_seller_group_id)
            if groups_obj:
                for group_obj in groups_obj:
                    group_obj.sudo().write({"users": [(4, current_user.id, 0)]})

            current_user.update_groups_for_mp_user(current_user)
        else:
            value['error'] = True
        return request.redirect_query('/my/marketplace/become_seller', query=value)

    @http.route('/my/marketplace', type='http', auth="public", website=True, sitemap=False)
    def account(self):
        """ Redirect to seller dashboard"""
        seller_dashboard_menu_id = request.env[
            'ir.model.data'].check_object_reference('odoo_marketplace', 'wk_seller_dashboard')[1]
        new_url = "/web#menu_id=" + str(seller_dashboard_menu_id)
        return request.redirect(new_url)


class MarketplaceSellerProfile(http.Controller):

    @http.route(['/profile/url/handler/vaidation'], type='json', auth="public", methods=['POST'], website=True, sitemap=False)
    def profile_url_validation(self, url_handler, **post):
        """Validate profile url"""
        model = post.get('model', False)
        url_handler = url_handler.lower()
        profile_or_shop_id = post.get('profile_or_shop_id',False)
        if model:
            if profile_or_shop_id:
                sameurl = request.env[model].sudo().search([('url_handler', '=', url_handler), ('id', '!=',int(profile_or_shop_id))])
            else:
                sameurl = request.env[model].sudo().search([('url_handler', '=', url_handler)])
        else:
            sameurl = request.env["res.partner"].sudo().search([('url_handler', '=', url_handler)])
        if len(sameurl) == 0:
            return True
        else:
            return False

    @http.route(['/seller/profile/<int:seller_id>',
        '/seller/profile/<int:seller_id>/page/<int:page>',
        '/seller/profile/<seller_url_handler>',
        '/seller/profile/<seller_url_handler>/page/<int:page>'],
        type='http', auth="public", website=True)
    def seller(self, seller_id=None, seller_url_handler=None, page=0, category=None, search='', ppg=False, **post):
        if not request.website.enable_marketplace or not request.website.mp_show_seller_list:
            return request.render('http_routing.404')
        seller = url = False
        uid, context, env = request.uid, dict(request.env.context), request.env
        if seller_url_handler:
            seller = request.env["res.partner"].sudo().search([("url_handler", "=", str(seller_url_handler))], limit=1)
            url = "/seller/profile/" + str(seller.url_handler)
        elif seller_id:
            seller = env['res.partner'].sudo().browse(seller_id)
            wk_name = seller.sudo().name.strip().replace(" ", "-")
            url = '/seller/profile/' + wk_name + '-' + str(seller.id)
        if not seller or not seller.seller:
            return request.render("http_routing.403")

        if seller and not seller.website_published:
            officer_group = env.ref('odoo_marketplace.marketplace_officer_group')
            manager_group = env.ref('odoo_marketplace.marketplace_manager_group')
            user_obj = env.user
            group_bool_val = [i in user_obj.groups_id.ids for i in (officer_group.id,manager_group.id)]
            group_exist = True in group_bool_val
            if not group_exist and user_obj.url_handler != seller.url_handler:
                return request.render("http_routing.403")
        if not ppg:
            ppg = request.env['website'].get_current_website().shop_ppg

        PPR = request.env['website'].get_current_website().shop_ppr
        if ppg:
            try:
                ppg = int(ppg)
            except ValueError:
                ppg = PPG
            post["ppg"] = ppg
        else:
            ppg = PPG

        if not context.get('pricelist'):
            pricelist = request.website._get_current_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = env['product.pricelist'].sudo().browse(context['pricelist'])

        ## calculating seller total sales order count
        sales_count = 0
        all_products = request.env['product.template'].sudo().search(
            [("marketplace_seller_id", "=", seller.sudo().id)])
        for prod in all_products.with_user(SUPERUSER_ID):
            sales_count += prod.sales_count

        attrib_list = request.httprequest.args.getlist('attrib')
        url_for_keep = url
        keep = QueryURL(url_for_keep, category=category and int(
            category), search=search, attrib=attrib_list)

        seller_product_ids = request.env["product.template"].search([("marketplace_seller_id", "=", seller.id)])

        product_count = request.env["product.template"].sudo().search_count([('sale_ok', '=', True), ('status', '=', "approved"), ("website_published", "=", True), ("id", "in", seller_product_ids.ids)])
        pager = request.website.pager(url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)
        products = env['product.template'].sudo().search([('sale_ok', '=', True), ('status', '=', "approved"), ("website_published", "=", True), ("marketplace_seller_id", "=", seller.id)], limit=ppg, offset=pager['offset'], order='website_published desc, website_sequence desc')

        from_currency = env['res.users'].sudo().browse(uid).company_id.currency_id
        to_currency = pricelist.currency_id
        compute_currency = lambda price: env['res.currency'].sudo()._compute(from_currency, to_currency, price)

        recommend_id = request.env['seller.recommendation'].search([('seller_id', '=', seller.id), ('customer_id', '=', request.env.user.partner_id.id)], limit=1)
        fiscal_position = request.env['website'].get_current_website().fiscal_position_id.sudo()
        products_prices = lazy(lambda: products._get_sales_prices(pricelist, fiscal_position))

        values = {
            'seller': seller,
            'main_object' : seller,
            'search': search,
            'rows': PPR,
            'bins': TableCompute().process(products, ppg, PPR),
            'ppg': ppg,
            'ppr': PPR,
            'pager': pager,
            'products': products,
            "keep": keep,
            'compute_currency': compute_currency,
            "pricelist": pricelist,
            "sales_count": sales_count,
            "already_recommend" : recommend_id.recommend_state if recommend_id else None,
            "product_count": int(product_count),
            'get_product_prices': lambda product: lazy(lambda: products_prices[product.id]),
        }
        website_sale_wishlist = request.env['ir.module.module'].sudo().search([('state', '=', 'installed'), ('name', '=', 'website_sale_wishlist')])
        if website_sale_wishlist:
            values['products_in_wishlist'] = request.env['product.wishlist'].current().product_id.product_tmpl_id
        return request.render("odoo_marketplace.mp_seller_profile", values)

    @http.route('/seller/profile/recently-product/', type='json', auth="public", website=True)
    def seller_profile_recently_product(self, seller_id, page=0, category=None, search='', ppg=False, **post):
        if not seller_id:
            return False
        uid, context, env = request.uid, dict(request.env.context), request.env
        url = "/seller/" + str(seller_id)
        seller_obj = env["res.partner"].sudo().browse(seller_id)
        recently_product = request.website.mp_recently_product

        page = 0
        category = None
        search = ''
        ppg = False

        if not ppg:
            ppg = request.env['website'].get_current_website().shop_ppg

        PPR = request.env['website'].get_current_website().shop_ppr
        if ppg:
            try:
                ppg = int(ppg)
            except ValueError:
                ppg = PPG
            post["ppg"] = ppg
        else:
            ppg = PPG

        if not context.get('pricelist'):
            pricelist = request.website._get_current_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = env['product.pricelist'].sudo().browse(context['pricelist'])

        attrib_list = request.httprequest.args.getlist('attrib')
        keep = QueryURL('/profile/', category=category and int(category),
                        search=search, attrib=attrib_list)
        recently_product_obj = request.env['product.template'].search([
                ('sale_ok', '=', True),
                ('status', '=', "approved"),
                ("website_published", "=", True),
                ("marketplace_seller_id", "=", seller_obj.id)
            ],
            order='create_date desc, website_published desc, website_sequence desc',
            limit=recently_product
        )
        product_count = len(recently_product_obj.ids)
        pager = request.website.pager(
            url=url, total=product_count, page=page, step=20, scope=7, url_args=post)
        product_ids = request.env['product.template'].search([("id", "in", recently_product_obj.ids)], limit=ppg, offset=pager[
                                                             'offset'], order='website_published desc, website_sequence desc')
        products = env['product.template'].browse(product_ids.ids)
        from_currency = env['res.users'].sudo().browse(uid).company_id.currency_id
        to_currency = pricelist.currency_id
        compute_currency = lambda price: env['res.currency'].sudo()._compute(from_currency, to_currency, price)

        fiscal_position = request.env['website'].get_current_website().fiscal_position_id.sudo()
        products_prices = lazy(lambda: products._get_sales_prices(pricelist, fiscal_position))

        values = {
            'rows': PPR,
            'bins': TableCompute().process(products, ppg, PPR),
            'ppg': ppg,
            'ppr': PPR,
            'pager': pager,
            'products': products,
            "keep": keep,
            'compute_currency': compute_currency,
            "pricelist": pricelist,
            'seller_obj': seller_obj,
            'get_product_prices': lambda product: lazy(lambda: products_prices[product.id]),
        }
        website_sale_wishlist = request.env['ir.module.module'].sudo().search([('state', '=', 'installed'), ('name', '=', 'website_sale_wishlist')])
        if website_sale_wishlist:
            values['products_in_wishlist'] = request.env['product.wishlist'].current().product_id.product_tmpl_id
        return request.env['ir.qweb']._render("odoo_marketplace.shop_recently_product", values, engine='ir.qweb')

    @http.route(['/marketplace/image/<int:partner_id>/<model_name>/<field_name>'], type='http', auth="public", website=True)
    def user_avatar(self, partner_id,model_name, field_name, **post):
        status, headers, content = request.env['ir.http'].binary_content(
            model=model_name, id=partner_id, field=field_name, default_mimetype='image/png', env=request.env(user=odoo.SUPERUSER_ID))

        if not content:
            img_path = odoo.modules.get_module_resource(
                'web', 'static/src/img', 'placeholder.png')
            with open(img_path, 'rb') as f:
                image = f.read()
            content = image.encode('base64')
        if status == 304:
            return werkzeug.wrappers.Response(status=304)
        image_base64 = base64.b64decode(content)
        headers.append(('Content-Length', len(image_base64)))
        response = request.make_response(image_base64, headers)
        response.status = str(status)
        return response

    def _get_search_order(self, post):
        # OrderBy will be parsed in orm and so no direct sql injection
        # id is added to be sure that order is a unique sort key
        return 'is_published desc,%s , id desc' % post.get('order', 'website_sequence desc')

    def _get_seller_search_domain(self, search):
        domain = [("website_published", "=", True), ("seller", '=', True), ("state", "=", "approved")]
        if search:
            for srch in search.split(" "):
                domain += [('name', 'ilike', srch)]
        return domain

    @http.route([
        '/sellers/list/',
        '/sellers/list/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=False)
    def load_mp_all_seller(self, page=0, search='', ppg=False, **post):
        if not request.website.enable_marketplace or not request.website.mp_show_seller_list:
            return request.render('http_routing.404')
        if not ppg:
            ppg = request.env['website'].get_current_website().shop_ppg

        PPR = request.env['website'].get_current_website().shop_ppr
        if ppg:
            try:
                ppg = int(ppg)
            except ValueError:
                ppg = SPG
            post["ppg"] = ppg
        else:
            ppg = SPG

        domain = self._get_seller_search_domain(search)
        keep = QueryURL('/sellers/list', search=search)

        url = "/sellers/list"
        if search:
            post["search"] = search

        seller_obj = request.env['res.partner']
        seller_count = seller_obj.sudo().search_count(domain)
        total_active_seller = seller_obj.sudo().search_count(self._get_seller_search_domain(""))
        pager = request.website.pager(url=url, total=seller_count, page=page, step=ppg, scope=7, url_args=post)
        seller_objs = seller_obj.sudo().search(domain, limit=ppg, offset=pager['offset'], order=self._get_search_order(post))

        values = {
            'search': search,
            'pager': pager,
            'seller_objs': seller_objs,
            'search_count': seller_count,  # common for all searchbox
            'bins': TableCompute().process(seller_objs, ppg, PPR),
            'ppg': ppg,
            'ppr': PPR,
            'rows': SPR,
            'keep': keep,
            'total_active_seller' : total_active_seller,
        }
        return request.render("odoo_marketplace.sellers_list", values)

    @http.route(['/seller/change_sequence'], type='json', auth="public")
    def change_sequence(self, id, sequence):
        seller_shop_obj = request.env['res.partner'].browse(id)
        if sequence == "top":
            seller_shop_obj.set_sequence_top()
        elif sequence == "bottom":
            seller_shop_obj.set_sequence_bottom()
        elif sequence == "up":
            seller_shop_obj.set_sequence_up()
        elif sequence == "down":
            seller_shop_obj.set_sequence_down()

    @http.route(['/seller/change_size'], type='json', auth="public")
    def change_size(self, id, x, y):
        seller_shop_obj = request.env['res.partner'].browse(id)
        return seller_shop_obj.write({'website_size_x': x, 'website_size_y': y})

    @http.route(['/seller/change_styles'], type='json', auth="public")
    def change_styles(self, id, style_id):
        seller_shop_obj = request.env['res.partner'].browse(id)

        remove = []
        active = False
        style_id = int(style_id)
        for style in seller_shop_obj.website_style_ids:
            if style.id == style_id:
                remove.append(style.id)
                active = True
                break

        style = request.env['seller.shop.style'].browse(style_id)

        if remove:
            seller_shop_obj.write({'website_style_ids': [(3, rid) for rid in remove]})
        if not active:
            seller_shop_obj.write({'website_style_ids': [(4, style.id)]})

class MarketplaceSellerShop(http.Controller):

    @http.route(['/seller/shop/<shop_url_handler>', '/seller/shop/<shop_url_handler>/page/<int:page>'], type='http', auth="public", website=True)
    def seller_shop(self, shop_url_handler, page=0, category=None, search='', ppg=False, **post):
        if not request.website.enable_marketplace or not request.website.mp_show_seller_shop_list:
            return request.render('http_routing.404')
        shop_obj = request.env["seller.shop"].sudo().search([("url_handler", "=", str(shop_url_handler))], limit=1)
        if not shop_obj:
            return False
        if not shop_obj.sudo().website_published and request.env.user.seller and request.env.user.url_handler != shop_obj.sudo().seller_id.url_handler:
            return request.render("http_routing.403")

        def _get_search_domain(search):
            domain = request.website.sale_product_domain()
            domain += [("marketplace_seller_id", "=",
                        shop_obj.sudo().seller_id.id)]

            if search:
                for srch in search.split(" "):
                    domain += [
                        '|', '|', '|', ('name', 'ilike',
                                        srch), ('description', 'ilike', srch),
                        ('description_sale', 'ilike', srch), ('product_variant_ids.default_code', 'ilike', srch)]
            product_obj = request.env['product.template'].sudo().search(domain)
            return request.env['product.template'].browse(product_obj.ids)

        uid, context, env = request.uid, dict(request.env.context), request.env
        url = "/seller/shop/" + str(shop_obj.url_handler)
        if search:
            post["search"] = search

        if not ppg:
            ppg = request.env['website'].get_current_website().shop_ppg

        PPR = request.env['website'].get_current_website().shop_ppr
        if ppg:
            try:
                ppg = int(ppg)
            except ValueError:
                ppg = PPG
            post["ppg"] = ppg
        else:
            ppg = PPG

        if not context.get('pricelist'):
            pricelist = request.website._get_current_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = env['product.pricelist'].sudo().browse(context['pricelist'])

        # Calculate seller total sales count
        sales_count = 0
        all_products = request.env['product.template'].sudo().search(
            [("marketplace_seller_id", "=", shop_obj.sudo().seller_id.id)])
        for prod in all_products.with_user(SUPERUSER_ID):
            sales_count += prod.sales_count

        attrib_list = request.httprequest.args.getlist('attrib')
        url_for_keep = '/seller/shop/' + str(shop_obj.url_handler)
        keep = QueryURL(url_for_keep, category=category and int(
            category), search=search, attrib=attrib_list)

        product_count = request.env["product.template"].sudo().search_count([('sale_ok', '=', True), ('status', '=', "approved"), ("website_published", "=", True), ("id", "in", shop_obj.sudo().seller_product_ids.ids)])
        pager = request.website.pager(url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)
        products = env['product.template'].sudo().search([('sale_ok', '=', True), ('status', '=', "approved"), ("website_published", "=", True), ("marketplace_seller_id", "=", shop_obj.sudo().seller_id.id), ("id", "in", shop_obj.sudo().seller_product_ids.ids)], limit=ppg, offset=pager['offset'], order='website_published desc, website_sequence desc')

        from_currency = env['res.users'].sudo().browse(uid).company_id.currency_id
        to_currency = pricelist.currency_id
        compute_currency = lambda price: env['res.currency'].sudo()._compute(from_currency, to_currency, price)
        shop_banner_url = request.website.image_url(shop_obj, 'shop_banner')

        fiscal_position = request.env['website'].get_current_website().fiscal_position_id.sudo()
        products_prices = lazy(lambda: products._get_sales_prices(pricelist, fiscal_position))

        values = {
            'shop_obj': shop_obj,
            'main_object': shop_obj, 
            'search': search,
            'rows': PPR,
            'bins': TableCompute().process(products if not search else _get_search_domain(search), ppg, PPR),
            'ppg': ppg,
            'ppr': PPR,
            'pager': pager,
            'products': products if not search else _get_search_domain(search),
            "keep": keep,
            'compute_currency': compute_currency,
            "pricelist": pricelist,
            'hide_pager': len(_get_search_domain(search)),
            'shop_banner_url': shop_banner_url,
            "sales_count": sales_count,
            "product_count": int(product_count),
            'get_product_prices': lambda product: lazy(lambda: products_prices[product.id]),
        }
        website_sale_wishlist = request.env['ir.module.module'].sudo().search([('state', '=', 'installed'), ('name', '=', 'website_sale_wishlist')])
        if website_sale_wishlist:
            values['products_in_wishlist'] = request.env['product.wishlist'].current().product_id.product_tmpl_id
        return request.render("odoo_marketplace.mp_seller_shop", values)

    @http.route(['/seller/shop/change_sequence'], type='json', auth="public")
    def change_sequence(self, id, sequence):
        seller_shop_obj = request.env['seller.shop'].browse(id)
        if sequence == "top":
            seller_shop_obj.set_sequence_top()
        elif sequence == "bottom":
            seller_shop_obj.set_sequence_bottom()
        elif sequence == "up":
            seller_shop_obj.set_sequence_up()
        elif sequence == "down":
            seller_shop_obj.set_sequence_down()

    @http.route(['/seller/shop/change_size'], type='json', auth="public")
    def change_size(self, id, x, y):
        seller_shop_obj = request.env['seller.shop'].browse(id)
        return seller_shop_obj.write({'website_size_x': x, 'website_size_y': y})

    @http.route('/seller/shop/recently-product/', type='json', auth="public", website=True)
    def seller_shop_recently_product(self, shop_id, page=0, category=None, search='', ppg=False, **post):
        uid, context, env = request.uid, dict(request.env.context), request.env
        url = "/seller/shop/" + str(shop_id)
        shop_obj = env["seller.shop"].sudo().browse(shop_id)
        recently_product = request.website.mp_recently_product

        page = 0
        category = None
        search = ''
        ppg = False

        if not ppg:
            ppg = request.env['website'].get_current_website().shop_ppg

        PPR = request.env['website'].get_current_website().shop_ppr
        if ppg:
            try:
                ppg = int(ppg)
            except ValueError:
                ppg = PPG
            post["ppg"] = ppg
        else:
            ppg = PPG

        if not context.get('pricelist'):
            pricelist = request.website._get_current_pricelist()
            context['pricelist'] = int(pricelist)
        else:
            pricelist = env['product.pricelist'].sudo().browse(context['pricelist'])

        attrib_list = request.httprequest.args.getlist('attrib')
        keep = QueryURL('/shop', category=category and int(category),
                        search=search, attrib=attrib_list)

        recently_product_obj = request.env['product.template'].search([('sale_ok', '=', True), ('status', '=', "approved"), ("website_published", "=", True), (
            "marketplace_seller_id", "=", shop_obj.seller_id.id), ("id", "in", shop_obj.sudo().seller_product_ids.ids)], order='create_date desc, website_published desc, website_sequence desc', limit=recently_product)
        product_count = len(recently_product_obj.ids)
        pager = request.website.pager(
            url=url, total=product_count, page=page, step=20, scope=7, url_args=post)
        product_ids = request.env['product.template'].search([("id", "in", recently_product_obj.ids)], limit=ppg, offset=pager[
                                                             'offset'], order='website_published desc, website_sequence desc')
        products = env['product.template'].browse(product_ids.ids)

        from_currency = env['res.users'].sudo().browse(uid).company_id.currency_id
        to_currency = pricelist.currency_id
        compute_currency = lambda price: env['res.currency'].sudo()._compute(from_currency, to_currency, price)

        fiscal_position = request.env['website'].get_current_website().fiscal_position_id.sudo()
        products_prices = lazy(lambda: products._get_sales_prices(pricelist, fiscal_position))

        values = {
            'rows': PPR,
            'bins': TableCompute().process(products, ppg, PPR),
            'ppg': ppg,
            'ppr': PPR,
            'pager': pager,
            'products': products,
            "keep": keep,
            'compute_currency': compute_currency,
            "pricelist": pricelist,
            'shop_obj': shop_obj,
            'get_product_prices': lambda product: lazy(lambda: products_prices[product.id]),
        }
        website_sale_wishlist = request.env['ir.module.module'].sudo().search([('state', '=', 'installed'), ('name', '=', 'website_sale_wishlist')])
        if website_sale_wishlist:
            values['products_in_wishlist'] = request.env['product.wishlist'].current().product_id.product_tmpl_id
        return request.env['ir.qweb']._render("odoo_marketplace.shop_recently_product", values, engine='ir.qweb')

    @http.route(['/seller', '/seller/login'], type='http', auth="public", website=True, sitemap=False)
    def mp_sell(self, redirect=None, **post):
        """Redirect to seller landing page """
        if not request.website.enable_marketplace or not request.website.mp_show_sell_menu_header and not request.website.mp_show_sell_menu_footer:
            return request.render('http_routing.404')
        uid, context, env = request.uid, dict(request.env.context), request.env
        ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return http.redirect_with_hash(redirect)

        if not request.uid:
            request.uid = odoo.SUPERUSER_ID

        values = request.params.copy()
        values.update({
            "hide_top_menu": True,
            "test": True,
            "signup_enabled": request.env['res.users']._get_signup_invitation_scope() == 'b2c',
        })
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            old_uid = request.uid
            uid = request.session.authenticate(request.session.db, request.params[
                                               'login'], request.params['password'])
            if uid is not False:
                request.params['login_success'] = True
                if not redirect:
                    redirect = '/web'
                return http.redirect_with_hash(redirect)
            request.uid = old_uid
            values['error'] = "Wrong login/password"
        return request.render("odoo_marketplace.wk_mp_seller_landing_page", values)

    @http.route(['/add/header/button'], type='json', auth="public", website=True)
    def add_header_button(self, **post):
        """Change seller signup button content"""
        signup_enabled = request.env['res.users']._get_signup_invitation_scope() == 'b2c'
        if not signup_enabled:
            return False
        route = ''
        btn_content = _('Open a Marketplace Store')
        if request.env.user._is_admin() or request.env.user == request.website.user_id:
            route = '/seller/signup'
        elif request.env.user.is_marketplace_user():
            route = '/my/marketplace'
            btn_content = _("Go to Marketplace Dashboard")
        else:
            route = '/my/marketplace/become_seller'
        return {"route":route, "btn_content":btn_content }

    def _get_search_order(self, post):
        # OrderBy will be parsed in orm and so no direct sql injection
        # id is added to be sure that order is a unique sort key
        return 'is_published desc,%s , id desc' % post.get('order', 'website_sequence desc')

    def _get_seller_shop_search_domain(self, search):
            """Seller shop search domain"""
            domain = [("website_published", "=", True)]

            if search:
                for srch in search.split(" "):
                    domain += [
                        '|', ('name', 'ilike',
                                        srch), ('description', 'ilike', srch)]
            return domain


    @http.route([
        '/seller/shops/list/',
        '/seller/shops/list/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=False)
    def load_mp_all_seller_shop(self, page=0, search='', ppg=False, **post):
        if not request.website.enable_marketplace or not request.website.mp_show_seller_shop_list:
            return request.render('http_routing.404')
        if not ppg:
            ppg = request.env['website'].get_current_website().shop_ppg or 20

        PPR = request.env['website'].get_current_website().shop_ppr or 4

        if ppg:
            try:
                ppg = int(ppg)
            except ValueError:
                ppg = SPG
            post["ppg"] = ppg
        else:
            ppg = SPG

        domain = self._get_seller_shop_search_domain(search)
        keep = QueryURL('/seller/shops/list', search=search)

        url = "/seller/shops/list"
        if search:
            post["search"] = search

        seller_shop_obj = request.env['seller.shop']
        seller_shop_count = seller_shop_obj.sudo().search_count(domain)
        pager = request.website.pager(url=url, total=seller_shop_count, page=page, step=ppg, scope=7, url_args=post)
        seller_shops = seller_shop_obj.sudo().search(domain, limit=ppg, offset=pager['offset'], order=self._get_search_order(post))

        values = {
            'search': search,
            'pager': pager,
            'seller_shops': seller_shops,
            'search_count': seller_shop_count,  # common for all searchbox
            'bins': TableCompute().process(seller_shops, ppg, PPR),
            'ppg': ppg,
            'ppr': PPR,
            'rows': SPR,
            'keep': keep,
        }
        return request.render("odoo_marketplace.seller_shop_list", values)

class SellerReview(http.Controller):

    @http.route(['/seller/review'], type='json', auth="public", website=True)
    def review(self, **post):
        if post.get('review') and post.get('title') and post.get('stars'):
            review_dict = {}
            review_dict['msg'] = post.get('review')
            review_dict['rating'] = int(post.get('stars'))
            review_dict['title'] = post.get('title')
            review_dict['marketplace_seller_id'] = post.get('seller_id')
            review_dict["partner_id"] = request.env.user.partner_id.id
            review_dict["website_published"] = request.website.mp_review_auto_publish
            review_obj = request.env['seller.review'].sudo().create(review_dict)
            message_to_publish = request.website.mp_message_to_publish
            if message_to_publish:
                return message_to_publish
            else:
                return "  Congratulation!!! your review has been submitted successfully."
        return "  Congratulation!!! your review has been submitted successfully."

    @http.route(['/seller/shop/change_styles'], type='json', auth="public")
    def change_styles(self, id, style_id):
        seller_shop_obj = request.env['seller.shop'].browse(id)

        remove = []
        active = False
        style_id = int(style_id)
        for style in seller_shop_obj.website_style_ids:
            if style.id == style_id:
                remove.append(style.id)
                active = True
                break

        style = request.env['seller.shop.style'].browse(style_id)

        if remove:
            seller_shop_obj.write({'website_style_ids': [(3, rid) for rid in remove]})
        if not active:
            seller_shop_obj.write({'website_style_ids': [(4, style.id)]})


    @http.route(['/seller/review/help'], type='json', auth="public", methods=['POST'], website=True)
    def review_help(self,  seller_review_id, review_help=0,  **post):
        review_help_obj = request.env['review.help']
        res = []
        if not seller_review_id:
            return False
        if review_help == 0:
            return False
        if seller_review_id and review_help:
            review_help_ids = request.env['review.help'].search(
                [('seller_review_id', '=', seller_review_id), ('customer_id', '=', request.env.user.partner_id.id)])
            if review_help_ids:
                review_help_id = review_help_obj.browse(review_help_ids[0])
                if review_help == 1:
                    review_help_ids[0].write({"review_help": "yes"})
                if review_help == -1:
                    review_help_ids[0].write({"review_help": "no"})
                if review_help == 2:
                    review_help_ids[0].write({"review_help": "no"})
                if review_help == -2:
                    review_help_ids[0].write({"review_help": "yes"})
            else:
                if review_help == 1:
                    review_help_obj.sudo().create(
                        {"customer_id": request.env.user.partner_id.id, "seller_review_id": seller_review_id, "review_help": "yes"})
                if review_help == -1:
                    review_help_obj.sudo().create(
                        {"customer_id": request.env.user.partner_id.id, "seller_review_id": seller_review_id, "review_help": "no"})
            review_obj = request.env['seller.review'].browse(seller_review_id)
            review_obj.sudo()._set_total_helpful()  # Call depends method manually
            review_obj.sudo()._set_total_not_helpful()  # Call depends method manually
            res.append(review_obj.helpful)
            res.append(review_obj.not_helpful)
        return res

    @http.route(['/seller/load/review'], type='json', auth="public", website=True)
    def load_seller_review(self, seller_id, offset=0, limit=False, sort_by="recent", filter_by=-1, **kwargs):
        seller_obj = request.env['res.partner']
        return_review_obj = seller_obj.sudo().fetch_active_review2(
            seller_id, int(offset), limit, sort_by, filter_by)
        values = {
            'seller_review_ids': return_review_obj,
            'seller': request.env['res.partner'].sudo().browse(seller_id),
        }
        return request.env['ir.qweb']._render("odoo_marketplace.wk_seller_review_template", values, engine='ir.qweb')

    @http.route(['/seller/load/review/count'], type='json', auth="public", website=True)
    def load_seller_review_count(self, seller_id, offset=0, limit=False, sort_by="recent", filter_by=-1, **kwargs):
        """Load seller review count on the basis of rating"""
        seller_obj = request.env['res.partner']
        return_seller_review_obj = seller_obj.sudo().fetch_active_review2(
            seller_id, int(offset), limit, sort_by, filter_by)
        if filter_by == -1:
            review_ids = request.env["seller.review"].search([('marketplace_seller_id', '=', seller_id), (
                'website_published', '=', True)], order="helpful desc" if sort_by == "most_helpful" else "create_date desc")
        if filter_by == 1:
            review_ids = request.env["seller.review"].search([('marketplace_seller_id', '=', seller_id), ('website_published', '=', True), (
                'rating', '=', 1)], order="helpful desc" if sort_by == "most_helpful" else "create_date desc")
        if filter_by == 2:
            review_ids = request.env["seller.review"].search([('marketplace_seller_id', '=', seller_id), ('website_published', '=', True), (
                'rating', '=', 2)], order="helpful desc" if sort_by == "most_helpful" else "create_date desc")
        if filter_by == 3:
            review_ids = request.env["seller.review"].search([('marketplace_seller_id', '=', seller_id), ('website_published', '=', True), (
                'rating', '=', 3)], order="helpful desc" if sort_by == "most_helpful" else "create_date desc")
        if filter_by == 4:
            review_ids = request.env["seller.review"].search([('marketplace_seller_id', '=', seller_id), ('website_published', '=', True), (
                'rating', '=', 4)], order="helpful desc" if sort_by == "most_helpful" else "create_date desc")
        if filter_by == 5:
            review_ids = request.env["seller.review"].search([('marketplace_seller_id', '=', seller_id), ('website_published', '=', True), (
                'rating', '=', 5)], order="helpful desc" if sort_by == "most_helpful" else "create_date desc")
        return [len(return_seller_review_obj), len(review_ids)]

    @http.route(['/seller/recommend'], type='json', auth="public", website=True)
    def seller_recommend(self, seller_id, recommend_state="no", **kwargs):
        recommend_obj = request.env['seller.recommendation']
        if not seller_id:
            return False

        sol_objs = request.env["sale.order.line"].sudo().search(
            [("product_id.marketplace_seller_id", "=", seller_id), ("order_id.partner_id", "=", request.env.user.partner_id.id), ("order_id.state", "in", ["sale", "done"])])

        if len(sol_objs.ids) == 0:
            return_message = _(
                "You have to purchase a product of this seller first.")
            return return_message

        recommend_ids = recommend_obj.search(
            [('seller_id', '=', seller_id), ('customer_id', '=', request.env.user.partner_id.id)])
        if recommend_ids:
            for rec in recommend_ids:
                rec.sudo().write({"recommend_state": recommend_state})
        else:
            recommend_obj.sudo().create({"customer_id": request.env.user.partner_id.id,
                                         "seller_id": seller_id, "recommend_state": recommend_state})
        return True

    @http.route(['/seller/review/check'], type='json', auth="public", website=True)
    def check_seller_review(self, seller_id, **kwargs):
        """Check review limit of customer"""
        return_message = ""
        sol_objs = request.env["sale.order.line"].sudo().search(
            [("product_id.marketplace_seller_id", "=", seller_id), ("order_id.partner_id", "=", request.env.user.partner_id.id), ("order_id.state", "in", ["sale", "done"])])
        for_seller_total_review_obj = request.env["seller.review"].sudo().search(
            [('marketplace_seller_id', '=', seller_id), ('partner_id', '=', request.env.user.partner_id.id)])

        # This code must be used in create of review
        if len(sol_objs.ids) == 0:
            return_message = _(
                "You have to purchase a product of this seller first.")
            return return_message
        elif len(for_seller_total_review_obj.ids) >= len(sol_objs.ids):
            return_message = _(
                "According to your purchase your review limit is over.")
            return return_message
        else:
            return True

class TrackSol(http.Controller):

    @http.route('/track/sol', type='json', auth="public", website=True)
    def track_order_line(self, sol_id, **kwargs):
        """Provide order line marketplace state information """
        if not sol_id:
            return False
        values = {
            'sol_id': request.env["sale.order.line"].sudo().browse(sol_id),
        }
        return request.env['ir.qweb']._render("odoo_marketplace.marketplace_order_line_info", values, engine='ir.qweb')

class MarketplaceMail(http.Controller):

    @http.route(['/marketplace_mail/post/json'], type='json', auth='public', website=True)
    def mp_chatter_json(self, res_model='', res_id=None, message='', **kw):
        res_id = int(res_id) if res_id else res_id
        data = WebsiteMail().chatter_json(res_model, res_id, message, **kw)
        if data:
            return request.env['ir.qweb']._render("odoo_marketplace.mp_chatter_mail_append", data, engine='ir.qweb')
        else:
            return False

class WKsellerMP(http.Controller):

    @http.route(['/wk/check/mp/seller'], type='json', auth="public", methods=['POST'], website=True)
    def wk_check_mp_seller(self, **post):
        return request.env.user.check_user_is_draft_or_approved_seller()


class PortalAccount(CustomerPortal):

    @http.route(['/my/invoices', '/my/invoices/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_invoices(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        domain = [('partner_id', '=', request.env.user.partner_id.id)]
        if request.env.user.has_group('odoo_marketplace.marketplace_manager_group') or request.env.user.has_group('odoo_marketplace.marketplace_officer_group'):
            values = self._prepare_my_invoices_values(page, date_begin, date_end, sortby, filterby)
        else:
            values = self._prepare_my_invoices_values(page, date_begin, date_end, sortby, filterby,domain)
        pager = portal_pager(**values['pager'])
        invoices = values['invoices'](pager['offset'])
        request.session['my_invoices_history'] = invoices.ids[:100]
        values.update({
                'invoices': invoices,
                'pager': pager,
        })
        return request.render("account.portal_my_invoices", values)
    
    def _prepare_home_portal_values(self, counters):
        """Values for /my & /my/home routes template rendering.
        Includes the record count for the displayed badges.
        where 'coutners' is the list of the displayed badges
        and so the list to compute.
        """
        values = super()._prepare_home_portal_values(counters)
        domain = [('partner_id', '=', request.env.user.partner_id.id)]
        domain = expression.AND([
        domain or [],
        self._get_invoices_domain(),
        ])
        if request.env.user.has_group('odoo_marketplace.marketplace_manager_group') or request.env.user.has_group('odoo_marketplace.marketplace_officer_group'):
            if 'invoice_count' in counters:
                invoice_count = request.env['account.move'].search_count(self._get_invoices_domain()) \
                    if request.env['account.move'].check_access_rights('read', raise_exception=False) else 0
                values['invoice_count'] = invoice_count
            return values
        else:
            if 'invoice_count' in counters:
                invoice_count = request.env['account.move'].search_count(domain) \
                    if request.env['account.move'].check_access_rights('read', raise_exception=False) else 0
                values['invoice_count'] = invoice_count
            return values

class ActionInherit(Action):

    def get_allowed_module_resource(self):
        allowed_models = ['odoo_marketplace']
        return allowed_models

    @http.route('/web/action/load', type='json', auth="user")
    def load(self, action_id, additional_context=None):
        res = super(ActionInherit, self).load(action_id=action_id, additional_context=additional_context)
        if res and res.get('type') == 'ir.actions.act_window' and request.env.user.check_user_is_draft_or_approved_seller():
            allowed_module_resources = self.get_allowed_module_resource() or []
            xml_id = res.get('xml_id')
            module_name = xml_id.split('.')[0] if xml_id else False
            if module_name in allowed_module_resources:
                return res
            else:
                return False
        else:
            return res


class MpAnalyticsDashboard(http.Controller):

    #=== TOP SALES DASHBOARD DETAILS === #

    @http.route(["/get/dashboard/card/details"], type="json", auth="user", methods=["POST"], website=True,)
    def get_sales_dashboard_details(self, **post):

        dashboard_obj = request.env['marketplace.dashboard']
        sales_data =  dashboard_obj.get_dashboard_card_details(post)
        currency = request.website.company_id.currency_id.symbol

        return {
            "sol_count": sales_data["sol_count"],
            "total_sale_amount": sales_data["total_sale_amount"],
            "currency": currency,
            "admin_commission": sales_data["admin_earning"],
            "total_mp_products": sales_data["total_mp_products"],
            "initialDate": sales_data["initial_date"],
            "finalDate": sales_data["final_date"],
        }
    
    #=== SALES DATA ===#

    @http.route("/get/sales/data", type="json", auth="user", methods=["POST"], website=True)
    def get_sales_data(self, **post):

        dashboard_obj = request.env['marketplace.dashboard']
        sales_data =  dashboard_obj.get_dashboard_sales_data(post)
        currency = request.website.company_id.currency_id.symbol

        return {
            "days_values": sales_data["days_values"],
            "days_labels": sales_data["days_labels"],
            "months_labels": sales_data["months_labels"],
            "months_values": sales_data["months_values"],
            "years_labels": sales_data["years_labels"],
            "years_values": sales_data["years_values"],
            "currency": currency,
        }

    #=== TOTAL ORDERS ===#

    @http.route("/get/total/orders", type="json", auth="user", methods=["POST"], website=True)
    def getTotalOrders(self, **post):
        
        dashboard_obj = request.env['marketplace.dashboard']
        total_orders_data =  dashboard_obj.get_dashboard_total_orders(post)

        return {
            "days_labels": total_orders_data["days_labels"],
            "days_values": total_orders_data["days_values"],
            "months_labels": total_orders_data["months_labels"],
            "months_values": total_orders_data["months_values"],
            "years_labels": total_orders_data["years_labels"],
            "years_values": total_orders_data["years_values"],
        }
    
    #=== ACTIVE & REGISTERED SELLERS ===#

    @http.route("/get/active/sellers", type="json", auth="user", methods=["POST"], website=True)
    def get_active_sellers(self, **post):
        
        dashboard_obj = request.env['marketplace.dashboard']
        active_registered_sellers_data =  dashboard_obj.get_dashboard_active_registered_sellers(post)

        return {
            "isAdmin": active_registered_sellers_data["isAdmin"],
            "days_values": active_registered_sellers_data["days_values"],
            "reg_days_values": active_registered_sellers_data["reg_days_values"],
            "days_labels": active_registered_sellers_data["days_labels"],
            "active_months_labels": active_registered_sellers_data["active_months_labels"],
            "active_months_values": active_registered_sellers_data["active_months_values"],
            "registered_months_labels": active_registered_sellers_data["registered_months_labels"],
            "registered_months_values": active_registered_sellers_data["registered_months_values"],
            "active_years_labels": active_registered_sellers_data["active_years_labels"],
            "active_years_values": active_registered_sellers_data["active_years_values"],
            "registered_years_labels": active_registered_sellers_data["registered_years_labels"],
            "registered_years_values": active_registered_sellers_data["registered_years_values"],
        }

    #=== TOP PERFORMING SELLER ===#

    @http.route("/get/top/performing/sellers", type="json", auth="user", methods=["POST"], website=True)
    def get_top_performing_sellers(self, **post):

        dashboard_obj = request.env['marketplace.dashboard']
        top_perform_seller_data =  dashboard_obj.get_dashboard_top_perform_sellers(post)
        currency = request.website.company_id.currency_id.symbol

        return {
            'isAdmin': top_perform_seller_data["is_admin"],
            'sellers': top_perform_seller_data["sellers"],
            'seller_ids': top_perform_seller_data["seller_ids"],
            'order_count': top_perform_seller_data["order_count"],
            'currency': currency,
        }

    #=== TOP SELLING PRODUCTS ===#

    @http.route("/get/top/products", type="json", auth="user", methods=["POST"], website=True)
    def get_top_products(self, **post):

        dashboard_obj = request.env['marketplace.dashboard']
        top_products_data =  dashboard_obj.get_dashboard_top_products(post)

        return {
            "top_products": top_products_data["top_products"],
        }
    
    #=== OVERALL SELLERS RATING ===#

    @http.route("/get/seller/rating", type="json", auth="user", methods=["POST"], website=True)
    def get_seller_ratings(self, **post):\
        
        dashboard_obj = request.env['marketplace.dashboard']
        seller_rating_data =  dashboard_obj.get_dashboard_seller_ratings(post)

        return{
            "total_reviews": seller_rating_data["total_reviews"],
            "percentage_value": seller_rating_data["percentage_value"],
            "average_rating": seller_rating_data["average_rating"],
            "top_seller_ratings": seller_rating_data["top_seller_ratings"],
            "rating_values": seller_rating_data["rating_values"],
            "rating_labels": seller_rating_data["rating_labels"]
        }
    
    #=== BEST SELLING PRODUCT (SELLER) ===#
    
    @http.route("/seller/best/selling/product", type="json", auth="user", methods=["POST"], website=True)
    def get_seller_best_selling_prod(self, **post):

        dashboard_obj = request.env['marketplace.dashboard']
        seller_product_data =  dashboard_obj.get_dashboard_seller_best_selling_product(post)

        return {
            "isSeller": seller_product_data['isSeller'],
            "seller_name": seller_product_data['name'],
            "best_selling_label": seller_product_data["best_selling_label"],
            "best_selling_data": seller_product_data["best_selling_data"],
            "best_selling_prod_ids": seller_product_data["best_selling_prod_ids"]
        }
