/** @odoo-module **/
import { registry } from "@web/core/registry";
import { ChartRenderer } from "./chart_renderer/chart_renderer";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from '@web/core/l10n/translation';
import { session } from "@web/session";
import { browser } from "@web/core/browser/browser";

export class MpSalesDashboard extends Component {
    setup() {
        this.rpc = useService('rpc');
        this.orm = useService('orm');
        this.actionService = useService("action");
        this.router = useService("router");

        const today = new Date();
        const sevenDaysAgo = new Date(today.getTime() - 6 * 24 * 60 * 60 * 1000);
        const lastInterval = this.getLastItemFromStorage('period')

        this.state = useState({
            ratingPercentageValue: '',
            isAdmin: false,
            isSeller: false,
            solCount: null,
            totalSaleAmount: null,
            currency: null,
            adminCommission: null,
            selectValue: '7',
            topProducts: null,
            totalProducts: null,
            initialDate: this.formatDateTime(sevenDaysAgo),
            finalDate: this.formatDateTime(today),
        });
        this.setItemInStorage('key', 'value')
        this.getLastItemFromStorage('key')

        onMounted(() => {
            this.setDropdownValue('period')
            this.setDropdownValue('sales-filter');
            this.setDropdownValue('total-orders');
            this.setDropdownValue('performing-sellers');
            this.setDropdownValue('top-products');
            this.setDropdownValue('products-count');
            this.setDropdownValue('seller-ratings');
            this.setDropdownValue('best-selling');
            this.setupCardHandlers()
            if (this.state.isAdmin) {
                this.setDropdownValue('active-seller-filter');
            }
            if (lastInterval) {
                this.state.selectValue = lastInterval
            }
            this.setStartEndDate();
            this.setSalesGraphType();
            this.setSellersGraphType();

            document.getElementById('applyFilter').addEventListener('click', this._handleApplyFilter.bind(this));
        });

        onWillStart(this.initialize.bind(this));
    }

    formatDateTime(date) { return date.toISOString().replace('T', ' ').slice(0, 19) }

    async initialize() {
        
        const promises = [
            this.loadDashboardData(),
            this.getSellerRatings(),
            this.getSalesData(),
            this.getSellers(),
            this.getTopPerformingSellers(),
            this.getTotalOrders(),
            this.getTopProducts(),
            this.getBestSelling()
        ];

        await Promise.all(promises);
    }


    async setStartEndDate() {
        const lastSelected = this.getLastItemFromStorage('period')

        if (lastSelected == 'custom') {
            document.getElementById('custom_dates').style.display = 'flex'
            const lastStart = this.getLastItemFromStorage('start-date')
            const lastEnd = this.getLastItemFromStorage('end-date')

            if (document.getElementById('custom_dates') && lastStart && lastEnd) {
                const startDateObj = new Date(Date.parse(lastStart.replace(" ", "T") + "Z"));
                const endDateObj = new Date(Date.parse(lastEnd.replace(" ", "T") + "Z"));

                const formattedStartDate = startDateObj.toISOString().split('T')[0];
                const formattedEndDate = endDateObj.toISOString().split('T')[0];

                document.getElementById('start_date').value = formattedStartDate;
                document.getElementById('end_date').value = formattedEndDate;
            }
            await this.loadDashboardData()
        }
    }

    setItemInStorage(key, value) { browser.localStorage.setItem(key, value) }

    getLastItemFromStorage(key) {

        const items = browser.localStorage
        if (items.getItem(key)) {
            const result = items.getItem(key);
            return result
        }

    }
    setDropdownValue(selectId) {
        const select_filter = document.getElementById(selectId);
        const lastSelected = this.getLastItemFromStorage(selectId);
        if (lastSelected && select_filter) {
            select_filter.value = lastSelected;
        }
    }

    setSalesGraphType() {
        const lastSalesGraphType = this.getLastItemFromStorage('sales-graph-type');
        if (lastSalesGraphType) {
            const graph = document.querySelector(`input[type="radio"][value="${lastSalesGraphType}"]`);
            if (graph) {
                graph.checked = true;
                this.state.graphType = lastSalesGraphType
                this.salesGraphSelect({ target: graph })
            }
        }
    }

