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
from datetime import datetime, timedelta
import calendar
from collections import defaultdict
import logging
_logger = logging.getLogger(__name__)


class marketplace_dashboard(models.Model):
    _name = "marketplace.dashboard"
    _description = "Marketplace Dashboard"

    def is_user_seller(self):
        # Works with single id
        seller_group = self.env['ir.model.data'].check_object_reference(
            'odoo_marketplace', 'marketplace_draft_seller_group')[1]
        manager_group = self.env['ir.model.data'].check_object_reference(
            'odoo_marketplace', 'marketplace_officer_group')[1]
        groups_ids = self.env.user.sudo().groups_id.ids
        if seller_group in groups_ids and manager_group in groups_ids:
            return False
        if seller_group in groups_ids and manager_group not in groups_ids:
            return True

    def _is_seller_or_manager(self):
        for rec in self:
            is_seller = False
            if rec._uid:
                seller_groups = self.env.ref('odoo_marketplace.marketplace_seller_group')
                manager_group = self.env.ref('odoo_marketplace.marketplace_officer_group')
                if rec._uid in seller_groups.users.ids:
                    is_seller = True
                if rec._uid in manager_group.users.ids:
                    is_seller = False
            rec.is_seller = is_seller

    def _get_new_count(self):
        """ Calculate record for new state """
        for rec in self:
            if rec.state == 'order':
                if rec.is_seller:
                    user_obj = self.env['res.users'].browse(self._uid)
                    obj = self.env['sale.order.line'].search(
                        [('state','!=','draft'), ('marketplace_seller_id', '=',user_obj.partner_id.id), ('marketplace_state', '=', 'new')])
                else:
                    obj = self.env['sale.order.line'].search(
                        [('state','!=','draft'), ('marketplace_seller_id', '!=', False), ('marketplace_state', '=', 'new')])
                rec.count_product_new = len(obj)
            elif rec.state == 'payment':
                obj = self.env['seller.payment'].search(
                    [('seller_id', '!=', False), ('state', '=', 'draft'), ('payment_mode','=','seller_payment')])
                rec.count_product_new = len(obj)
            else:
                rec.count_product_new = 0

    def _get_approved_count(self):
        """ Calculate count of Approved records on dashboard"""
        for rec in self:
            if rec.state == 'product':
                if rec.is_user_seller():
                    obj = self.env['product.template'].search(
                        [('marketplace_seller_id.user_ids', '=', self._uid), ('status', '=', 'approved')])
                else:
                    obj = self.env['product.template'].search(
                        [('marketplace_seller_id', '!=', False), ('status', '=', 'approved')])
                rec.count_product_approved = len(obj)
            elif rec.state == 'seller':
                obj = self.env['res.partner'].search(
                    [('seller', '=', True), ('state', '=', 'approved')])
                rec.count_product_approved = len(obj)
            elif rec.state == 'order':
                if rec.is_seller:
                    user_obj = self.env['res.users'].browse(rec._uid)
                    obj = self.env['sale.order.line'].search(
                        [('marketplace_seller_id', '=',user_obj.partner_id.id), ('marketplace_state', '=', 'approved'),('state', 'not in', ('draft', 'sent'))])
                else:
                    obj = self.env['sale.order.line'].search(
                        [('marketplace_seller_id', '!=', False), ('marketplace_state', '=', 'approved'),('state', 'not in', ('draft', 'sent'))])
                rec.count_product_approved = len(obj)
            elif rec.state == 'payment':
                obj = self.env['seller.payment'].search(
                    [('seller_id', '!=', False), ('state', '=', 'confirm'), ('payment_mode','=','seller_payment')])
                rec.count_product_approved = len(obj)
            elif rec.state == 'stock':
                if rec.is_seller:
                    user_obj = self.env['res.users'].browse(rec._uid)
                    obj = self.env['marketplace.stock'].search(
                        [('marketplace_seller_id', '=',user_obj.partner_id.id), ('state', '=', 'approved')])
                else:
                    obj = self.env['marketplace.stock'].search(
                        [("marketplace_seller_id","!=",False), ('state', '=', 'approved')])
                rec.count_product_approved = len(obj)
            else:
                rec.count_product_approved = 0

    def _get_pending_count(self):
        """ Calculate count of pending records on dashboard"""
        for rec in self:
            if rec.state == 'product':
                if rec.is_user_seller():
                    obj = self.env['product.template'].search(
                        [('marketplace_seller_id.user_ids', '=', rec._uid), ('status', '=', 'pending')])
                else:
                    obj = self.env['product.template'].search(
                        [('marketplace_seller_id', '!=', False), ('status', '=', 'pending')])
                rec.count_product_pending = len(obj)
            elif rec.state == 'seller':
                obj = self.env['res.partner'].search(
                    [('seller', '=', True), ('state', '=', 'pending')])
                rec.count_product_pending = len(obj)
            elif rec.state == 'order':
                user_obj = self.env['res.users'].browse(rec._uid)
                if rec.is_seller:
                    obj = self.env['sale.order.line'].search(
                        [('marketplace_seller_id', '=',user_obj.partner_id.id), ('marketplace_state', '=', 'pending'),('state', 'not in', ('draft', 'sent'))])
                else:
                    obj = self.env['sale.order.line'].search(
                        [('marketplace_seller_id', '!=', False), ('marketplace_state', '=', 'pending'),('state', 'not in', ('draft', 'sent'))])
                rec.count_product_pending = len(obj)
            elif rec.state == 'payment':
                obj = self.env['seller.payment'].search(
                    [('seller_id', '!=', False), ('state', '=', 'requested'), ('payment_mode','=','seller_payment')])
                rec.count_product_pending = len(obj)
            elif rec.state == 'stock':
                if rec.is_seller:
                    user_obj = self.env['res.users'].browse(rec._uid)
                    obj = self.env['marketplace.stock'].search(
                        [('marketplace_seller_id', '=',user_obj.partner_id.id), ('state', '=', 'requested')])
                else:
                    obj = self.env['marketplace.stock'].search(
                        [("marketplace_seller_id","!=",False), ('state', '=', 'requested')])
                rec.count_product_pending = len(obj)
            else:
                rec.count_product_pending = 0

    def _get_rejected_count(self):
        """ Calculate count of rejected records on dashboard"""
        for rec in self:
            if rec.state == 'product':
                if rec.is_user_seller():
                    obj = self.env['product.template'].search(
                        [('marketplace_seller_id.user_ids', '=', rec._uid), ('status', '=', 'rejected')])
                else:
                    obj = self.env['product.template'].search(
                        [('marketplace_seller_id', '!=', False), ('status', '=', 'rejected')])
                rec.count_product_rejected = len(obj)
            elif rec.state == 'seller':
                obj = self.env['res.partner'].search(
                    [('seller', '=', True), ('state', '=', 'denied')])
                rec.count_product_rejected = len(obj)
            elif rec.state == 'order':
                user_obj = self.env['res.users'].browse(rec._uid)
                if rec.is_seller:
                    obj = self.env['sale.order.line'].search(
                        [('marketplace_seller_id', '=',user_obj.partner_id.id), ('marketplace_state', '=', 'shipped'),('state', 'not in', ('draft', 'sent'))])
                else:
                    obj = self.env['sale.order.line'].search(
                        [('marketplace_seller_id', '!=', False), ('marketplace_state', '=', 'shipped'),('state', 'not in', ('draft', 'sent'))])
                rec.count_product_rejected = len(obj)
            elif rec.state == 'payment':
                obj = self.env['seller.payment'].search(
                    [('seller_id', '!=', False), ('state', '=', 'canceled'), ('payment_mode','=','seller_payment') ])
                rec.count_product_rejected = len(obj)
            elif rec.state == 'stock':
                if rec.is_seller:
                    user_obj = self.env['res.users'].browse(rec._uid)
                    obj = self.env['marketplace.stock'].search(
                        [('marketplace_seller_id', '=',user_obj.partner_id.id), ('state', '=', 'rejected')])
                else:
                    obj = self.env['marketplace.stock'].search(
                        [("marketplace_seller_id","!=",False), ('state', '=', 'rejected')])
                rec.count_product_rejected = len(obj)
            else:
                rec.count_product_rejected = 0


    def _get_cancelled_count(self):
        """ Calculate count of cancelled records on dashboard"""
        for rec in self:
            if rec.state == 'order':
                user_obj = self.env['res.users'].browse(rec._uid)
                if rec.is_seller:
                    obj = self.env['sale.order.line'].search(
                        [('marketplace_seller_id', '=',user_obj.partner_id.id), ('marketplace_state', '=', 'cancel'),('state', 'not in', ('draft', 'sent'))])
                else:
                    obj = self.env['sale.order.line'].search(
                        [('marketplace_seller_id', '!=', False), ('marketplace_state', '=', 'cancel'),('state', 'not in', ('draft', 'sent'))])
                rec.count_product_cancelled = len(obj)
            else:
                rec.count_product_cancelled = 0

    def _get_done_count(self):
        """ Calculate count of done records on dashboard"""
        for rec in self:
            if rec.state == 'order':
                if rec.is_seller:
                    user_obj = self.env['res.users'].browse(rec._uid)
                    obj = self.env['sale.order.line'].search(
                        [('marketplace_seller_id', '=',user_obj.partner_id.id), ('marketplace_state', '=', 'done'),('state', 'not in', ('draft', 'sent'))])
                else:
                    obj = self.env['sale.order.line'].search(
                        [('marketplace_seller_id', '!=', False), ('marketplace_state', '=', 'done'),('state', 'not in', ('draft', 'sent'))])
                rec.count_product_done = len(obj)
            elif rec.state == 'payment':
                obj = self.env['seller.payment'].search(
                    [('seller_id', '!=', False), ('state', '=', 'posted'), ('payment_mode','=','seller_payment')])
                rec.count_product_done = len(obj)
            else:
                rec.count_product_done = 0


    count_product_done = fields.Integer(compute='_get_done_count')
    color = fields.Integer(string='Color Index')
    name = fields.Char(string="Name", translate=True)
    state = fields.Selection(
        [('product', 'Product'), ('seller', 'Seller'), ('order', 'Order'), ('payment', 'Payment'),('stock', 'Stock')])
    count_product_new = fields.Integer(compute='_get_new_count')
    count_product_approved = fields.Integer(compute='_get_approved_count')
    count_product_pending = fields.Integer(compute='_get_pending_count')
    count_product_rejected = fields.Integer(compute='_get_rejected_count')
    count_product_cancelled = fields.Integer(compute='_get_cancelled_count')
    is_seller = fields.Boolean(compute="_is_seller_or_manager")

    ########################### ANALYTICS DASHBOARD METHODS ###########################

    # === SALES CARD DATA---START ===#
    def get_dashboard_card_details(self, post):
        select_value = post.get("selectValue")
        custom_initial_date = post.get("initialDate")
        custom_final_date = post.get("finalDate")

        date_range, sale_domain, payment_domain, total_product_domain, admin_commission_domain = self._prepare_date_range(
            select_value, custom_initial_date, custom_final_date)

        return self._execute_dashboard_queries(date_range, sale_domain, payment_domain, total_product_domain, admin_commission_domain)

    def _prepare_date_range(self, select_value, custom_initial_date, custom_final_date):
        if not select_value:
            return (None, None), [], [], [], []

        is_custom = select_value == "custom"
        select_value = int(select_value) - 1 if not is_custom else None

        current_date = datetime.now() if not is_custom else custom_final_date
        prev_date = current_date - \
            timedelta(days=select_value) if not is_custom else custom_initial_date

        if is_custom:
            initial_date = custom_initial_date
            final_date = custom_final_date
        else:
            prev_date = prev_date.replace(
                hour=0, minute=0, second=0, microsecond=0)
            initial_date = prev_date.strftime("%Y-%m-%d %H:%M:%S")
            final_date = current_date.strftime("%Y-%m-%d %H:%M:%S")

        if initial_date and final_date:
            date_filter = f"create_date >= '{initial_date}' AND create_date <= '{final_date}'"
            sale_domain = [
                f"sol.create_date >= '{initial_date}' AND sol.create_date <= '{final_date}'"]
            payment_domain = total_product_domain = [date_filter]
            admin_commission_domain = [
                f"aml.create_date >= '{initial_date}' AND aml.create_date <= '{final_date}'"]

        else:
            sale_domain = payment_domain = total_product_domain = admin_commission_domain = []

        return (
            (initial_date, final_date),
            sale_domain, payment_domain,
            total_product_domain,
            admin_commission_domain
        )

    def _execute_dashboard_queries(self, date_range, sale_domain, payment_domain, total_product_domain, admin_commission_domain):
        initial_date, final_date = date_range
        is_admin = self.env.user.has_group(
            "odoo_marketplace.marketplace_manager_group")
        partner = self.env.user.partner_id

        where_clause = " AND ".join(sale_domain) or "TRUE"
        where_clause_payment = " AND ".join(payment_domain) or "TRUE"
        where_clause_total_product = " AND ".join(
            total_product_domain) or "TRUE"
        where_clause_admin_commission = " AND ".join(
            admin_commission_domain) or "TRUE"

        seller_condition = f"= {partner.id}" if not is_admin else "IS NOT NULL"

        sale_order_query = f"""
            SELECT COUNT(*)
            FROM sale_order AS so
            JOIN sale_order_line AS sol 
            ON sol.order_id = so.id
            WHERE sol.marketplace_state IN ('shipped', 'done') 
            AND sol.marketplace_seller_id {seller_condition} 
            AND {where_clause}
        """

        total_products_query = f"""
            SELECT COUNT(*)
            FROM product_template
            WHERE marketplace_seller_id {seller_condition}
            AND status = 'approved'
            AND {where_clause_total_product}
            AND active = TRUE
        """

        total_sale_query = f"""
            SELECT SUM(price_total)
            FROM sale_order_line
            WHERE marketplace_state IN ('shipped', 'done')
            AND marketplace_seller_id {seller_condition} 
            AND {where_clause_payment}
        """

        admin_earning_query = f"""
            SELECT SUM(aml.seller_commission) AS total_commission
            FROM account_move_line aml
            JOIN seller_paymnet_invoice_line spil ON aml.id = spil.account_invoice_line
            JOIN seller_payment sp ON spil.seller_payment = sp.id
            WHERE {where_clause_admin_commission}
            AND sp.seller_id {seller_condition}
        """

        self.env.cr.execute(sale_order_query)
        sol_count = self.env.cr.fetchone()[0]

        self.env.cr.execute(total_products_query)
        total_mp_products = self.env.cr.fetchone()[0]

        self.env.cr.execute(total_sale_query)
        total_sale_query_result = self.env.cr.fetchone()[0]
        total_sale_amount = round(
            total_sale_query_result, 2) if total_sale_query_result else 0

        self.env.cr.execute(admin_earning_query)
        res_admin_pay = self.env.cr.fetchone()[0]
        admin_earning = round(res_admin_pay, 2) if res_admin_pay else 0

        return {
            "sol_count": sol_count,
            "total_sale_amount": total_sale_amount,
            "admin_earning": admin_earning,
            "total_mp_products": total_mp_products,
            "initial_date": initial_date,
            "final_date": final_date,
        }

    # === SALES CARD DATA---END ===#

    # === SALES CHART DATA---START ===#
    def get_dashboard_sales_data(self, post):
        """Get Sales Graph Data
        rtype: dict
        - days_values (dict): Sales data per day of the week
        - days_labels (list): Labels for the days of the week
        - months_labels (list): Labels for the months
        - months_values (list): Sales data per month
        - years_labels (list): Labels for the years
        - years_values (list): Sales data per year
        """

        select_filter = post.get("selectFilter")

        amount_per_day = {}
        amount_per_month = {}
        amount_per_year = {}
        months_labels = years_labels = []
        months_values = years_values = []

        partner = self.env.user.partner_id
        is_admin = self.env.user.has_group(
            "odoo_marketplace.marketplace_manager_group")
        seller_condition = f"marketplace_seller_id = {partner.id}" if not is_admin else "marketplace_seller_id IS NOT NULL"

        sales_data_weekly = self._get_sales_query_result(
            "day", "6 days", seller_condition)
        for date, amount in sales_data_weekly:
            day_of_week = date.strftime("%a")
            amount_per_day[day_of_week] = amount_per_day.get(
                day_of_week, 0) + amount

        if select_filter == "M":
            sales_data_monthly = self._get_sales_query_result(
                "month", "1 year", seller_condition)
            for month, m_amount in sales_data_monthly:
                month_of_year = month.strftime("%b")
                amount_per_month[month_of_year] = (
                    amount_per_month.get(month_of_year, 0) + m_amount
                )
            sorted_months = self._get_sorted_months()
            amount_per_month = {month: amount_per_month.get(
                month, 0) for month in sorted_months}

            sorted_sales_data = dict(
                sorted(amount_per_month.items(),
                       key=lambda item: sorted_months.index(item[0]))
            )

            months_values = list(sorted_sales_data.values())
            months_labels = list(sorted_sales_data.keys())

        if select_filter == "Y":
            sales_data_yearly = self._get_sales_query_result(
                "year", "", seller_condition)
            if sales_data_yearly:
                min_year = min(dt.year for dt, _ in sales_data_yearly)
                max_year = max(dt.year for dt, _ in sales_data_yearly)
                result = {year: 0 for year in range(min_year, max_year + 1)}
                for dt, amount in sales_data_yearly:
                    result[dt.year] += amount
                years_labels = list(result.keys())
                years_values = list(result.values())
            else:
                years_labels = []
                years_values = []

        days_labels = [(datetime.today() - timedelta(days=i)
                        ).strftime("%a") for i in range(7)][::-1]

        return {
            "days_values": amount_per_day,
            "days_labels": days_labels,
            "months_labels": months_labels,
            "months_values": months_values,
            "years_labels": years_labels,
            "years_values": years_values,
        }

    def _get_sales_query_result(self, period, interval, seller_condition):
        if period == "year":
            yearly_query = f"""
                SELECT date_trunc('year', create_date) AS year,
                SUM(price_total) AS yearly_price_total
                FROM sale_order_line
                WHERE {seller_condition}
                AND marketplace_state IN ('shipped', 'done')
                GROUP BY date_trunc('year', create_date)
                ORDER BY year;
            """
            self.env.cr.execute(yearly_query)
            return self.env.cr.fetchall()

        query = f"""
            SELECT date_trunc('{period}', create_date) AS {period},
            SUM(price_total) AS {period}_price_total
            FROM sale_order_line
            WHERE create_date >= CURRENT_DATE - INTERVAL '{interval}'
            AND {seller_condition}
            AND marketplace_state IN ('shipped', 'done')
            GROUP BY date_trunc('{period}', create_date)
            ORDER BY {period};
        """
        self.env.cr.execute(query)
        return self.env.cr.fetchall()
    # === SALES CHART DATA---END ===#

    # === TOTAL ORDERS-START ===#
    def get_dashboard_total_orders(self, post):
        """Get Total Orders Graph Data
        rtype: dict
        - days_values (dict): Total orders per day of the week
        - days_labels (list): Labels for the days of the week
        - months_labels (list): Labels for the months
        - months_values (list): Total orders per month
        - years_labels (list): Labels for the years
        - years_values (list): Total orders per year
        """

        select_filter = post.get('selectFilterValue')

        partner = self.env.user.partner_id
        is_admin = self.env.user.has_group(
            "odoo_marketplace.marketplace_manager_group")

        seller_condition = f"marketplace_seller_id = {partner.id}" if not is_admin else "marketplace_seller_id IS NOT NULL"

        weekly_query_result = self._get_orders_query_result(
            'Dy', '6 days', seller_condition)
        weekly_data = dict(weekly_query_result)
        days_labels = [(datetime.today() - timedelta(days=i)
                        ).strftime("%a") for i in range(7)][::-1]

        if select_filter == "M":
            monthly_query_result = self._get_orders_query_result(
                'Mon', '1 year', seller_condition)
            sorted_months = self._get_sorted_months()
            amount_per_month = {month: 0 for month in sorted_months}
            for month, m_amount in monthly_query_result:
                amount_per_month[month] += m_amount

            sorted_orders_data = dict(sorted(amount_per_month.items(
            ), key=lambda item: list(amount_per_month.keys()).index(item[0])))

            months_labels = list(sorted_orders_data.keys())
            months_values = list(sorted_orders_data.values())

        if select_filter == "Y":
            yearly_query_result = self._get_orders_query_result(
                'YYYY', '10 years', seller_condition)
            yearly_data = dict(yearly_query_result)
            current_year = datetime.now().year
            result = {year: 0 for year in range(
                current_year - 10, current_year + 1)}
            for dt, count in yearly_data.items():
                result[int(dt)] += count
            years_labels = list(result.keys())
            years_values = list(result.values())

        return {
            "days_values": weekly_data,
            "days_labels": days_labels,
            "months_labels": months_labels if select_filter == "M" else [],
            "months_values": months_values if select_filter == "M" else [],
            "years_labels": years_labels if select_filter == "Y" else [],
            "years_values": years_values if select_filter == "Y" else [],
        }

    def _get_orders_query_result(self, period, interval, seller_condition):
        query = f"""
        SELECT TO_CHAR(create_date, '{period}') AS {period}_abbr,
        COUNT(*) AS order_count
        FROM sale_order_line
        WHERE create_date >= CURRENT_DATE - INTERVAL '{interval}'
        AND marketplace_state IN ('shipped', 'done')
        AND {seller_condition}
        GROUP BY TO_CHAR(create_date, '{period}')
        ORDER BY MIN(create_date);
        """
        self.env.cr.execute(query)
        return self.env.cr.fetchall()
    # === TOTAL ORDERS-END ===#

    # === ACTIVE AND REGISTERED SELLERS DETAIL--START ===#
    def get_dashboard_active_registered_sellers(self, post):
        """Get Active and Registered Sellers Data
        rtype: dict
        - isAdmin (bool): Indicates if the user is an admin
        - days_values (dict): Active sellers per day
        - reg_days_values (dict): Registered sellers per day
        - days_labels (list): Labels for the days
        - active_months_labels (list): Labels for the active sellers per month
        - active_months_values (list): Values for the active sellers per month
        - registered_months_labels (list): Labels for the registered sellers per month
        - registered_months_values (list): Values for the registered sellers per month
        - active_years_labels (list): Labels for the active sellers per year
        - active_years_values (list): Values for the active sellers per year
        - registered_years_labels (list): Labels for the registered sellers per year
        - registered_years_values (list): Values for the registered sellers per year
        """

        select_filter = post.get('selectFilterValue')

        active_sellers_per_day = {}
        registered_sellers_per_day = {}
        active_months_counts = {}
        registered_months_counts = {}
        active_years_counts = {}
        registered_years_counts = {}
        active_months_labels = []
        registered_months_labels = []
        active_months_values = []
        registered_months_values = []
        active_years_labels = []
        active_years_values = []
        registered_years_labels = []
        registered_years_values = []

        is_admin = self.env.user.has_group(
            "odoo_marketplace.marketplace_manager_group")

        def process_data(data, time_format, sellers_dict):
            for date, count in data:
                key = date.strftime(time_format)
                sellers_dict[key] = sellers_dict.get(key, 0) + count

        # Fetch data for weekly active and registered sellers
        weekly_data = self._fetch_seller_data('weekly')
        for seller_type in ["active", "registered"]:
            process_data(weekly_data[seller_type], "%a",
                         active_sellers_per_day if seller_type == "active" else registered_sellers_per_day)

        if select_filter == "M":
            # Fetch data for monthly active and registered sellers
            monthly_data = self._fetch_seller_data('monthly')
            for seller_type in ["active", "registered"]:
                if seller_type == "active":
                    process_data(
                        monthly_data[seller_type], "%b", active_months_counts)
                else:
                    process_data(
                        monthly_data[seller_type], "%b", registered_months_counts)

            sorted_months = self._get_sorted_months()
            active_months_labels = registered_months_labels = sorted_months

            active_months_values = [active_months_counts.get(
                month, 0) for month in sorted_months]
            registered_months_values = [registered_months_counts.get(
                month, 0) for month in sorted_months]

            active_months_labels = sorted_months
            registered_months_labels = sorted_months

        if select_filter == "Y":
            yearly_data = self._fetch_seller_data('yearly')

            active_data = yearly_data.get('active', [])
            registered_data = yearly_data.get('registered', [])

            start_year = min(active_data[0][0].year - 10, registered_data[0][0].year -
                             10) if active_data and registered_data else datetime.today().year - 10
            end_year = max(active_data[-1][0].year if active_data else datetime.today(
            ).year, registered_data[-1][0].year if registered_data else datetime.today().year)

            for seller_type in ["active", "registered"]:
                result_counts = active_years_counts if seller_type == "active" else registered_years_counts
                data = yearly_data.get(seller_type, [])

                for year in range(start_year, end_year + 1):
                    result_counts[year] = 0

                for dt, amount in data:
                    result_counts[dt.year] += amount

            active_years_labels = list(active_years_counts.keys())
            active_years_values = list(active_years_counts.values())
            registered_years_labels = list(registered_years_counts.keys())
            registered_years_values = list(registered_years_counts.values())

        days_labels = [(datetime.today() - timedelta(days=i)
                        ).strftime("%a") for i in range(7)][::-1]

        return {
            "isAdmin": is_admin,
            "days_values": active_sellers_per_day,
            "reg_days_values": registered_sellers_per_day,
            "days_labels": days_labels,
            "active_months_labels": active_months_labels,
            "active_months_values": active_months_values,
            "registered_months_labels": registered_months_labels,
            "registered_months_values": registered_months_values,
            "active_years_labels": active_years_labels,
            "active_years_values": active_years_values,
            "registered_years_labels": registered_years_labels,
            "registered_years_values": registered_years_values,
        }

    def _fetch_seller_data(self, period):
        """Fetch seller data for the given period."""
        queries = {
            "weekly": {
                "active": """
                    SELECT date_trunc('day', write_date) AS day, COUNT(name) AS active_sellers
                    FROM res_partner
                    WHERE write_date >= CURRENT_DATE - INTERVAL '7 day' AND seller = True
                    AND state = 'approved' AND active = True AND is_published = True
                    GROUP BY date_trunc('day', write_date)
                    ORDER BY day;
                """,
                "registered": """
                    SELECT date_trunc('day', create_date) AS day, COUNT(name) AS registered_sellers
                    FROM res_partner
                    WHERE create_date >= CURRENT_DATE - INTERVAL '7 day' AND seller = True
                    GROUP BY date_trunc('day', create_date)
                    ORDER BY day;
                """,
            },
            "monthly": {
                "active": """
                    SELECT date_trunc('month', write_date) AS month, COUNT(name) AS active_sellers
                    FROM res_partner
                    WHERE write_date >= CURRENT_DATE - INTERVAL '1 year' AND seller = True
                    AND state = 'approved' AND active = True AND is_published = True
                    GROUP BY date_trunc('month', write_date)
                    ORDER BY month;
                """,
                "registered": """
                    SELECT date_trunc('month', create_date) AS month, COUNT(name) AS registered_sellers
                    FROM res_partner
                    WHERE create_date >= CURRENT_DATE - INTERVAL '1 year' AND seller = True
                    GROUP BY date_trunc('month', create_date)
                    ORDER BY month;
                """,
            },
            "yearly": {
                "active": """
                    SELECT date_trunc('year', write_date) AS year, COUNT(name) AS active_sellers
                    FROM res_partner
                    WHERE seller = True AND state = 'approved' AND active = True AND is_published = True
                    GROUP BY date_trunc('year', write_date)
                    ORDER BY year;
                """,
                "registered": """
                    SELECT date_trunc('year', create_date) AS year, COUNT(name) AS registered_sellers
                    FROM res_partner
                    WHERE seller = True
                    GROUP BY date_trunc('year', create_date)
                    ORDER BY year;
                """,
            },
        }

        result = {}
        for seller_type in ["active", "registered"]:
            query = queries[period][seller_type]
            self.env.cr.execute(query)
            result[seller_type] = self.env.cr.fetchall()

        return result

    # === ACTIVE AND REGISTERED SELLERS DETAIL---END ===#

    # === TOP PERFORMING SELLER---START ===#
    def get_dashboard_top_perform_sellers(self, post):
        """Get Top Performing Sellers
        rtype: dict
        - is_admin (bool): Indicates if the user is a admin
        - sellers (list): Sellers Name list
        - order_count (list): Sellers Order count

        """

        select_filter = post.get('selectFilterValue')
        if select_filter == "M":
            interval = '1 month'
        elif select_filter == "Y":
            interval = '1 year'
        else:
            interval = '7 day'

        is_admin = self.env.user.has_group(
            "odoo_marketplace.marketplace_manager_group")

        top_performing_seller_data = self._get_top_performing_sellers_query(
            interval)
        seller_ids, sellers, order_count = [], [], []
        for data in top_performing_seller_data:
            seller_ids.append(data[0])
            sellers.append(data[1])
            order_count.append(data[2])

        return {
            'is_admin': is_admin,
            'seller_ids': seller_ids,
            'sellers': sellers,
            'order_count': order_count,
        }

    def _get_top_performing_sellers_query(self, interval):
        query = f"""
            SELECT rp.id, rp.name AS seller_name, SUM(sol.price_subtotal) AS total_sale_amount
            FROM sale_order_line sol
            JOIN res_partner rp ON sol.marketplace_seller_id = rp.id
            WHERE sol.create_date >= CURRENT_DATE - INTERVAL '{interval}'
            AND sol.marketplace_state IN ('shipped', 'done')
            GROUP BY rp.id, rp.name
            ORDER BY total_sale_amount DESC
            LIMIT 5
        """

        self.env.cr.execute(query)
        return self.env.cr.fetchall()
    # === TOP PERFORMING SELLER---END ===#

    # === TOP PRODUCTS---START ===#
    def get_dashboard_top_products(self, post):
        """Get Top Products Data
        rtype: dict
        - top_products (list): List of top products with their details
        """

        select_filter = post.get('selectFilter')
        prodLimit = post.get('prodsCount')
        product_domain = []
        partner = self.env.user.partner_id
        is_admin = self.env.user.has_group(
            "odoo_marketplace.marketplace_manager_group")
        seller_condition = f"= {partner.id}" if not is_admin else "IS NOT NULL"
        product_limit = 5
        if prodLimit:
            product_limit = int(prodLimit)

        if select_filter == "M":
            product_domain.append(
                "sol.create_date >= CURRENT_DATE - INTERVAL '1 month'")
        elif select_filter == "Y":
            product_domain.append(
                "sol.create_date >= CURRENT_DATE - INTERVAL '1 year'")
        else:
            product_domain.append(
                "sol.create_date >= CURRENT_DATE - INTERVAL '6 days'")
            
        where_clause_product = " AND ".join(product_domain) or "TRUE"

        top_products = self._get_top_products_query(
            seller_condition, where_clause_product, product_limit)

        prod_data = [(item[0], list(item[1].values())[0], item[2],
                      item[3], item[4]) for item in top_products]

        return {
            "top_products": prod_data,
        }

    def _get_top_products_query(self, seller_condition, where_clause_product, product_limit):
        query = f"""
            SELECT p.id, pt.name, rp.name, SUM(sol.product_uom_qty) AS total_qty,
            SUM(sol.price_unit * sol.product_uom_qty) AS total_revenue
            FROM sale_order_line AS sol
            JOIN product_product AS p 
            ON sol.product_id = p.id
            JOIN product_template AS pt
            ON p.product_tmpl_id = pt.id
            JOIN res_partner AS rp
            ON sol.marketplace_seller_id = rp.id
            WHERE sol.marketplace_seller_id {seller_condition}  
            AND {where_clause_product}
            AND sol.marketplace_state IN ('shipped', 'done')
            GROUP BY p.id, pt.name, rp.name
            ORDER BY total_qty DESC
            LIMIT {product_limit}
        """

        self.env.cr.execute(query)
        return self.env.cr.fetchall()

    # === TOP PRODUCTS---END ===#

    # === SELLER RATINGS---START ===#
    def get_dashboard_seller_ratings(self, post):
        """Get Seller Ratings Data
        rtype: dict
        - total_reviews (int): Total count of reviews
        - percentage_value (float): Percentage value of average rating
        - average_rating (float): Average rating value
        - top_seller_ratings (list): List of top seller ratings
        - rating_values (list): Values for the rating percentages
        - rating_labels (list): Labels for the ratings
        """

        select_filter = post.get('selectFilter')
        max_rating = 5
        partner = self.env.user.partner_id
        is_admin = self.env.user.has_group(
            "odoo_marketplace.marketplace_manager_group")
        seller_condition = f"rev.marketplace_seller_id = {partner.id}" if not is_admin else "rev.marketplace_seller_id IS NOT NULL"

        if select_filter == "M":
            interval = '1 month'
        elif select_filter == "Y":
            interval = '1 year'
        else:
            interval = '7 day'

        total_rating_count, total_rating_value = self._get_seller_ratings(
            seller_condition, interval)

        # Calculate average rating and percentage value
        average_rating, percentage_value = self._calculate_average_rating(
            total_rating_count, total_rating_value, max_rating)

        # Horizontal bar chart
        rating_percentages, rating_values, rating_labels = self._get_rating_percentages(
            seller_condition, interval)

        # Get top seller ratings
        top_seller_ratings = self._get_top_seller_ratings(
            seller_condition, interval)

        return {
            "total_reviews": total_rating_count,
            "percentage_value": percentage_value,
            "average_rating": average_rating,
            "top_seller_ratings": top_seller_ratings,
            "rating_values": rating_values,
            "rating_labels": rating_labels,
        }

    def _get_seller_ratings(self, seller_condition, interval):
        query = f"""
            SELECT date_trunc('day', rev.write_date) AS week, COUNT(rev.id), SUM(rev.rating)
            FROM seller_review AS rev
            WHERE rev.write_date >= CURRENT_DATE - INTERVAL '{interval}'
            AND rev.state = 'pub' 
            AND {seller_condition}
            GROUP BY week, rev.marketplace_seller_id
        """
        self.env.cr.execute(query)
        rating_data = self.env.cr.fetchall()

        total_rating_count = sum(
            rating_count for _, rating_count, _ in rating_data)
        total_rating_value = sum(
            total_rating for _, _, total_rating in rating_data)

        return total_rating_count, total_rating_value

    def _calculate_average_rating(self, total_rating_count, total_rating_value, max_rating):
        if total_rating_count != 0:
            average_rating = round(
                (total_rating_value / total_rating_count), 2)
            percentage_value = round((average_rating * 100) / max_rating)
        else:
            average_rating = 0
            percentage_value = 0
        return average_rating, percentage_value

    def _get_rating_percentages(self, seller_condition, interval):
        all_ratings_query = f"""
            SELECT rev.rating, COUNT(*) as count
            FROM seller_review AS rev
            WHERE rev.write_date >= CURRENT_DATE - INTERVAL '{interval}'
            AND rev.state = 'pub'
            AND {seller_condition}
            GROUP BY rev.rating
            ORDER BY rev.rating
            LIMIT 10
        """

        self.env.cr.execute(all_ratings_query)
        all_ratings_data = self.env.cr.fetchall()

        rating_counts = defaultdict(int)
        for rating, count in all_ratings_data:
            rating_counts[rating] += count

        total_count = sum(rating_counts.values())
        rating_percentages = {}

        for rating in range(1, 6):
            count = rating_counts.get(rating, 0)
            percentage = round((count / total_count) * 100,
                               2) if total_count > 0 else 0
            rating_percentages[rating] = percentage

        rating_values = list(rating_percentages.values())
        rating_values.reverse()
        rating_labels = list(map(str, range(1, 6)))[::-1]  # Reverse labels

        return rating_percentages, rating_values, rating_labels

    def _get_top_seller_ratings(self, seller_condition, interval):
        top_seller_rating_reviews_avg = f"""
            SELECT date_trunc('day', rev.write_date) AS week, rp.id, rp.name, rev.rating
            FROM seller_review AS rev
            JOIN res_partner AS rp ON rev.marketplace_seller_id = rp.id
            WHERE rev.write_date >= CURRENT_DATE - INTERVAL '{interval}'
            AND rev.state = 'pub' 
            AND {seller_condition}
            GROUP BY week, rp.id, rp.name, rev.rating
        """

        self.env.cr.execute(top_seller_rating_reviews_avg)
        top_seller_rating_data = self.env.cr.fetchall()

        ratings = defaultdict(list)
        for _, partner_id, name, rating in top_seller_rating_data:
            ratings[(partner_id, name)].append(rating)

        sellers_avg_rating = {name: sum(
            ratings_list) / len(ratings_list) for name, ratings_list in ratings.items()}
        top_seller_ratings = [(key, round(value, 2))
                              for key, value in sellers_avg_rating.items()]
        top_seller_ratings.sort(key=lambda x: x[1], reverse=True)

        return top_seller_ratings
    # === SELLER RATINGS---END ===#

    # === SELLER BEST SELLING PRODUCT---START ===#
    def get_dashboard_seller_best_selling_product(self, post):

        select_filter = post.get('selectFilter')
        prodLimit = post.get('bestProdsCount')
        partner = self.env.user.partner_id
        is_admin = self.env.user.has_group(
            "odoo_marketplace.marketplace_manager_group")
        seller_condition = f"= {partner.id}" if not is_admin else "IS NOT NULL"
        product_limit = 5
        if prodLimit:
            product_limit = int(prodLimit)
        product_domain = []

        if select_filter == "M":
            product_domain.append(
                f"sol.create_date >= CURRENT_DATE - INTERVAL '1 month'")
        elif select_filter == "Y":
            product_domain.append(
                f"sol.create_date >= CURRENT_DATE - INTERVAL '1 year'")
        else:
            product_domain.append(
                f"sol.create_date >= CURRENT_DATE - INTERVAL '6 days'")

        where_clause_product = " AND ".join(product_domain) or "TRUE"

        best_product_data = self._get_best_selling_products(
            seller_condition, where_clause_product, product_limit)

        best_selling_label = [item[0] for item in best_product_data]
        best_selling_data = [item[3] for item in best_product_data]
        best_selling_prod_ids = [item[2] for item in best_product_data]

        return {
            "isSeller": not is_admin,
            "name": partner.name,
            "best_selling_label": best_selling_label,
            "best_selling_data": best_selling_data,
            "best_selling_prod_ids": best_selling_prod_ids
        }

    def _get_best_selling_products(self, seller_condition, where_clause_product, product_limit):
        query = f"""
            SELECT pt.name AS product_name, rp.name AS seller_name, pt.id AS product_template_id,
            SUM(sol.product_uom_qty) AS total_qty,
            SUM(sol.price_unit * sol.product_uom_qty) AS total_revenue
            FROM sale_order_line AS sol
            JOIN product_product AS p 
            ON sol.product_id = p.id
            JOIN product_template AS pt
            ON p.product_tmpl_id = pt.id
            JOIN res_partner AS rp
            ON sol.marketplace_seller_id = rp.id
            WHERE sol.marketplace_seller_id {seller_condition}
            AND {where_clause_product}
            AND sol.marketplace_state IN ('shipped', 'done')
            GROUP BY pt.id, pt.name, rp.name
            ORDER BY total_qty DESC
            LIMIT {product_limit}
        """

        self.env.cr.execute(query)
        best_product_data = self.env.cr.fetchall()

        prod_data = [(list(item[0].values())[0] if isinstance(item[0], dict) else item[0],
                      item[1], item[2], item[3], item[4]) for item in best_product_data]

        return prod_data
    # === SELLER BEST SELLING PRODUCT---END ===#

    def _get_sorted_months(self):
        """Returns a List of abbreviated custom sorted months label."""
        all_months = [calendar.month_abbr[i] for i in range(1, 13)]
        current_month = datetime.today().strftime('%b')
        current_month_index = all_months.index(current_month)
        months_before_current = all_months[:current_month_index]
        months_after_current = all_months[current_month_index + 1:]
        sorted_months = months_after_current + \
            months_before_current + [current_month]

        return sorted_months

    def prepare_filter_context(self, data):
        """Returns a dict context for the charts filteration."""
        chartName = data.get('chartName')
        chartFilter = {
            'sellersChart': data.get('sellersChartFilter'),
            'ratingsChart': data.get('ratingsChartFilter'),
            'salesChart': data.get('salesChartFilter'),
            'ordersChart': data.get('ordersChartFilter'),
            'bestProdsChart': data.get('bestProdsChartFilter')
        }.get(chartName, '')

        context = {}
        if chartFilter == 'M':
            context['group_by'] = 'create_date:month'
        elif chartFilter == 'Y':
            context['group_by'] = 'create_date:year'

        return context

    def get_filtered_domain(self, post):
        """Returns a domain filter based on the provided duration."""
        duration = post.get("duration")
        initialDate = post.get("initialDate")
        finalDate = post.get("finalDate")
        chartName = post.get('chartName')
        filter_days = {'W': 7}

        chartFilter = {
            'sellersChart': post.get('sellersChartFilter'),
            'ratingsChart': post.get('ratingsChartFilter'),
            'salesChart': post.get('salesChartFilter'),
            'ordersChart': post.get('ordersChartFilter'),
            'bestProdsChart': post.get('bestProdsChartFilter')
        }.get(chartName, '')

        if duration == "custom" and initialDate and finalDate:
            domain = [('create_date', '>=', initialDate),
                      ('create_date', '<=', finalDate)]
        elif chartFilter in filter_days:
            domain = [('create_date', '>=', self._get_start_time_of_the_day(
                filter_days[chartFilter]))]
        elif chartName in ['ratingsChart', 'bestProdsChart']:
            ratings_filter_days = {'W': 7, 'M': 30, 'Y': 365}
            domain = [('create_date', '>=', self._get_start_time_of_the_day(
                ratings_filter_days.get(chartFilter, 0)))]
        elif duration:
            domain = [
                ('create_date', '>=', self._get_start_time_of_the_day(int(duration)))]
        else:
            domain = []

        return domain

    def _get_start_time_of_the_day(self, duration):
        """Returns the start time of the day for the specified duration."""
        dt = datetime.now() - timedelta(days=duration-1)
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
