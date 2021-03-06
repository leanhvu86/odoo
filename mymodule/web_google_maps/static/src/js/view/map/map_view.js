odoo.define('web_google_maps.MapView', function (require) {
    'use strict';

    var BasicView = require('web.BasicView');
    var core = require('web.core');

    var MapModel = require('web_google_maps.MapModel');
    var MapRenderer = require('web_google_maps.MapRenderer');
    var MapController = require('web_google_maps.MapController');

    var _lt = core._lt;

    var MapView = BasicView.extend({
        accesskey: 'm',
        display_name: _lt('Map'),
        icon: 'fa-map-o',
        config: _.extend({}, BasicView.prototype.config, {
            Model: MapModel,
            Renderer: MapRenderer,
            Controller: MapController
        }),
        viewType: 'map',
        mobile_friendly: true,
        init: function (viewInfo, params) {
            this._super.apply(this, arguments);

            var arch = this.arch;
            var attrs = arch.attrs;
            console.log('boxbox', attrs);
            console.log('boxbox_param', params);
            console.log('view initial');
            window.model_current = viewInfo.model; //set model current khi vao map view dinh nghia no dang o view model nao
            window.isClickVehicle = false // set k show infor vào vehicle nào

            var activeActions = this.controllerParams.activeActions;
            var mode = arch.attrs.editable && !params.readonly ? "edit" : "readonly";

            this.loadParams.limit = this.loadParams.limit || 80;
            this.loadParams.openGroupByDefault = true;
            this.loadParams.type = 'list';

            this.loadParams.groupBy = arch.attrs.default_group_by ? [arch.attrs.default_group_by] : (params.groupBy || []);

            this.rendererParams.arch = arch;
            this.rendererParams.mapLibrary = attrs.library;
            this.rendererParams.model = attrs.model;
            if (attrs.library === 'drawing') {
                this.rendererParams.drawingMode = attrs.drawing_mode;
                this.rendererParams.drawingPath = attrs.drawing_path;
            } else if (attrs.library === 'geometry') {
                var colors = this._setMarkersColor(attrs.colors);
                this.rendererParams.markerColor = attrs.color;
                this.rendererParams.markerColors = colors;
                this.rendererParams.fieldLat = attrs.lat;
                this.rendererParams.fieldLng = attrs.lng;
            }

            this.rendererParams.record_options = {
                editable: activeActions.edit,
                deletable: activeActions.delete,
                read_only_mode: params.readOnlyMode || true,
            };

            this.controllerParams.mode = mode;
            this.controllerParams.hasButtons = true;
        },
        _setMarkersColor: function (colors) {
            var pair, color, expr;
            if (!colors) {
                return false;
            }
            return _(colors.split(';'))
                .chain()
                .compact()
                .map(function (color_pair) {
                    pair = color_pair.split(':');
                    color = pair[0];
                    expr = pair[1];
                    return [color, py.parse(py.tokenize(expr)), expr];
                }).value();
        }
    });

    return MapView;

});

odoo.define('web_google_maps.RouteView', function (require) {
    'use strict';

    var BasicView = require('web.BasicView');
    var core = require('web.core');

    var MapModel = require('web_google_maps.MapModel');
    var RouteRenderer = require('web_google_maps.RouteRenderer');
    var MapController = require('web_google_maps.MapController');

    var _lt = core._lt;

    var RouteView = BasicView.extend({
        accesskey: 'm',
        display_name: _lt('Route'),
        icon: 'fa-map-signs',
        config: _.extend({}, BasicView.prototype.config, {
            Model: MapModel,
            Renderer: RouteRenderer,
            Controller: MapController
        }),
        viewType: 'route',
        mobile_friendly: true,
        init: function (viewInfo, params) {
            this._super.apply(this, arguments);

            var arch = this.arch;
            var attrs = arch.attrs;
            console.log('boxbox route', attrs);
            console.log('boxbox_param route', params);
            console.log('view initial');

            var activeActions = this.controllerParams.activeActions;
            var mode = arch.attrs.editable && !params.readonly ? "edit" : "readonly";

            this.loadParams.limit = this.loadParams.limit || 80;
            this.loadParams.openGroupByDefault = true;
            this.loadParams.type = 'list';

            this.loadParams.groupBy = arch.attrs.default_group_by ? [arch.attrs.default_group_by] : (params.groupBy || []);

            this.rendererParams.arch = arch;
            this.rendererParams.mapLibrary = attrs.library;
            this.rendererParams.model = attrs.model;
            if (attrs.library === 'drawing') {
                this.rendererParams.drawingMode = attrs.drawing_mode;
                this.rendererParams.drawingPath = attrs.drawing_path;
            } else if (attrs.library === 'geometry') {
                var colors = this._setMarkersColor(attrs.colors);
                this.rendererParams.markerColor = attrs.color;
                this.rendererParams.markerColors = colors;
                this.rendererParams.fieldLat = attrs.lat;
                this.rendererParams.fieldLng = attrs.lng;
            }

            this.rendererParams.record_options = {
                editable: activeActions.edit,
                deletable: activeActions.delete,
                read_only_mode: params.readOnlyMode || true,
            };

            this.controllerParams.mode = mode;
            this.controllerParams.hasButtons = true;
        },
        _setMarkersColor: function (colors) {
            var pair, color, expr;
            if (!colors) {
                return false;
            }
            return _(colors.split(';'))
                .chain()
                .compact()
                .map(function (color_pair) {
                    pair = color_pair.split(':');
                    color = pair[0];
                    expr = pair[1];
                    return [color, py.parse(py.tokenize(expr)), expr];
                }).value();
        }
    });

    return RouteView;

});
odoo.define('web_google_maps.ChatView', function (require) {
    'use strict';

    var BasicView = require('web.BasicView');
    var core = require('web.core');

    var MapModel = require('web_google_maps.MapModel');
    var ChatRenderer = require('web_google_maps.ChatRenderer');
    var MapController = require('web_google_maps.MapController');

    var _lt = core._lt;

    var ChatView = BasicView.extend({
        accesskey: 'c',
        display_name: _lt('Chat'),
        icon: 'fa-comments',
        config: _.extend({}, BasicView.prototype.config, {
            Model: MapModel,
            Renderer: ChatRenderer,
            Controller: MapController
        }),
        viewType: 'chat',
        mobile_friendly: true,
        init: function (viewInfo, params) {
            this._super.apply(this, arguments);

            var arch = this.arch;
            var attrs = arch.attrs;

            var activeActions = this.controllerParams.activeActions;
            var mode = arch.attrs.editable && !params.readonly ? "edit" : "readonly";

            this.loadParams.limit = this.loadParams.limit || 80;
            this.loadParams.openGroupByDefault = true;
            this.loadParams.type = 'list';

            this.loadParams.groupBy = arch.attrs.default_group_by ? [arch.attrs.default_group_by] : (params.groupBy || []);

            this.rendererParams.arch = arch;
            this.rendererParams.mapLibrary = attrs.library;
            this.rendererParams.model = attrs.model;
            this.rendererParams.record_options = {
                editable: activeActions.edit,
                deletable: activeActions.delete,
                read_only_mode: params.readOnlyMode || true,
            };

            this.controllerParams.mode = mode;
            this.controllerParams.hasButtons = true;
        }
    });

    return ChatView;

});