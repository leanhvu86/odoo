odoo.define('share_van_order.tree_view_button', function (require){
    "use strict";
    var core = require('web.core');
    var ListView = require('web.ListView');
    var ListController = require("web.ListController");

    var includeDict = {
        renderButtons: function () {
            this._super.apply(this, arguments);
            if (this.modelName == 'sharevan.bidding.vehicle') {
                var your_btn = this.$buttons.find('button.o_list_button_custom_print');
                your_btn.on('click', this.proxy('o_list_button_custom_print'));
            }
        },
        o_list_button_custom_print: function(){
            this.do_action({
                name: "Open a wizard",
                type: 'ir.actions.act_window',
                res_model: 'sharevan.bidding.vehicle',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
            });
        }
    };

    ListController.include(includeDict);
});