    setSellersGraphType() {
        const lastSellersGraphType = this.getLastItemFromStorage('sellers-graph-type');

        if (lastSellersGraphType) {
            const graph = document.querySelector(`input[type="radio"][value="${lastSellersGraphType}"]`);
            if (graph) {
                graph.checked = true;
                this.state.sellersGraphType = lastSellersGraphType
                this.sellersGraphSelect({ target: graph })
            }
        }
    }

    async _handleApplyFilter() {
        await this.setCustomDates();
        await this.loadDashboardData();
    }

    async handleSelectChange() {
        const select = document.getElementById('period');
        this.setItemInStorage('period', select.value)
        this.state.selectValue = this.getLastItemFromStorage('period')

        const customDateRangeView = document.getElementById('custom_dates');
        const startDate = document.getElementById('start_date');
        const endDate = document.getElementById('end_date');

        if (select.value === 'custom') {
            customDateRangeView.style.display = 'flex';
            startDate.value = this.state.initialDate.slice(0, 10);
            endDate.value = this.state.finalDate.slice(0, 10);
        } else {
            startDate.value = '';
            endDate.value = '';
            customDateRangeView.style.display = 'none';
        }
        await this.loadDashboardData();
    }

    async setCustomDates() {
        const startDate = document.getElementById('start_date').value
        const endDate = document.getElementById('end_date').value
        document.getElementById('start_date').value = startDate
        document.getElementById('end_date').value = endDate

        const s_time = '00:00:00';
        const e_time = '23:59:59';
        const startDateTime = `${startDate} ${s_time}`;
        const endDateTime = `${endDate} ${e_time}`;

        this.setItemInStorage('start-date', startDateTime)
        this.setItemInStorage('end-date', endDateTime)

        if (endDateTime < startDateTime) {
            alert('Please select a valid date interval...')
        }
        else {
            this.state.initialDate = startDateTime;
            this.state.finalDate = endDateTime;
            var today = new Date().toISOString().split('T')[0]
            $('.check_date').attr('max', today)
        }
    }

    async loadDashboardData() {
        const lastSelected = this.getLastItemFromStorage('period')
        const lastStartDate = this.getLastItemFromStorage('start-date')
        const lastEndDate = this.getLastItemFromStorage('end-date')
        const selectValue = lastSelected || this.state.selectValue
        const startDate = lastStartDate || this.state.initialDate
        const endDate = lastEndDate || this.state.finalDate

        try {

            const response = await this.rpc('/get/dashboard/card/details', {
                selectValue: selectValue,
                initialDate: startDate,
                finalDate: endDate,
            });

            if (response) {
                Object.assign(this.state, {
                    solCount: response.sol_count,
                    totalSaleAmount: response.total_sale_amount,
                    currency: response.currency,
                    adminCommission: response.admin_commission,
                    totalProducts: response.total_mp_products,
                    initialDate: response.initialDate,
                    finalDate: response.finalDate,
                });
            }

            this.setupCardHandlers();
        } catch (error) {
            console.error("Error fetching sales dashboard details:", error);
        }
    }

    setupCardHandlers() {
        const cardElements = {
            cardOrders: { id: 'card_total_orders', handler: this.openOrders.bind(this) },
            cardProducts: { id: 'card_total_products', handler: this.openProducts.bind(this) },
            cardSales: { id: 'card_total_sales', handler: this.openSales.bind(this) },
            cardAdminCommission: { id: 'card_total_comm', handler: this.openAdminCommission.bind(this) },
        };

        for (const key in cardElements) {
            const { id, handler } = cardElements[key];
            const element = document.getElementById(id);
            if (element) element.addEventListener('click', handler);
        }
    }

    async getFilterParams() {
        const lastSelected = this.getLastItemFromStorage('period')
        const lastStartDate = this.getLastItemFromStorage('start-date')
        const lastEndDate = this.getLastItemFromStorage('end-date')
        const duration = lastSelected || this.state.selectValue
        const params = { duration: duration };

        if (this.state.selectValue === 'custom') {
            params.initialDate = lastStartDate || this.state.initialDate;
            params.finalDate = lastEndDate || this.state.finalDate;
        }
        return params;
    }

