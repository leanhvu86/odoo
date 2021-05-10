odoo.define('web_google_maps.view_registry', function (require) {
    "use strict";

    var MapView = require('web_google_maps.MapView');
    var view_registry = require('web.view_registry');
    var RouteView = require('web_google_maps.RouteView');
    var ChatView = require('web_google_maps.ChatView');
    var ReportView = require('web_google_maps.ReportView');
    view_registry.add('map', MapView);
    view_registry.add('route', RouteView);
    view_registry.add('chat', ChatView);
    view_registry.add('report', ReportView);

});
