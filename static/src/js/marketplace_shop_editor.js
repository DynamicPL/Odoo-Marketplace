/** @odoo-module **/
/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : https://store.webkul.com/license.html/ */

import { jsonrpc } from "@web/core/network/rpc_service";
import options from "@web_editor/js/editor/snippets.options";
import { _t } from "@web/core/l10n/translation";

    options.registry.website_sale = options.registry.website_sale.extend({
        start: function () {
            var self = this;
            this.td_seller_shop_id = parseInt(this.$target.find('[data-oe-model="seller.shop"]').data('oe-id'));
            this.td_seller_id = parseInt(this.$target.find('[data-oe-model="res.partner"]').data('oe-id'));

            if (this.td_seller_shop_id)
            {
                new Model('seller.shop.style')
                    .call('search_read', [[]])
                        .then(function (data) {
                            var $ul = self.$el.find('ul[name="style"]');
                            for (var k in data) {
                                $ul.append(
                                    $('<li data-style="'+data[k]['id']+'" data-toggle_class="'+data[k]['html_class']+'"/>')
                                        .append( $('<a/>').text(data[k]['name']) ));
                            }
                            self.set_active();
                        });
            }

            if (this.td_seller_id)
            {
                new Model('seller.shop.style')
                    .call('search_read', [[]])
                        .then(function (data) {
                            var $ul = self.$el.find('ul[name="style"]');
                            for (var k in data) {
                                $ul.append(
                                    $('<li data-style="'+data[k]['id']+'" data-toggle_class="'+data[k]['html_class']+'"/>')
                                        .append( $('<a/>').text(data[k]['name']) ));
                            }
                            self.set_active();
                        });
            }

            if (! this.td_seller_shop_id && ! this.td_seller_id)
                this._super();
            this.bind_resize();
        },
        reload: function () {
            if (location.href.match(/\?enable_editor/)) {
                location.reload();
            } else {
                location.href = location.href.replace(/\?(enable_editor=1&)?|#.*|$/, '?enable_editor=1&');
            }
        },
        bind_resize: function () {
            var self = this;
            this.$el.on('mouseenter', 'ul[name="size"] table', function (event) {
                $(event.currentTarget).addClass("oe_hover");
            });
            this.$el.on('mouseleave', 'ul[name="size"] table', function (event) {
                $(event.currentTarget).removeClass("oe_hover");
            });
            this.$el.on('mouseover', 'ul[name="size"] td', function (event) {
                var $td = $(event.currentTarget);
                var $table = $td.closest("table");
                var x = $td.index()+1;
                var y = $td.parent().index()+1;

                var tr = [];
                for (var yi=0; yi<y; yi++) tr.push("tr:eq("+yi+")");
                var $select_tr = $table.find(tr.join(","));
                var td = [];
                for (var xi=0; xi<x; xi++) td.push("td:eq("+xi+")");
                var $select_td = $select_tr.find(td.join(","));

                $table.find("td").removeClass("select");
                $select_td.addClass("select");
            });
            this.$el.on('click', 'ul[name="size"] td', function (event) {
                var $td = $(event.currentTarget);
                var x = $td.index()+1;
                var y = $td.parent().index()+1;
                if (self.product_tmpl_id)
                jsonrpc('/shop/change_size',  {'id': self.product_tmpl_id, 'x': x, 'y': y}).then(self.reload);
                if (self.td_seller_shop_id)
                jsonrpc('/seller/shop/change_size', {'id': self.td_seller_shop_id, 'x': x, 'y': y}).then(self.reload);
                if (self.td_seller_id)
                jsonrpc('/seller/change_size', {'id': self.td_seller_id, 'x': x, 'y': y}).then(self.reload);
            });
        },
        style: function (type, value, $li) {
            if(type !== "click") return;
            if (this.product_tmpl_id)
            jsonrpc('/shop/change_styles', {'id': this.product_tmpl_id, 'style_id': value});
            if (this.td_seller_shop_id)
            jsonrpc('/seller/shop/change_styles',  {'id': this.td_seller_shop_id, 'style_id': value});
            if (this.td_seller_id)
            jsonrpc('/seller/change_styles', {'id': this.td_seller_id, 'style_id': value});
        },
        go_to: function (type, value) {
            if(type !== "click") return;
            if (this.product_tmpl_id)
            jsonrpc('/shop/change_sequence', {'id': this.product_tmpl_id, 'sequence': value}).then(this.reload);
            if (this.td_seller_shop_id)
            jsonrpc('/seller/shop/change_sequence', {'id': this.td_seller_shop_id, 'sequence': value}).then(this.reload);
            if (this.td_seller_id)
            jsonrpc('/seller/change_sequence', {'id': this.td_seller_id, 'sequence': value}).then(this.reload);
        }
    });