    async openAction(model, method, params = {}) {
        const action = await this.orm.call(model, method, [session.user_id], { params });
        this.actionService.doAction(action);
    }

    async openOrders() {
        await this.openAction('sale.order.line', 'action_open_sale_orders', await this.getFilterParams());
    }
    async openProducts() {
        await this.openAction('product.template', 'action_open_product_template', await this.getFilterParams());
    }
    async openSales() {
        await this.openAction('sale.order.line', 'action_open_sale_orders', await this.getFilterParams());
    }
    async openAdminCommission() {
        await this.openAction('seller.payment', 'action_open_seller_payment', await this.getFilterParams());
    }

    // OPEN CHARTS ACTION

    async openCharts(ev, filterId, chartName, model, actionMethod, seller_ids = null, best_selling_prod_ids = null) {
        const params = {}
        const filterElem = document.getElementById(filterId)
        if (filterElem) {
            params[`${chartName}Filter`] = filterElem.value
        }
        params['chartName'] = chartName
        if (seller_ids !== null) {
            params['seller_ids'] = seller_ids
        }
        if (best_selling_prod_ids !== null) {
            params['best_selling_prod_ids'] = best_selling_prod_ids
        }
        const action = await this.orm.call(model, actionMethod, [session.user_id], { params });
        this.actionService.doAction(action);
    }

    async openSalesChart(ev) {
        await this.openCharts(ev, 'sales-filter', 'salesChart', 'sale.order.line', 'action_open_sale_orders')
    };

    async openSellersChart(ev) {
        await this.openCharts(ev, 'active-seller-filter', 'sellersChart', 'res.partner', 'action_open_sellers')
    }

    async openOrdersChart(ev) {
        await this.openCharts(ev, 'total-orders', 'ordersChart', 'sale.order.line', 'action_open_sale_orders')
    }

    async openRatingsChart(ev) {
        await this.openCharts(ev, 'seller-ratings', 'ratingsChart', 'seller.review', 'action_open_seller_rating')
    }

    async openBestProductsChart(ev) {
        const best_selling_prod_ids = document.querySelector('input[name="best_selling_prod_ids"]').value
        await this.openCharts(ev, 'best-selling', 'bestProdsChart', 'product.template', 'action_open_product_template', null, best_selling_prod_ids)
    }

    async openchartTopSellers(ev) {
        const seller_ids = document.querySelector('input[name="seller_ids"]').value
        await this.openCharts(ev, 'top-sellers', 'topSellersChart', 'res.partner', 'action_open_sellers', seller_ids)
    }

    async openProductViewForm(productId) {
        const action = await this.orm.call('product.product', 'action_open_product', [session.user_id], { productId });
        this.actionService.doAction(action);
    }

    async openPartnerViewForm(partnerId) {
        const action = await this.orm.call('seller.review', 'action_open_seller_rating', [session.user_id], { partnerId: partnerId });
        this.actionService.doAction(action);
    }

    // --------------------SALES GRAPH--------------------

    async handleSalesSelectChange() {
        const select_filter = document.getElementById('sales-filter');
        this.setItemInStorage('sales-filter', select_filter.value)
        await this.getSalesData();
    }

    salesGraphSelect(ev) {
        const graphType = ev.target.value;
        this.setItemInStorage('sales-graph-type', graphType);
        this.state.graph_type = graphType;
    }

