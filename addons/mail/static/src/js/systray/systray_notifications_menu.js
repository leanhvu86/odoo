odoo.define('mail.systray.NotificationsMenu', function (require) {
    "use strict";

    var core = require('web.core');
    var session = require('web.session');
    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');
    var QWeb = core.qweb;
    /**
     * Menu item appended in the systray part of the navbar, redirects to the next
     * activities of all app
     */
    var NotificationsMenu = Widget.extend({
        name: 'notifications_menu',
        template: 'mail.systray.NotificationsMenu',
        events: {
            'click .o_systray_activity': '_onActivityActionClick',
            'click .o_no_notification': '_onNotificationsFilterClick',
            'scroll .o_mail_systray_dropdown': '_actionScroll',
            'show.bs.dropdown': '_onNotificationsMenuShow',
            'click #load_more_notifications': '_onLoadMoreNotifications',

        },
        init: function (parent, data, options, recordOptions) {
            this._super(parent);
            this.current_page = 1;
            this.total_page = 0;
            this.page = 0;
            this.limit = 10;
            this.array = [];
            this.click_check = true;
        },

        start: function () {
            this._$activitiesPreview = this.$('.o_mail_systray_dropdown_items');
            // this.call('mail_service', 'getMailBus').on('activity_updated', this, this._updateCounter);
            // this._updateCounter();
            this._updateActivityPreview();
            return this._super();
        },
        // //--------------------------------------------------
        // // Private
        // //--------------------------------------------------
        // /**
        //  * Make RPC and get current user's activity details
        //  * @private
        //  */
        _getNotificationsData: function () {
            var self = this;
            return self._rpc({
                model: 'res.users',
                method: 'systray_get_notifications',
                args: [self.page, self.limit],
                kwargs: {context: session.user_context},
            }).then(function (data) {
                if (self.click_check == true) {
                    self.array = self.array.concat(data.data);
                    self._activities = self.array;
                    self.total_page = data.total_page;
                    self.count = self._activities.filter(word => word.status == "new").length;
                    if (self.count > 0) {
                        self.$('.o_notification_count').text(self.count);
                    }
                    if (self.count == 0) {
                        $(".o_notification_count").css("display", "none");
                        self.$('.o_notification_count').text(0);

                    }
                }

            });
        },
        // /**
        //  * Get particular model view to redirect on click of activity scheduled on that model.
        //  * @private
        //  * @param {string} model
        //  */
        // /**
        //  * Update(render) activity system tray view on activity updation.
        //  * @private
        //  */


        _updateActivityPreview: function () {
            var self = this;
            self._getNotificationsData().then(function () {
                self._$activitiesPreview.appendTo(self._$activitiesPreview.html(QWeb.render('mail.systray.NotificationsMenu.Previews', {
                    widget: self
                })));

            });
            QWeb.render
        },
        _onLoadMoreNotifications: function (event) {
            this.current_page += 1;
            this.page += 1;
            this.click_check = true;
            this._updateActivityPreview();
            event.stopPropagation();
        },

        _onActivityActionClick: function (event) {
            var id = event.currentTarget.attributes.id.value;
            var res_model = event.currentTarget.attributes.resmodel.value;
            var res_id = event.currentTarget.attributes.resid.value;
            var notification_type = event.currentTarget.attributes.noti.value;

            self = this;
            self._rpc({
                model: 'res.users',
                method: 'change_notifications',
                args: [id],
                kwargs: {context: session.user_context},
                // args: [1],
            }).then(function () {
                if (notification_type == "sos") {

                    self.do_action({
                        type: 'ir.actions.act_window',
                        name: 'Fleet vehicle',
                        res_model: 'fleet.vehicle',
                        view_mode: 'map',
                        // res_id: Number(res_id),
                        views: [[false, 'map']],
                        search_view_id: [false]
                    });

                } else {
                    self.do_action({
                        type: 'ir.actions.act_window',
                        name: 'Fleet vehicle',
                        res_model: res_model,
                        res_id: Number(res_id),
                        views: [[false, 'form']],
                        search_view_id: [false],
                    });
                }


                self.count -= 1;
                if (self.count == 0) {
                    $(".o_notification_count").css("display", "none");
                    self.$('.o_notification_count').text(0);
                }
                self.$('.o_notification_count').text(self.count);
            });


        },
        //
        // /**
        //  * Redirect to particular model view
        //  * @private
        //  * @param {MouseEvent} event
        //  */

        _onNotificationsMenuShow: function () {
            this._updateActivityPreview();
            this.click_check = false;
        },
    });

    SystrayMenu.Items.push(NotificationsMenu);

    return NotificationsMenu;

});
