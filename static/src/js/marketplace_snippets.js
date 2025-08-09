/** @odoo-module **/

/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : https://store.webkul.com/license.html/ */

import { jsonrpc } from "@web/core/network/rpc_service";
import publicWidget from "@web/legacy/js/public/public_widget";
publicWidget.registry.wkMarketplaceSnippets = publicWidget.Widget.extend({
    selector: '#open_store_button',

        start: function () {
            var $this = this
            $this._fetch().then(function(result){$this.$el.html(result)});
            return this._super.apply(this, arguments);
        },
        _fetch: function () {
            return jsonrpc(
                '/add/header/button'
            ).then(res => {
                if (res.route === false){
                    return ''
                }
                var store_btn_el = `<a href="${res.route}" class="btn" style="font-weight:600;background:#3BD3F4;border-radius: 2px;color:#fff;text-transform: uppercase;">${res.btn_content}</a>`;
                return store_btn_el;
            });
        },
    });