    async getSalesData() {
        const selectFilter = this.getLastItemFromStorage('sales-filter');
        try {

            const response = await this.rpc('/get/sales/data', { selectFilter });
            if (response) {
                const {
                    days_values,
                    days_labels,
                    months_labels,
                    months_values,
                    years_labels,
                    years_values,
                    currency,
                } = response;

                let labels, data;

                switch (selectFilter) {
                    case "M":
                        labels = months_labels;
                        data = months_values;
                        break;
                    case "Y":
                        labels = years_labels;
                        data = years_values;
                        break;
                    default:
                        labels = days_labels;
                        data = days_values;
                        break;
                }

                let record = data;
                record = Array.isArray(record) ? record : Object.values(record);
                const filteredData = record.filter(val => val !== "" && val !== null && val !== 0);

                if (filteredData.length === 0) {
                    this.state.sales = null;
                    this.state.noMpSalesData = true;
                } else {
                    this.state.sales = {
                        data: {
                            labels: labels,
                            datasets: [{
                                maxBarThickness: 14,
                                barPercentage: 0.5,
                                label: _t('Sales'),
                                data: data,
                                hoverOffset: 4,
                                borderColor: 'rgb(35, 116, 143)',
                                backgroundColor: 'rgb(35, 116, 143)',
                                borderRadius: 50
                            }]
                        },
                        options: {
                            responsive: true,
                            plugins: {
                                legend: {
                                    display: false
                                }
                            },
                            tension: 0.4,
                            scales: {
                                x: {
                                    grid: {
                                        display: false
                                    }
                                },
                                y: {
                                    ticks: {
                                        stepsize: 1,
                                        callback: function (value) {
                                            return currency + Math.floor(value);
                                        }
                                    }
                                }
                            }
                        },
                    }
                    this.state.noMpSalesData = false;
                }
            }

        } catch (error) {
            console.error("Error while fetching sales data:", error)
        }
    }

    // --------------------TOTAL ORDERS--------------------


    async handleTotalOrdersSelectChange() {
        const select_filter = document.getElementById('total-orders');
        this.setItemInStorage('total-orders', select_filter.value)

        await this.getTotalOrders()
    }

    async getTotalOrders() {
        const lastSelected = this.getLastItemFromStorage('total-orders')
        const selectFilterValue = lastSelected
        try {

            const response = await this.rpc('/get/total/orders', { selectFilterValue });
            if (response) {
                const {
                    days_values,
                    days_labels,
                    months_labels,
                    months_values,
                    years_labels,
                    years_values
                } = response;

                let labels, data;

                switch (selectFilterValue) {
                    case "M":
                        labels = months_labels;
                        data = months_values;
                        break;
                    case "Y":
                        labels = years_labels;
                        data = years_values;
                        break;
                    default:
                        labels = days_labels;
                        data = days_values;
                        break;
                }

                let record = data;
                record = Array.isArray(record) ? record : Object.values(record);
                const filteredData = record.filter(val => val !== "" && val !== null && val !== 0);

                if (filteredData.length === 0) {
                    this.state.orders = null;
                    this.state.noMpOrdersData = true;
                } else {

                    this.state.orders = {
                        data: {
                            labels: labels,
                            datasets: [{
                                maxBarThickness: 14,
                                barPercentage: 0.5,
                                label: _t('Total'),
                                data: data,
                                hoverOffset: 4,
                                borderColor: 'rgb(35, 116, 143)',
                                backgroundColor: 'rgb(35, 116, 143)',
                                borderRadius: 50
                            }]
                        },
                        options: {
                            responsive: true,
                            width: 10,
                            fill: true,
                            tension: 0.4,
                            plugins: {
                                legend: {
                                    display: false,
                                },
                                title: {
                                    display: true,
                                    position: 'bottom',
                                    text: _t(`Sale order line v/s time period`),
                                },
                                roundedBars: {
                                    cornerRadius: 4,
                                    allCorners: true,
                                },
                            },
                            scales: {
                                x: {
                                    grid: {
                                        display: false
                                    }
                                },
                                y: {
                                    ticks: {
                                        stepSize: 1,
                                        callback: function (value) {
                                            return Math.floor(value)
                                        }
                                    }
                                }
                            }
                        }
                    };
                    this.state.noMpOrdersData = false;
                }
            }

        } catch (error) {
            console.error("Error while fetching total sale order lines:", error);
        }
    }

    // --------------------ACTIVE & NEW REGISTERED SELLERS--------------------

    async handleActiveSellersSelectChange() {
        const select_filter = document.getElementById('active-seller-filter');
        this.setItemInStorage('active-seller-filter', select_filter.value)

        await this.getSellers()
    }

