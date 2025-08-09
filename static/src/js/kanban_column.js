/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { KanbanColumnQuickCreate } from "@web/views/kanban/kanban_column_quick_create";


    KanbanColumnQuickCreate.include({

        init: function (parent, data, options, recordOptions) {
            this._super(parent, data, options, recordOptions);
            if(data.context.no_archive == 1){
                this.has_active_field = false;
            }
        },
    });

