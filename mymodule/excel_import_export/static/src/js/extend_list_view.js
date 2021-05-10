odoo.define('excel_import_export.action_button', function (require) {
    "use strict";
    /**
     * Button 'Create' is replaced by Custom Button
     **/
    var core = require('web.core');
    var ListController = require('web.ListController');
    ListController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            console.log('122222')
            if (this.$buttons) {
                this.$buttons.find('.o_list_export_xlsx').click(this.proxy('action_def'));
            }
        },
        //--------------------------------------------------------------------------
        // Define Handler for new Custom Button
        //--------------------------------------------------------------------------
        /**
         * @private
         * @param {MouseEvent} event
         */
        action_def: function (e) {
            var self = this;
            if (self.modelName == 'weight.unit') {
                var active_id = this.model.get(this.handle).getContext()['active_ids'];
                var model_name = this.model.get(this.handle).getContext()['active_model'];
                console.log('1212')
                self.do_action('excel_import_export.action_report_res_user');
                return
                /*this._rpc({
                    model: 'weight.unit',
                    method: 'js_python_method',
0                }).then(function (result) {
                    // console.log(result, '111111111')
                });*/
            }
            return
        },
    });
});