    sellersGraphSelect(ev) {
        const sellersgraphType = ev.target.value;
        this.setItemInStorage('sellers-graph-type', sellersgraphType)
        this.state.sellersGraphType = sellersgraphType;
    }
    async getSellers() {
        const lastSelected = this.getLastItemFromStorage('active-seller-filter')
        const selectFilterValue = lastSelected
        try {
            
            const response = await this.rpc('/get/active/sellers', { selectFilterValue });
            if (response && response.isAdmin) {
                this.state.isAdmin = true;
                const {
                    days_values,
                    reg_days_values,
                    days_labels,
                    active_months_labels,
                    active_months_values,
                    registered_months_values,
                    active_years_labels,
                    active_years_values,
                    registered_years_values,
                } = response;

                let labels, active_data, register_data

                switch (selectFilterValue) {
                    case "M":
                        labels = active_months_labels;
                        active_data = active_months_values;
                        register_data = registered_months_values;
                        break;
                    case "Y":
                        labels = active_years_labels;
                        active_data = active_years_values;
                        register_data = registered_years_values;
                        break;
                    default:
                        labels = days_labels;
                        active_data = days_values;
                        register_data = reg_days_values;
                        break;
                }

                let active_record = active_data;
                let register_record = register_data;

                active_record = Array.isArray(active_record) ? active_record : Object.values(active_record);
                register_record = Array.isArray(register_record) ? register_record : Object.values(register_record);
                const filteredActiveData = active_record.filter(val => val !== "" && val !== null && val !== 0);
                const filteredRegisterData = register_record.filter(val => val !== "" && val !== null && val !== 0);

                if (filteredActiveData.length === 0 && filteredRegisterData.length === 0) {
                    this.state.sellers = null;
                    this.state.noMpSellersData = true;
                } else {
                    this.state.sellers = {
                        data: {
                            labels,
                            datasets: [
                                {
                                    label: _t('Active Sellers'),
                                    data: active_data,
                                    hoverOffset: 4,
                                    borderColor: 'rgb(249, 190, 37)',
                                    maxBarThickness: 14,
                                    barPercentage: 0.5,
                                    backgroundColor: 'rgb(249, 190, 37)',
                                    borderRadius: 50,
                                },
                                {
                                    label: _t('New Registered Sellers'),
                                    data: register_data,
                                    hoverOffset: 4,
                                    borderColor: 'rgb(35, 116, 143)',
                                    maxBarThickness: 14,
                                    barPercentage: 0.5,
                                    backgroundColor: 'rgb(35, 116, 143)',
                                    borderRadius: 50,
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            plugins: {
                                title: {
                                    display: false,
                                    position: 'bottom',
                                    text: 'Active & Registered Seller over the Period'
                                },
                                legend: {
                                    align: 'start',
                                    labels: {
                                        boxWidth: 12,
                                        textAlign: 'center'
                                    }
                                }
                            },
                            scales: {
                                x: {
                                    grid: {
                                        display: false
                                    }
                                },
                                y: {
                                    ticks: {
                                        callback: function (value) {
                                            return Math.floor(value);
                                        }
                                    }
                                }
                            }
                        },
                    }
                    this.state.noMpSellersData = false;
                }
            }
            else {
                this.state.isAdmin = false;
            }

        } catch (error) {
            console.error("Error while fetching sellers:", error);
        }
    }

    // --------------------TOP PERFORMING SELLERS--------------------

    async handlePerformingSelectChange() {
        const select_filter = document.getElementById('performing-sellers');
        this.setItemInStorage('performing-sellers', select_filter.value)
        await this.getTopPerformingSellers()
    }

    async getTopPerformingSellers() {
        const lastSelected = this.getLastItemFromStorage('performing-sellers')
        const selectFilterValue = lastSelected

        const title_text = {
            W: _t("Top Performing Seller in Last 7 Days (WEEK)"),
            M: _t("Top Performing Seller in Last 30 Days (MONTH)"),
            Y: _t("Top Performing Seller in Last 365 Days (YEAR)")
        }[selectFilterValue] || _t("Top Performing Seller in Last 7 Days (WEEK)");

        try {

            const response = await this.rpc('/get/top/performing/sellers', { selectFilterValue });
            if (response && response.isAdmin) {
                const {
                    sellers,
                    order_count,
                    currency
                } = response
                this.state.sellerIds = response.seller_ids

                const top_seller = sellers[0]

                if (sellers.length === 0) {
                    this.state.topPerformingSeller = null;
                    this.state.noMpTopSellersData = true;
                } else {
                    this.state.topPerformingSeller = {
                        data: {
                            labels: sellers,
                            datasets: [
                                {
                                    label: _t("Top Seller"),
                                    data: order_count,
                                    hoverOffset: 4,
                                    maxBarThickness: 14,
                                    barPercentage: 0.5,
                                    borderColor: 'rgb(35, 116, 143)',
                                    backgroundColor: 'rgb(35, 116, 143)',
                                    borderRadius: 50
                                },
                            ]
                        },
                        options: {
                            responsive: true,
                            plugins: {
                                legend: {
                                    display: false,
                                },
                                title: {
                                    display: true,
                                    position: 'bottom',
                                    text: top_seller ? title_text + ": " + top_seller : ''
                                }
                            },
                            scales: {
                                x: {
                                    grid: {
                                        display: false
                                    }
                                },
                                y: {
                                    ticks: {
                                        callback: function (value) {
                                            return currency + Math.floor(value);
                                        }
                                    },
                                }
                            }
                        },
                    };
                    this.state.noMpTopSellersData = false;
                }
            }
            else {
                this.state.isAdmin = false
            }

        } catch (error) {
            console.error("Error while fetching top performing sellers:", error);
        }

    }

    // --------------------TOP SELLING PRODUCTS--------------------

    async handleTopProductSelectChange() {
        const select_filter = document.getElementById('top-products');
        this.setItemInStorage('top-products', select_filter.value)
        const select_filter_prod = document.getElementById('products-count');
        this.state.prodsCount = 5;
        await this.getTopProducts();
    }

    async handleProductsCountSelectChange() {
        const select_filter_prod = document.getElementById('products-count');
        this.setItemInStorage('products-count', select_filter_prod.value)
        await this.getTopProducts()
    }

    async getTopProducts() {
        const lastSelected = this.getLastItemFromStorage('top-products')
        const selectFilter = lastSelected ? lastSelected : this.state.filterTopProducts;
        const lastSelectedCount = this.getLastItemFromStorage('products-count')
        const prodsCount = lastSelectedCount ? lastSelectedCount : this.state.prodsCount;
        try {

            const response = await this.rpc('/get/top/products', { selectFilter, prodsCount });
            if (response) {
                if (response.top_products.length === 0) {
                    this.state.noMpTopProductsData = true;
                } else {
                    Object.assign(this.state, {
                        topProducts: response.top_products,
                        totalProductsCount: response.total_products_count
                    })
                    this.state.noMpTopProductsData = false;
                }
            }
        } catch (error) {
            console.error("Error while fetching Top products:", error);
        }
    }

    // --------------------OVERALL SELLERS RATING--------------------

    async handleRatingsSelectChange() {
        const select_filter = document.getElementById('seller-ratings');
        this.setItemInStorage('seller-ratings', select_filter.value)
        // this.state.filterSellerRatings = select_filter.value
        await this.getSellerRatings()
    }

    async getSellerRatings() {
        const lastSelected = this.getLastItemFromStorage('seller-ratings')
        const selectFilter = lastSelected

        try {

            const response = await this.rpc('/get/seller/rating', { selectFilter })
            if (response) {
                this.state.ratingPercentageValue = response['percentage_value']
                this.state.averageRating = response['average_rating']
                this.state.totalReviews = response['total_reviews']
                this.state.topSellerRatings = response['top_seller_ratings']
                this.state.ratingList = response['rating_list']
                this.state.ratingValues = response['rating_values']

                var labels = response['rating_labels']
                var data = response['rating_values']

                if (response['total_reviews'] === 0) {
                    this.state.ratings = null;
                    this.state.noMpRatingsData = true;
                } else {
                    this.state.ratings = {
                        data: {
                            labels: labels,
                            datasets: [{
                                label: _t('Seller Ratings'),
                                maxBarThickness: 12,
                                barPercentage: 0.5,
                                data: data,
                                hoverOffset: 4,
                                borderColor: 'rgb(35, 116, 143)',
                                backgroundColor: [
                                    'rgb(37, 147, 135)',
                                    'rgb(40, 196, 94)',
                                    'rgb(249, 190, 37)',
                                    'rgb(201, 137, 5)',
                                    'rgba(247, 113, 113)'
                                ],
                                borderRadius: 50
                            }]
                        },
                        options: {
                            indexAxis: 'y',
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'end'
                                }
                            },
                            scales: {
                                x: {
                                    grid: {
                                        display: false
                                    },
                                    ticks: {
                                        display: false
                                    }
                                },
                                y: {
                                    grid: {
                                        display: false
                                    }
                                }
                            },
                        },
                    }
                    this.state.noMpRatingsData = false;
                }
            }

        } catch (error) {
            console.error("Error while fetching Seller ratings:", error);
        }

    }

