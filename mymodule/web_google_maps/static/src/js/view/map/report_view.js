odoo.define('web_google_maps.ReportView', function (require) {
    'use strict';

    var BasicView = require('web.BasicView');
    var core = require('web.core');

    var MapModel = require('web_google_maps.MapModel');
    var ReportRenderer = require('web_google_maps.ReportRenderer');
    var MapController = require('web_google_maps.MapController');

    var _lt = core._lt;

    var ReportView = BasicView.extend({
        accesskey: 'c',
        display_name: _lt('Report'),
        icon: 'fa-comments',
        config: _.extend({}, BasicView.prototype.config, {
            // Model: MapModel,
            Renderer: ReportRenderer,
            // Controller: MapController
        }),
        viewType: 'report',
        mobile_friendly: true,
        init: function (viewInfo, params) {
            this._super.apply(this, arguments);

            // var arch = this.arch;
            // var attrs = arch.attrs;
            //
            // var activeActions = this.controllerParams.activeActions;
            // var mode = arch.attrs.editable && !params.readonly ? "edit" : "readonly";

            // this.loadParams.limit = this.loadParams.limit || 80;
            // this.loadParams.openGroupByDefault = true;
            // this.loadParams.type = 'list';
            // this.loadParams.groupBy = arch.attrs.default_group_by ? [arch.attrs.default_group_by] : (params.groupBy || []);

            // this.rendererParams.arch = arch;
            // this.rendererParams.mapLibrary = attrs.library;
            // this.rendererParams.model = attrs.model;
            // this.rendererParams.record_options = {
            //     editable: activeActions.edit,
            //     deletable: activeActions.delete,
            //     read_only_mode: params.readOnlyMode || true,
            // };
            //
            // this.controllerParams.mode = mode;
            // this.controllerParams.hasButtons = true;
        }
    });

    return ReportView;

});