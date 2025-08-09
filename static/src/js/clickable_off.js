/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { Message } from '@mail/core/common/message';
import { MessagingMenu } from '@mail/core/web/messaging_menu';
import { useService } from "@web/core/utils/hooks";
import { useState, onWillStart } from "@odoo/owl";
import { ActivityMenu } from '@mail/core/web/activity_menu';
import { DebugMenu } from "@web/core/debug/debug_menu";
import { session } from '@web/session';

patch(MessagingMenu.prototype, {
    setup() {
        var res = super.setup()
        this.state = useState({
            seller: session.is_admin
        });
        return res
    },
})

patch(DebugMenu.prototype, {
    setup() {
        this.state = useState({
            seller: session.is_admin
        });
        return super.setup()
    },
})

patch(ActivityMenu.prototype, {
    setup() {
        var res = super.setup()
        this.state = useState({
            seller: session.is_admin
        });
        return res
    }
})

patch(Message.prototype, {
    onClick(ev) {
        if (!session.is_admin && ev.target.closest(".o_mail_redirect")) {
            ev.preventDefault();
            return false
        }
        return super.onClick(ev)
    },
})