    // --------------------BEST SELLING PRODUCTS FOR SELLER--------------------

    async handleBestSellingSelectChange() {
        const select_filter = document.getElementById('best-selling');
        this.setItemInStorage('best-selling', select_filter.value)
        const select_filter_prod = document.getElementById('best-selling-products-count');
        await this.getBestSelling()
    }

    async handleBestSellingProductsCountSelectChange() {
        const select_filter_prod = document.getElementById('best-selling-products-count');
        this.setItemInStorage('best-selling-products-count', select_filter_prod.value)
        await this.getBestSelling()
    }

    async getBestSelling() {

        const lastSelected = this.getLastItemFromStorage('best-selling')
        const selectFilter = lastSelected
        const lastSelectedCount = this.getLastItemFromStorage('best-selling-products-count')
        const bestProdsCount = lastSelectedCount
        try {

            const response = await this.rpc('/seller/best/selling/product', { selectFilter, bestProdsCount });
            if (response && response.isSeller) {
                this.state.best_selling_prod_ids = response['best_selling_prod_ids']

                var labels = response['best_selling_label']
                var data = response['best_selling_data']
                const seller = response['seller_name']
                const screenWidth = window.innerWidth;
                const doughnutRadius = screenWidth <= 576 ? 70 : (screenWidth <= 1024 ? 130 : 150);
                const showLegend = screenWidth > 576

                if (response['best_selling_prod_ids'].length === 0) {
                    this.state.best_selling = null;
                    this.state.noMpBestProdSellersData = true;
                } else {
                    this.state.best_selling = {
                        data: {
                            labels: labels,
                            datasets: [{
                                label: _t('Best Products'),
                                data: data,
                                hoverOffset: 4,
                                borderColor: 'rgb(35, 116, 143)',
                                backgroundColor: [
                                    'rgb(37, 147, 135)',
                                    'rgb(40, 196, 94)',
                                    'rgb(249, 190, 37)',
                                    'rgb(201, 137, 5)',
                                    'rgb(247, 113, 113)'
                                ],
                            }]
                        },
                        options: {
                            responsive: true,
                            plugins: {
                                title: {
                                    display: true,
                                    position: 'bottom',
                                    text: _t("Best Selling over the duration: ") + seller
                                },
                                legend: {
                                    display: showLegend
                                }
                            },
                            maintainAspectRatio: true,
                            radius: doughnutRadius,
                        }
                    }
                    this.state.noMpBestProdSellersData = false;
                }
            }
            else {
                this.state.isSeller = false
            }

        } catch (error) {
            console.error("Error while fetching Best sold products for seller: ", error);
        }
    }
}

MpSalesDashboard.template = 'odoo_marketplace.mp_sales_dashboard';
MpSalesDashboard.components = { ChartRenderer }
registry.category("actions").add("mp_analytics_dashboard_tag", MpSalesDashboard);
