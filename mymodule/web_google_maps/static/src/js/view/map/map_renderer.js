odoo.define('web_google_maps.MapRenderer', function (require) {
    'use strict';

    const EVENT_VEHICLE = {
        BUZZER_ON: 'engineStop',
        BUZZER_OFF: 'engineResume',
        CUSTOM_COMMAND: 'customCommand',
        DRAW_GEOFENCE: 'drawGeofence'
    }

    var Notification = require("web.Notification");
    var rpc = require("web.rpc");
    var BasicRenderer = require('web.BasicRenderer');
    var core = require('web.core');
    var QWeb = require('web.QWeb');
    var session = require('web.session');
    var utils = require('web.utils');
    var Widget = require('web.Widget');
    var FieldManagerMixin = require('web.FieldManagerMixin');
    var ServicesMixin = require('web.ServicesMixin');
    var relational_fields = require('web.relational_fields');
    var KanbanRecord = require('web.KanbanRecord');
    var _t = core._t;
    var ajax = require('web.ajax');
    var qweb = core.qweb;
    var mapCenter; //map current
    var mapWindow;
    var mapClearMarker;
    var funcGetInfoSocket = 0;
    var onChooseVehicle = 0;
    var onChooseVehicleNotClick = 0;
    var self = this, protocol, pathname, socket;
    var url_iot = session.iot_port.replace(/(^\w+:|^)\/\//, ''); // replace http
    protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    var MARKER_COLORS = [
        'green', 'yellow', 'blue', 'light-green',
        'red', 'magenta'
    ];

    var MAP_THEMES = {
        'default': [],
        'aubergine': [{
            "elementType": "geometry",
            "stylers": [{
                "color": "#1d2c4d"
            }]
        },
            {
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#8ec3b9"
                }]
            },
            {
                "elementType": "labels.text.stroke",
                "stylers": [{
                    "color": "#1a3646"
                }]
            },
            {
                "featureType": "administrative.country",
                "elementType": "geometry.stroke",
                "stylers": [{
                    "color": "#4b6878"
                }]
            },
            {
                "featureType": "administrative.land_parcel",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#64779e"
                }]
            },
            {
                "featureType": "administrative.province",
                "elementType": "geometry.stroke",
                "stylers": [{
                    "color": "#4b6878"
                }]
            },
            {
                "featureType": "landscape.man_made",
                "elementType": "geometry.stroke",
                "stylers": [{
                    "color": "#334e87"
                }]
            },
            {
                "featureType": "landscape.natural",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#023e58"
                }]
            },
            {
                "featureType": "poi",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#283d6a"
                }]
            },
            {
                "featureType": "poi",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#6f9ba5"
                }]
            },
            {
                "featureType": "poi",
                "elementType": "labels.text.stroke",
                "stylers": [{
                    "color": "#1d2c4d"
                }]
            },
            {
                "featureType": "poi.business",
                "stylers": [{
                    "visibility": "off"
                }]
            },
            {
                "featureType": "poi.park",
                "elementType": "geometry.fill",
                "stylers": [{
                    "color": "#023e58"
                }]
            },
            {
                "featureType": "poi.park",
                "elementType": "labels.text",
                "stylers": [{
                    "visibility": "off"
                }]
            },
            {
                "featureType": "poi.park",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#3C7680"
                }]
            },
            {
                "featureType": "road",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#304a7d"
                }]
            },
            {
                "featureType": "road",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#98a5be"
                }]
            },
            {
                "featureType": "road",
                "elementType": "labels.text.stroke",
                "stylers": [{
                    "color": "#1d2c4d"
                }]
            },
            {
                "featureType": "road.highway",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#2c6675"
                }]
            },
            {
                "featureType": "road.highway",
                "elementType": "geometry.stroke",
                "stylers": [{
                    "color": "#255763"
                }]
            },
            {
                "featureType": "road.highway",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#b0d5ce"
                }]
            },
            {
                "featureType": "road.highway",
                "elementType": "labels.text.stroke",
                "stylers": [{
                    "color": "#023e58"
                }]
            },
            {
                "featureType": "transit",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#98a5be"
                }]
            },
            {
                "featureType": "transit",
                "elementType": "labels.text.stroke",
                "stylers": [{
                    "color": "#1d2c4d"
                }]
            },
            {
                "featureType": "transit.line",
                "elementType": "geometry.fill",
                "stylers": [{
                    "color": "#283d6a"
                }]
            },
            {
                "featureType": "transit.station",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#3a4762"
                }]
            },
            {
                "featureType": "water",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#0e1626"
                }]
            },
            {
                "featureType": "water",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#4e6d70"
                }]
            }
        ],
        'night': [{
            "elementType": "geometry",
            "stylers": [{
                "color": "#242f3e"
            }]
        },
            {
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#746855"
                }]
            },
            {
                "elementType": "labels.text.stroke",
                "stylers": [{
                    "color": "#242f3e"
                }]
            },
            {
                "featureType": "administrative.locality",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#d59563"
                }]
            },
            {
                "featureType": "poi",
                "elementType": "labels.text",
                "stylers": [{
                    "visibility": "off"
                }]
            },
            {
                "featureType": "poi",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#d59563"
                }]
            },
            {
                "featureType": "poi.business",
                "stylers": [{
                    "visibility": "off"
                }]
            },
            {
                "featureType": "poi.park",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#263c3f"
                }]
            },
            {
                "featureType": "poi.park",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#6b9a76"
                }]
            },
            {
                "featureType": "road",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#38414e"
                }]
            },
            {
                "featureType": "road",
                "elementType": "geometry.stroke",
                "stylers": [{
                    "color": "#212a37"
                }]
            },
            {
                "featureType": "road",
                "elementType": "labels.icon",
                "stylers": [{
                    "visibility": "off"
                }]
            },
            {
                "featureType": "road",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#9ca5b3"
                }]
            },
            {
                "featureType": "road.highway",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#746855"
                }]
            },
            {
                "featureType": "road.highway",
                "elementType": "geometry.stroke",
                "stylers": [{
                    "color": "#1f2835"
                }]
            },
            {
                "featureType": "road.highway",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#f3d19c"
                }]
            },
            {
                "featureType": "transit",
                "stylers": [{
                    "visibility": "off"
                }]
            },
            {
                "featureType": "transit",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#2f3948"
                }]
            },
            {
                "featureType": "transit.station",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#d59563"
                }]
            },
            {
                "featureType": "water",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#17263c"
                }]
            },
            {
                "featureType": "water",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#515c6d"
                }]
            },
            {
                "featureType": "water",
                "elementType": "labels.text.stroke",
                "stylers": [{
                    "color": "#17263c"
                }]
            }
        ],
        'dark': [{
            "elementType": "geometry",
            "stylers": [{
                "color": "#212121"
            }]
        },
            {
                "elementType": "labels.icon",
                "stylers": [{
                    "visibility": "off"
                }]
            },
            {
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#757575"
                }]
            },
            {
                "elementType": "labels.text.stroke",
                "stylers": [{
                    "color": "#212121"
                }]
            },
            {
                "featureType": "administrative",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#757575"
                }]
            },
            {
                "featureType": "administrative.country",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#9e9e9e"
                }]
            },
            {
                "featureType": "administrative.land_parcel",
                "stylers": [{
                    "visibility": "off"
                }]
            },
            {
                "featureType": "administrative.locality",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#bdbdbd"
                }]
            },
            {
                "featureType": "poi",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#757575"
                }]
            },
            {
                "featureType": "poi.park",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#181818"
                }]
            },
            {
                "featureType": "poi.park",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#616161"
                }]
            },
            {
                "featureType": "poi.park",
                "elementType": "labels.text.stroke",
                "stylers": [{
                    "color": "#1b1b1b"
                }]
            },
            {
                "featureType": "road",
                "elementType": "geometry.fill",
                "stylers": [{
                    "color": "#2c2c2c"
                }]
            },
            {
                "featureType": "road",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#8a8a8a"
                }]
            },
            {
                "featureType": "road.arterial",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#373737"
                }]
            },
            {
                "featureType": "road.highway",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#3c3c3c"
                }]
            },
            {
                "featureType": "road.highway.controlled_access",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#4e4e4e"
                }]
            },
            {
                "featureType": "road.local",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#616161"
                }]
            },
            {
                "featureType": "transit",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#757575"
                }]
            },
            {
                "featureType": "water",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#000000"
                }]
            },
            {
                "featureType": "water",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#3d3d3d"
                }]
            }
        ],
        'retro': [{
            "elementType": "geometry",
            "stylers": [{
                "color": "#ebe3cd"
            }]
        },
            {
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#523735"
                }]
            },
            {
                "elementType": "labels.text.stroke",
                "stylers": [{
                    "color": "#f5f1e6"
                }]
            },
            {
                "featureType": "administrative",
                "elementType": "geometry.stroke",
                "stylers": [{
                    "color": "#c9b2a6"
                }]
            },
            {
                "featureType": "administrative.land_parcel",
                "elementType": "geometry.stroke",
                "stylers": [{
                    "color": "#dcd2be"
                }]
            },
            {
                "featureType": "administrative.land_parcel",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#ae9e90"
                }]
            },
            {
                "featureType": "landscape.natural",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#dfd2ae"
                }]
            },
            {
                "featureType": "poi",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#dfd2ae"
                }]
            },
            {
                "featureType": "poi",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#93817c"
                }]
            },
            {
                "featureType": "poi.park",
                "elementType": "geometry.fill",
                "stylers": [{
                    "color": "#a5b076"
                }]
            },
            {
                "featureType": "poi.park",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#447530"
                }]
            },
            {
                "featureType": "road",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#f5f1e6"
                }]
            },
            {
                "featureType": "road.arterial",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#fdfcf8"
                }]
            },
            {
                "featureType": "road.highway",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#f8c967"
                }]
            },
            {
                "featureType": "road.highway",
                "elementType": "geometry.stroke",
                "stylers": [{
                    "color": "#e9bc62"
                }]
            },
            {
                "featureType": "road.highway.controlled_access",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#e98d58"
                }]
            },
            {
                "featureType": "road.highway.controlled_access",
                "elementType": "geometry.stroke",
                "stylers": [{
                    "color": "#db8555"
                }]
            },
            {
                "featureType": "road.local",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#806b63"
                }]
            },
            {
                "featureType": "transit.line",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#dfd2ae"
                }]
            },
            {
                "featureType": "transit.line",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#8f7d77"
                }]
            },
            {
                "featureType": "transit.line",
                "elementType": "labels.text.stroke",
                "stylers": [{
                    "color": "#ebe3cd"
                }]
            },
            {
                "featureType": "transit.station",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#dfd2ae"
                }]
            },
            {
                "featureType": "water",
                "elementType": "geometry.fill",
                "stylers": [{
                    "color": "#b9d3c2"
                }]
            },
            {
                "featureType": "water",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#92998d"
                }]
            }
        ],
        'silver': [{
            "elementType": "geometry",
            "stylers": [{
                "color": "#f5f5f5"
            }]
        },
            {
                "elementType": "labels.icon",
                "stylers": [{
                    "visibility": "off"
                }]
            },
            {
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#616161"
                }]
            },
            {
                "elementType": "labels.text.stroke",
                "stylers": [{
                    "color": "#f5f5f5"
                }]
            },
            {
                "featureType": "administrative.land_parcel",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#bdbdbd"
                }]
            },
            {
                "featureType": "poi",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#eeeeee"
                }]
            },
            {
                "featureType": "poi",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#757575"
                }]
            },
            {
                "featureType": "poi.park",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#e5e5e5"
                }]
            },
            {
                "featureType": "poi.park",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#9e9e9e"
                }]
            },
            {
                "featureType": "road",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#ffffff"
                }]
            },
            {
                "featureType": "road.arterial",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#757575"
                }]
            },
            {
                "featureType": "road.highway",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#dadada"
                }]
            },
            {
                "featureType": "road.highway",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#616161"
                }]
            },
            {
                "featureType": "road.local",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#9e9e9e"
                }]
            },
            {
                "featureType": "transit.line",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#e5e5e5"
                }]
            },
            {
                "featureType": "transit.station",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#eeeeee"
                }]
            },
            {
                "featureType": "water",
                "elementType": "geometry",
                "stylers": [{
                    "color": "#c9c9c9"
                }]
            },
            {
                "featureType": "water",
                "elementType": "labels.text.fill",
                "stylers": [{
                    "color": "#9e9e9e"
                }]
            }
        ]
    }

    var MapRecord = KanbanRecord.extend({
        init: function (parent, state, options) {
            this._super.apply(this, arguments);
            this.fieldsInfo = state.fieldsInfo.map;
        }
    });

    function findInNode(node, predicate) {
        if (predicate(node)) {
            return node;
        }
        if (!node.children) {
            return undefined;
        }
        for (var i = 0; i < node.children.length; i++) {
            if (findInNode(node.children[i], predicate)) {
                return node.children[i];
            }
        }
    }

    function _sendCommand(self, url, body) {
        fetch(url, {
            method: 'post',
            headers: {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify(body)
        }).then(res => res.json())
            .then(res => console.log(res)).catch(() => {
            self.do_notify(_t("Error!"), _t("Error connecting to server!"));
        });
    }

    function qwebAddIf(node, condition) {
        if (node.attrs[qweb.prefix + '-if']) {
            condition = _.str.sprintf("(%s) and (%s)", node.attrs[qweb.prefix + '-if'], condition);
        }
        node.attrs[qweb.prefix + '-if'] = condition;
    }

    function transformQwebTemplate(node, fields) {
        // Process modifiers
        if (node.tag && node.attrs.modifiers) {
            var modifiers = node.attrs.modifiers || {};
            if (modifiers.invisible) {
                qwebAddIf(node, _.str.sprintf("!kanban_compute_domain(%s)", JSON.stringify(modifiers.invisible)));
            }
        }
        switch (node.tag) {
            case 'button':
            case 'a':
                var type = node.attrs.type || '';
                if (_.indexOf('action,object,edit,open,delete,url,set_cover'.split(','), type) !== -1) {
                    _.each(node.attrs, function (v, k) {
                        if (_.indexOf('icon,type,name,args,string,context,states,kanban_states'.split(','), k) !== -1) {
                            node.attrs['data-' + k] = v;
                            delete (node.attrs[k]);
                        }
                    });
                    if (node.attrs['data-string']) {
                        node.attrs.title = node.attrs['data-string'];
                    }
                    if (node.tag === 'a' && node.attrs['data-type'] !== "url") {
                        node.attrs.href = '#';
                    } else {
                        node.attrs.type = 'button';
                    }

                    var action_classes = " oe_kanban_action oe_kanban_action_" + node.tag;
                    if (node.attrs['t-attf-class']) {
                        node.attrs['t-attf-class'] += action_classes;
                    } else if (node.attrs['t-att-class']) {
                        node.attrs['t-att-class'] += " + '" + action_classes + "'";
                    } else {
                        node.attrs['class'] = (node.attrs['class'] || '') + action_classes;
                    }
                }
                break;
        }
        if (node.children) {
            for (var i = 0, ii = node.children.length; i < ii; i++) {
                transformQwebTemplate(node.children[i], fields);
            }
        }
    }

    var SidebarGroup = Widget.extend({
        template: 'MapView.MapViewGroupInfo',
        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.groups = options.groups;
        }
    });

    var SidebarGroupv2 = Widget.extend({
        template: 'MapView.MapViewItem',
        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.groups = options.groups;
        }
    });

    var MapRenderer = BasicRenderer.extend({
        className: 'o_map_view',
        template: 'MapView.MapView',
        /**
         * @override
         */
        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            this.mapLibrary = params.mapLibrary;
            this.modelInput = params.model;
            this.widgets = [];
            this.mapThemes = MAP_THEMES;
            this.qweb = new QWeb(session.debug, {
                _s: session.origin
            }, false);
            var templates = findInNode(this.arch, function (n) {
                return n.tag === 'templates';
            });
            transformQwebTemplate(templates, state.fields);
            this.qweb.add_template(utils.json_node_to_xml(templates));
            this.recordOptions = _.extend({}, params.record_options, {
                qweb: this.qweb,
                viewType: 'map',
            });
            this.state = state;
            this.shapesCache = {};
            this._initLibraryProperties(params);
            this.selected = [];
        },
        _initLibraryProperties: function (params) {
            if (this.mapLibrary === 'drawing') {
                this.drawingMode = params.drawingMode || 'shape_type';
                this.drawingPath = params.drawingPath || 'shape_paths';
                this.shapesLatLng = [];
            } else if (this.mapLibrary === 'geometry') {
                this.defaultMarkerColor = 'red';
                this.markerGroupedInfo = [];
                this.lst_vehicle_id = []
                this.markerCarInfo = [];
                this.markers = [];
                if (this.modelInput !== undefined) {
                    this.iconUrl = '/web_google_maps/static/src/img/markers/' + this.modelInput + '/';
                } else {
                    this.iconUrl = '/web_google_maps/static/src/img/markers/';
                }
                this.fieldLat = params.fieldLat;
                this.fieldLng = params.fieldLng;
                this.markerColor = params.markerColor;
                this.markerColors = params.markerColors;
                this.groupedMarkerColors = _.extend([], params.iconColors);
            }
        },
        /**
         * @override
         */
        updateState: function (state) {
            // console.log("render Update state App", state);
            this._setState(state);
            return this._super.apply(this, arguments);
        },
        _onClickCloseRightSliderBar: function (e) {
            $('#right_sidebar_report').css("display", "none")
        },
        _onClickCloseLeftSliderBar: function (e) {
            var self = this;
            var $input = $(e.currentTarget);
            $('#left_sidebar_first').css("display", "none")
            $('.drag_seperator').css("display", "block")
            window.setTimeout(function () {
                google.maps.event.trigger(mapCenter, 'resize');
            }, 100);
            // google.maps.event.addListener(mapCenter, "idle", function () {
            //     google.maps.event.trigger(mapCenter, 'resize');
            // });

        },
        _onClickOpenLeftSliderBar: function (e) {
            $('#left_sidebar_first').css("display", "block")
            $('.drag_seperator').css("display", "none")
            window.setTimeout(function () {
                google.maps.event.trigger(mapCenter, 'resize');
            }, 100);
        },
        /**
         * @override
         */
        start: function () {
            // console.log("render Initial App");
            this._initMap();
            // console.log("init drag seperator")
            // this._dragOpenCloseSlidebar(this.$seperator, 'left_sidebar_first', 'map_view_second', 'H')
            // this._dragOpenCloseSlidebar(this.$seperator2, 'map_view_second', 'right_sidebar_report', 'H')
            // console.log('init report')
            if (window.model_current == 'fleet.vehicle') {
                this.$el.on('click', '.close-right', this._onClickCloseRightSliderBar.bind(this));
                this.$el.on('click', '.close-left', this._onClickCloseLeftSliderBar.bind(this));
                this.$el.on('click', '.drag_seperator', this._onClickOpenLeftSliderBar.bind(this));
                this.$('.drag_seperator').removeClass('closed')
                this._getInfoSocket();
                // this.sync_socket();
            }
            return this._super();
        },
        _initReport: function () {
            var report = this._rpc({
                route: '/power-bi/embed',
                method: 'search_read',
                params: {},
            }).then(result => {
                    // console.log(result)
                    // Read embed application token from Model
                    var accessToken = result.accessToken
                    // Read embed URL from Model
                    var embedUrl = result.embedUrl;
                    // Read report Id from Model
                    var embedReportId = result.reportId;
                    // Get models. models contains enums that can be used.
                    var models = window['powerbi-client'].models;
                    // Embed configuration used to describe what and how to embed.
                    // This object is used when calling powerbi.embed.
                    // This also includes settings and options such as filters.
                    // You can find more information at https://github.com/Microsoft/PowerBI-JavaScript/wiki/Embed-Configuration-Details.
                    var config = {
                        type: 'report',
                        tokenType: models.TokenType.Embed,
                        accessToken: accessToken,
                        embedUrl: embedUrl,
                        id: embedReportId,
                        permissions: models.Permissions.All,
                        settings: {
                            filterPaneEnabled: true,
                            navContentPaneEnabled: true
                        }
                    };

                    // Get a reference to the embedded report HTML element
                    var reportContainer = this.$('#report_container')[0];
                    // Embed the report and display it within the div container.
                    var report = powerbi.embed(reportContainer, config);
                }
            )
        },
        _dragOpenCloseSlidebar: function (element, left, right, direction, handler) {
            // function is used for dragging and moving
            // Two variables for tracking positions of the cursor
            const drag = {x: 0, y: 0};
            const delta = {x: 0, y: 0};
            /* if present, the handler is where you move the DIV from
            otherwise, move the DIV from anywhere inside the DIV */
            handler ? (handler.onmousedown = dragMouseDown) : (element[0].onmousedown = dragMouseDown);

            // function that will be called whenever the down event of the mouse is raised
            function dragMouseDown(e) {
                drag.x = e.clientX;
                drag.y = e.clientY;
                document.onmousemove = onMouseMove;
                document.onmouseup = () => {
                    document.onmousemove = document.onmouseup = null;
                }
            }

            // function that will be called whenever the up event of the mouse is raised
            function onMouseMove(e) {
                const currentX = e.clientX;
                const currentY = e.clientY;

                delta.x = currentX - drag.x;
                delta.y = currentY - drag.y;

                const offsetLeft = element[0].offsetLeft;
                const offsetTop = element[0].offsetTop;

                const first = document.getElementById(left);
                const second = document.getElementById(right);
                let firstWidth = first.offsetWidth;
                let secondWidth = second.offsetWidth;
                if (direction === "H") // Horizontal
                {
                    element[0].style.left = offsetLeft + delta.x + "px";
                    firstWidth += delta.x;
                    secondWidth -= delta.x;
                }
                drag.x = currentX;
                drag.y = currentY;
                first.style.width = firstWidth + "px";
                second.style.width = secondWidth + "px";
            }
        },
        _getInfoSocket: function () {
            var self = this;
            var intervalID;
            getDevice_status()

            function format_date(date) {
                let datev2 = new Date(date)
                let day = datev2.getDate();
                let month = datev2.getMonth() + 1;
                let year = datev2.getFullYear();
                let hours = datev2.getHours();
                let minutes = datev2.getMinutes();
                let seconds = datev2.getSeconds()
                let yyyy_MM_dd = day + "-" + month + "-" + year + ": " + hours + "h" + minutes + "m" + seconds + "s"; // That's your formatted date.
                return yyyy_MM_dd;
            }

            // pathname = window.location.pathname.substring(0, window.location.pathname.lastIndexOf('/') + 1);
            function animatedMove(marker, t, current, moveto) {
                var lat = current.lat();
                var lng = current.lng();
                var deltalat = (moveto.lat() - current.lat()) / 100;
                var deltalng = (moveto.lng() - current.lng()) / 100;

                var delay = 10 * t;
                for (var i = 0; i < 100; i++) {
                    (function (ind) {
                        setTimeout(
                            function () {
                                var latlng;
                                var lat = marker.position.lat();
                                var lng = marker.position.lng();
                                lat += deltalat;
                                lng += deltalng;
                                latlng = new google.maps.LatLng(lat, lng);
                                marker.setPosition(latlng);
                                // marker.setRotation(120)
                            }, delay * ind
                        );
                    })(i)
                }
            }

            function getDevice_status() {
                var allower_current_company = session.user_context.allowed_company_ids
                var urlStringCompanyID = '';
                allower_current_company.forEach((id) => {
                    urlStringCompanyID += 'companyIds=' + id + '&'
                })
                var url_get_status_device = session.iot_port + '/api/devices;jsessionid=' + session.jsession_iot + '?' + urlStringCompanyID
                fetch(url_get_status_device, {
                    method: 'get',
                    headers: {
                        'Accept': 'application/json, text/plain, */*',
                        'Content-Type': 'application/json'
                    },
                }).then((res) =>
                    res.json()
                ).then(res => {
                    var onlineCount = 0;
                    var offlineCount = 0;
                    var unknownCount = 0;
                    res.forEach((device) => {
                        if (device.status == "online") {
                            onlineCount++;
                        }
                        if (device.status == "offline") {
                            offlineCount++;
                        }
                        if (device.status == "unknown") {
                            unknownCount++;
                        }
                    })
                    $('#offline').text(offlineCount);
                    $('#online').text(onlineCount);
                    $('#unknown').text(unknownCount);
                }).catch((res) => {
                    self.do_notify(_t("Error!"), _t("Connecting to server....."));
                });
            }

            /* web socket */
            function _initSocket() {
                var socketStatus;
                var countTokenFail = 0;
                do {
                    setTimeout(function () {
                        socket = new WebSocket(protocol + '//' + url_iot + '/' + 'api/socket?token=' +
                            session.access_token)
                        socketStatus = socket.readyState;
                        if (socketStatus == 0) {
                            socket.onmessage = function (event) {
                                var location = JSON.parse(event.data)
                                console.log(location)
                                var latLng, lat, lng, rotation, deviceID, speed, status, sos;
                                // set position , attributes
                                if (location.positions && location.positions.length > 0 && location.positions.length == 1 && window.model_current == 'fleet.vehicle') {

                                    deviceID = location.positions[0].deviceId
                                    speed = location.positions[0].speed
                                    sos = location.positions[0].sos_status
                                    //draw if status onl
                                    speed > 1 ? $('#' + deviceID).children("i").css("color", "green") : $('#' + deviceID).children("i").css("color", "#FF9800")
                                    if (sos == 1 || sos == 2) {
                                        $('li[name=' + deviceID + ']>span:first-child').css('display', 'block')
                                    }
                                    sos == 1 || sos == 2 ? $('li[name=' + deviceID + ']>span:first-child').css('display', 'block') : $('li[name=' + deviceID + ']>span:first-child').css('display', 'none')
                                    lat = location.positions[0].latitude
                                    lng = location.positions[0].longitude
                                    rotation = location.positions[0].course
                                    latLng = new google.maps.LatLng(lat, lng);
                                    // qua toc do
                                    if (speed >= 30) {
                                        session.rpc('/send/notification_driver', {
                                            vehicle: deviceID,
                                        })
                                    }
                                    if (onChooseVehicle != 0 && deviceID == onChooseVehicle) {
                                        $('#accuracy').text(location.positions[0].accuracy)
                                        $('#address').text(location.positions[0].latitude + ',' + location.positions[0].longitude)
                                        $('#altitude').text(location.positions[0].altitude)
                                        $('#course').text(location.positions[0].course)
                                        $('#deviceID').text(location.positions[0].deviceid)
                                        $('#deviceTime').text(format_date(location.positions[0].deviceTime))
                                        $('#latitude').text(location.positions[0].latitude)
                                        $('#longitude').text(location.positions[0].longitude)
                                        $('#speed').text(location.positions[0].speed)
                                    }
                                    mapClearMarker.markers.forEach(function (marker) {
                                        if (marker._odooRecord.data.id == deviceID) {
                                            marker.setIcon({
                                                // url: '/web_google_maps/static/src/img/markers/vehicle/car_marker.png',
                                                path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
                                                scale: 4,
                                                strokeColor: '#00F',
                                                rotation: rotation
                                            });
                                            animatedMove(marker, 10, marker.position, latLng);
                                        }
                                    });
                                }
                                if (location.devices) { // set status
                                    deviceID = location.devices[0].id
                                    status = location.devices[0].status
                                    if (status == "online") {
                                        $('li[name=' + deviceID + ']').css("background", "rgba(77, 250, 144, 0.3)")
                                        // $('li[name=' + deviceID + ']').children("i").css("color", "black!important")
                                    }
                                    if (status == "offline") {
                                        $('li[name=' + deviceID + ']').css("background", "rgb(255 84 104 / 30%)")
                                        $('li[name=' + deviceID + ']').children("i").css("color", "black!important")
                                    }
                                    if (status == "unknown") {
                                        $('li[name=' + deviceID + ']').css("background", "rgba(250, 190, 77, 0.3)")
                                    }
                                }
                            };
                            socket.onclose = function () {
                                console.log('socket dong')
                                var readyState = socket.readyState;
                                console.log(readyState)
                                if (intervalID) clearInterval(intervalID) //clear interval k cho goi api nhieu lan
                                funcGetInfoSocket = 1
                                if (countTokenFail === 20) {
                                    window.location.href = "/web/session/logout?redirect=/web/login";
                                }
                                //case mất mạng
                                _initSocket()
                                return
                            };
                            socket.onopen = function (evt) {
                                console.log(socket)
                                console.log(evt)
                                console.log('open socket')
                                countTokenFail = 0 //set về 0
                                funcGetInfoSocket = 0
                                // get status all vehicle every 20s
                                intervalID = setInterval(getDevice_status
                                    , 10000);
                            }
                        } else {
                            countTokenFail++;
                        }
                    }, 5000)
                } while (socketStatus == 3)
            }

            _initSocket()
        },
        sync_socket: function () {
            setInterval(() => {
                if (funcGetInfoSocket == 1) {
                    this._getInfoSocket();
                }
            }, 60000);
        },
        /**
         * Style the map
         * @private
         */
        _getMapTheme: function () {
            var self = this;
            var update_map = function (style) {
                var styledMapType = new google.maps.StyledMapType(self.mapThemes[style], {
                    name: 'Theme',
                });
                self.gmap.setOptions({
                    mapTypeControlOptions: {
                        mapTypeIds: ['roadmap', 'satellite', 'hybrid', 'terrain', 'styled_map'],
                    }
                });
                //Associate the styled map with the MapTypeId and set it to display.
                if (self.theme === 'default') return;
                self.gmap.mapTypes.set('styled_map', styledMapType);
                self.gmap.setMapTypeId('styled_map');
            }
            if (!this.theme) {
                this._rpc({
                    route: '/web/google_map_theme'
                }).then(function (data) {
                    console.log('_rpc', data);
                    if (data.theme && self.mapThemes.hasOwnProperty(data.theme)) {
                        self.theme = data.theme;
                        update_map(data.theme);
                    }
                });
            }
        },
        /**
         * Initialize map
         * @private
         */
        _initMap: function () {
            this.infoWindow = new google.maps.InfoWindow();
            this.$('.o_map_view').empty();

            this.gmap = new google.maps.Map(this.$('.o_map_view').get(0), {
                mapTypeId: google.maps.MapTypeId.ROADMAP,
                minZoom: 3,
                maxZoom: 20,
                fullscreenControl: true,
                mapTypeControl: true
            });

            mapCenter = this.gmap;
            mapWindow = this.infoWindow
            this._getMapTheme();
            if (this.mapLibrary === 'geometry') {
                this._initMarkerCluster();
            }
            this.$left_sidebar = this.$('.o_map_devices');
            this.$right_sidebar = this.$('.o_map_right_sidebar');
            // this.$seperator = this.$('#seperator');
            // this.$seperator2 = this.$('#seperator2');
        },
        _initMarkerCluster: function () {
            // console.log('init Marker')
            this.markerCluster = new MarkerClusterer(this.gmap, [], {
                imagePath: '/web_google_maps/static/lib/markercluster/img/m',
                gridSize: 20,
                maxZoom: 17
            });
        },
        /**
         * Compute marker color
         * @param {any} record
         * @return string
         */
        _getIconColor: function (record) {
            if (this.markerColor) {
                return this.markerColor;
            }

            if (!this.markerColors) {
                return this.defaultMarkerColor;
            }

            var context = _.mapObject(_.extend({}, record.data, {
                uid: session.uid,
                current_date: moment().format('YYYY-MM-DD') // TODO: time, datetime, relativedelta
            }), function (val, key) {
                return (val instanceof Array) ? (_.last(val) || '') : val;
            });
            for (var i = 0; i < this.markerColors.length; i++) {
                var pair = this.markerColors[i];
                var color = pair[0];
                var expression = pair[1];
                if (py.PY_isTrue(py.evaluate(expression, context))) {
                    return color;
                }
                // TODO: handle evaluation errors
            }
            return '';
        },
        /**
         * Create marker
         * @param {any} latLng: instance of google LatLng
         * @param {any} record
         * @param {string} color
         */
        _createMarker: function (latLng, record, color) {
            var options = {
                position: latLng,
                map: this.gmap,
                animation: google.maps.Animation.DROP,
                _odooRecord: record

            };
            if (color >= 0 && this.modelInput == 'vehicle') {
                if (color <= 0 && this.modelInput) {
                    options.icon = {
                        url: this.iconUrl + 'vans.png',
                        labelOrigin: new google.maps.Point(10, 14)
                    }
                    /* options.label = {
                         color: 'red',
                         fontWeight: 'bold',
                         text: 'van',
                         fontSize: '10px'
                     }*/
                } else if (color <= 1500) {
                    options.icon = {
                        url: this.iconUrl + 'green.png',
                        labelOrigin: new google.maps.Point(10, 10)
                    }
                    /* options.label = {
                         color: 'red',
                         fontWeight: 'bold',
                         text: '1ton',
                         fontSize: '10px',
                     }*/
                } else if (color <= 5000) {
                    options.icon = {
                        url: this.iconUrl + '5ton.png',
                        labelOrigin: new google.maps.Point(10, 14)
                    }
                    /* options.label = {
                         color: 'red',
                         fontWeight: 'bold',
                         text: '5ton',
                         fontSize: '10px',
                     }*/
                } else if (color <= 10000) {
                    options.icon = {
                        url: this.iconUrl + '10ton.png',
                        labelOrigin: new google.maps.Point(12, 13)
                    }
                    /*options.label = {
                        color: 'red',
                        fontWeight: 'bold',
                        text: '10ton',
                        fontSize: '9px'
                    }*/
                } else if (color <= 20000) {
                    options.icon = {
                        url: this.iconUrl + '20ton.png',
                        labelOrigin: new google.maps.Point(15, 28)
                    }
                    /* options.label = {
                         color: 'red',
                         fontWeight: 'bold',
                         text: '20ton',
                         fontSize: '10px'
                     }*/
                } else {
                    options.icon = {
                        url: this.iconUrl + 'truck.png',
                        labelOrigin: new google.maps.Point(10, 14)
                    }
                    /*options.label = {
                        color: 'red',
                        fontWeight: 'bold',
                        text: 'truck',
                        fontSize: '10px'
                    }*/
                }
            } else if (color) {
                options.icon = this.iconUrl + color.trim() + '.png';
            }
            if (this.modelInput == 'warehouse') {
                if (record.data.main_type === true) {
                    options.icon = this.iconUrl + 'red.png';
                } else {
                    options.icon = this.iconUrl + 'green.png';
                }
            }
            var marker = new google.maps.Marker(options);
            this.markers.push(marker);
            this._clusterAddMarker(marker);
        }
        ,
        /**
         * Handle Multiple Markers present at the same coordinates
         */
        _clusterAddMarker: function (marker) {
            var _position;
            var markerInClusters = this.markerCluster.getMarkers();
            var existingRecords = [];
            if (markerInClusters.length > 0) {
                markerInClusters.forEach(function (_cMarker) {
                    _position = _cMarker.getPosition();
                    if (marker.getPosition().equals(_position)) {
                        existingRecords.push(_cMarker._odooRecord);
                    }
                });
            }
            this.markerCluster.addMarker(marker);
            google.maps.event.addListener(marker, 'click', this._markerInfoWindow.bind(this, marker, existingRecords));
        }
        ,
        /**
         * Marker info window
         * @param {any} marker: instance of google marker
         * @param {any} record
         * @return function
         */
        _markerInfoWindow: function (marker, currentRecords) {
            var self = this;
            var _content = '';
            var markerRecords = [];
            var markerDiv = document.createElement('div');
            markerDiv.className = 'o_kanban_view o_kanban_grouped';

            var markerContent = document.createElement('div');
            markerContent.className = 'o_kanban_group';
            markerContent.style.padding = '1px'

            if (currentRecords.length > 0) {
                currentRecords.forEach(function (_record) {
                    // check view 1 infor windown khi click icon neu trung position
                    if (window.isClickVehicle && window.model_current == 'fleet.vehicle' && _record.data.id != onChooseVehicle) {
                        return
                    }
                    _content = self._generateMarkerInfoWindow(_record);
                    markerRecords.push(_content);
                    _content.appendTo(markerContent);
                });
            }

            var markerIwContent = this._generateMarkerInfoWindow(marker._odooRecord);

            markerIwContent.appendTo(markerContent);
            // console.log('markerContent', markerContent);
            // console.log('markerIwContent', markerIwContent);

            markerDiv.appendChild(markerContent);
            this.infoWindow.setContent(markerDiv);
            this.infoWindow.open(this.gmap, marker);
        }
        ,
        _shapeInfoWindow: function (record, event) {
            var markerDiv = document.createElement('div');
            markerDiv.className = 'o_kanban_view o_kanban_grouped';

            var markerContent = document.createElement('div');
            markerContent.className = 'o_kanban_group';

            var markerIwContent = this._generateMarkerInfoWindow(record);
            markerIwContent.appendTo(markerContent);

            markerDiv.appendChild(markerContent);
            this.infoWindow.setContent(markerDiv);
            this.infoWindow.setPosition(event.latLng);
            this.infoWindow.open(this.gmap);
        }
        ,
        /**
         * @private
         */
        _generateMarkerInfoWindow: function (record) {
            // console.log('_generateMarkerInfoWindow', record);
            if (this.modelInput == 'vehicle') { // hidden button edit delete
                this.recordOptions.selectionMode = true
            }
            var markerIw = new MapRecord(this, record, this.recordOptions);
            console.log('markerinfo window')
            return markerIw;
        }
        ,
        /**
         * Render markers
         * @private
         * @param {Object} record
         */
        _renderMarkers: function () {
            var isGrouped = !!this.state.groupedBy.length;
            console.log('_renderMarkers', this.state.data);
            if (isGrouped) {
                this._renderGrouped();
            } else {
                this._renderUngrouped();
            }
        }
        ,
        /**
         * Default location
         */
        _getDefaultCoordinate: function () {
            return new google.maps.LatLng(0.0, 0.0);
        }
        ,
        _renderGrouped: function () {
            var self = this;
            var defaultLatLng = this._getDefaultCoordinate();
            var color, latLng, lat, lng, max_tonnage;
            // console.log('render Group data', this.state.data);
            var selected = this.$right_sidebar[0].querySelector('.o_map_filter .o_map_filter_items');
            var listTitle = [];
            if (selected) {
                for (var i = 0; i < selected.children.length; i++) {
                    var node = selected.children[i].childNodes[3].childNodes[5].title;
                    var checked = selected.children[i].childNodes[1].checked;
                    if (node && checked) {
                        listTitle.push(node);
                    }
                }
            }
            _.each(this.state.data, function (record) {
                color = self._getGroupedMarkerColor();
                record.markerColor = color;
                // console.log('List checked group', listTitle)
                if (selected && !listTitle.includes(record.value)) {
                    self.markerGroupedInfo.push({
                        'title': record.value || 'Undefined',
                        'count': record.count,
                        'marker': self.iconUrl + record.markerColor.trim() + '.png',
                        'active': null,
                    });
                    return;
                }
                _.each(record.data, function (rec) {
                    lat = rec.data[self.fieldLat] || 0.0;
                    lng = rec.data[self.fieldLng] || 0.0;
                    latLng = new google.maps.LatLng(lat, lng);
                    if (rec.model == 'fleet.vehicle') {
                        max_tonnage = rec.data.max_tonnage_id || 0
                        self._createMarker(latLng, rec, max_tonnage);
                        var PositionInfo;
                        var idVehicle = rec.data.id;
                        if (rec.data.position_ids.res_ids.length != 0) {
                            var idLastPosition = rec.data.position_ids.res_ids.slice(-1)[0];
                            PositionInfo = idLastPosition
                        }
                        self.markerCarInfo.push({
                            'name': rec.data.license_plate || 'Không xác định',
                            'position': PositionInfo,
                            'id': idVehicle,
                            'iot_type': rec.data.iot_type
                        })
                        self.lst_vehicle_id.push(idVehicle)
                    } else {
                        self._createMarker(latLng, rec, color);
                    }
                });
                self.markerGroupedInfo.push({
                    'title': record.value || 'Undefined',
                    'count': record.count,
                    'marker': self.iconUrl + record.markerColor.trim() + '.png',
                    'active': true,
                });
            });
        }
        ,
        _renderUngrouped: function () {
            var self = this;
            var defaultLatLng = this._getDefaultCoordinate();
            var color, latLng, lat, lng, max_tonnage;

            _.each(this.state.data, function (record) {
                color = self._getIconColor(record);
                lat = record.data[self.fieldLat] || 0.0;
                lng = record.data[self.fieldLng] || 0.0;
                max_tonnage = record.data.max_tonnage_id
                if (record.model == 'fleet.vehicle') {
                    latLng = new google.maps.LatLng(lat, lng);
                    self._createMarker(latLng, record, max_tonnage);
                } else {
                    latLng = new google.maps.LatLng(lat, lng);
                    record.markerColor = color;
                    self._createMarker(latLng, record, color);
                }
            });
        }
        ,
        /**
         * Get color
         * @returns {string}
         */
        _getGroupedMarkerColor: function () {
            var color;
            if (this.groupedMarkerColors.length) {
                color = this.groupedMarkerColors.splice(0, 1)[0];
            } else {
                this.groupedMarkerColors = _.extend([], MARKER_COLORS);
                color = this.groupedMarkerColors.splice(0, 1)[0];
            }
            return color;
        }
        ,
        _drawPolygon: function (record) {
            var polygon;
            var path = record.data[this.drawingPath];
            var value = JSON.parse(path);
            if (Object.keys(value).length > 0) {
                if (this.shapesCache[record.data.id] === undefined) {
                    polygon = new google.maps.Polygon({
                        strokeColor: '#FF0000',
                        strokeOpacity: 0.85,
                        strokeWeight: 1.0,
                        fillColor: '#FF9999',
                        fillOpacity: 0.35,
                        map: this.gmap
                    });
                    polygon.setOptions(value.options);
                    this.shapesCache[record.data.id] = polygon;
                } else {
                    polygon = this.shapesCache[record.data.id];
                    polygon.setMap(this.gmap);
                }
                this.shapesLatLng = this.shapesLatLng.concat(value.options.paths);
                polygon.addListener('click', this._shapeInfoWindow.bind(this, record));
            }
        }
        ,
        _drawCircle: function (record) {
            var circle;
            var path = record.data[this.drawingPath];
            var value = JSON.parse(path);
            if (Object.keys(value).length > 0) {
                if (this.shapesCache[record.data.id] === undefined) {
                    circle = new google.maps.Circle({
                        strokeColor: '#FF0000',
                        strokeOpacity: 0.85,
                        strokeWeight: 1.0,
                        fillColor: '#FF9999',
                        fillOpacity: 0.35,
                        map: this.gmap
                    });
                    circle.setOptions(value.options);
                    this.shapesCache[record.data.id] = circle;
                } else {
                    circle = this.shapesCache[record.data.id];
                    circle.setMap(this.gmap);
                }
                this.shapesBounds.union(circle.getBounds());
                circle.addListener('click', this._shapeInfoWindow.bind(this, record));
            }
        }
        ,
        /**
         * Draw rectangle
         * @param {Object} record
         */
        _drawRectangle: function (record) {
            var rectangle;
            var path = record.data[this.drawingPath];
            var value = JSON.parse(path);
            if (Object.keys(value).length > 0) {
                var shapeOptions = value.options;
                if (this.shapesCache[record.data.id] === undefined) {
                    rectangle = new google.maps.Rectangle({
                        strokeColor: '#FF0000',
                        strokeOpacity: 0.85,
                        strokeWeight: 1.0,
                        fillColor: '#FF9999',
                        fillOpacity: 0.35,
                        map: this.gmap
                    });
                    rectangle.setOptions(shapeOptions);
                    this.shapesCache[record.data.id] = rectangle;
                } else {
                    rectangle = this.shapesCache[record.data.id];
                    rectangle.setMap(this.gmap);
                }

                this.shapesBounds.union(rectangle.getBounds());
                rectangle.addListener('click', this._shapeInfoWindow.bind(this, record));
            }
        }
        ,
        /**
         * Draw shape into the map
         */
        _renderShapes: function () {
            var self = this;
            var shapesToKeep = [];
            this.shapesBounds = new google.maps.LatLngBounds();
            _.each(this.state.data, function (record) {
                if (record.data.hasOwnProperty('id')) {
                    shapesToKeep.push((record.data.id).toString());
                }
                if (record.data[self.drawingMode] === 'polygon') {
                    self._drawPolygon(record);
                } else if (record.data[self.drawingMode] === 'rectangle') {
                    self._drawRectangle(record);
                } else if (record.data[self.drawingMode] === 'circle') {
                    self._drawCircle(record);
                }
            });
            this._cleanShapesInCache(shapesToKeep);
        }
        ,
        /**
         * @private
         * @param {Array} ShapesToKeep contains list of id
         * Remove shapes from the maps without deleting the shape
         * will keep those shapes in cache
         */
        _cleanShapesInCache: function (shapesToKeep) {
            _.each(this.shapesCache, function (shape, id) {
                if (shapesToKeep.indexOf(id) === -1) {
                    shape.setMap(null);
                }
            });
        }
        ,
        /**
         * @override
         */
        _renderView: function () {
            var self = this;
            mapClearMarker = this;
            if (this.mapLibrary === 'geometry') {
                // console.log('render view');
                this.markerGroupedInfo.length = 0;
                this.markerCarInfo.length = 0;
                this.lst_vehicle_id.length = 0;
                this._clearMarkerClusters();
                this._renderMarkers();
                this._clusterMarkers();
                // console.log('renderView', self)

                this.$left_sidebar.empty()
                // clear after back page
                this.$('#right_sidebar_report').css("display", "none")
                this.$('.detailsDevice').css({'display': 'none'})
                this.$('.topInfoVehicle').css({'display': 'none'})
                this.$('.o_map_devices').css({'height': 'calc(100% - 3em)', 'overflow-x': 'auto'})
                if (window.gRenderers) {
                    window.gRenderers.forEach((render) => {
                        render.setMap(null)
                        render = null
                    })
                    window.dMarker.forEach((marker) => {
                        marker.setMap(null)
                    })
                }
                //render add icon routing vehicle
                console.log(this.lst_vehicle_id)
                let current_datetime = new Date()
                let formatted_date = current_datetime.getFullYear() + "-" + self._appendLeadingZeroes(current_datetime.getMonth() + 1)
                    + "-" + self._appendLeadingZeroes(current_datetime.getDate())
                session.rpc('/routing_plan_day/get_driver_routing_distinct_vehicle', {
                    lst_vehicle_ids: this.lst_vehicle_id,
                    date_plan: formatted_date
                }).then((vehicles) => {
                    if (vehicles.records) {
                        vehicles.records.forEach((vehicle) => {
                            this.lst_vehicle_id = this.lst_vehicle_id.filter(val => val != vehicle.vehicle_id)
                            $('li[name=' + vehicle.vehicle_id + ']' + ' #' + vehicle.vehicle_id).before("<i class = 'fa fa-cube' style='float: left;color:green'></i>")
                            $('li[name=' + vehicle.vehicle_id + '] .dropleft').after("<i class = 'fa fa-phone-square' style='float: right;margin-right:5px;font-size:2rem;color:grey'></i>")
                        })
                    }
                })
                return this._super.apply(this, arguments)
                    .then(self._renderSidebarGroup.bind(self))
                    .then(self.mapGeometryCentered.bind(self));
            } else if (this.mapLibrary === 'drawing') {
                this.shapesLatLng.length = 0;
                this._renderShapes();
                return this._super.apply(this, arguments).then(this.mapShapesCentered.bind(this));
            }
            return this._super.apply(this, arguments);
        }
        ,
        _appendLeadingZeroes: function (n) {
            if (n <= 9) {
                return "0" + n;
            }
            return n
        }
        ,
        /**
         * Cluster markers
         * @private
         */
        _clusterMarkers: function () {
            this.markerCluster.addMarkers(this.markers);
        }
        ,
        /*show report*/
        _showReport: function () {
            $('#map_view_second').css("width", '200px');
        },
        _showAllVehicle: function () {
            mapClearMarker.markers.forEach(function (marker) {
                marker.setVisible(true);
            });
        }
        ,
        /**
         * Centering map
         */
        mapShapesCentered: function () {
            var mapBounds = new google.maps.LatLngBounds();
            if (!this.shapesBounds.isEmpty()) {
                mapBounds.union(this.shapesBounds);
            }
            _.each(this.shapesLatLng, function (latLng) {
                mapBounds.extend(latLng);
            });
            this.gmap.fitBounds(mapBounds);
        }
        ,
        /**
         * Centering map
         */
        mapGeometryCentered: function () {
            var self = this;
            var mapBounds = new google.maps.LatLngBounds();

            _.each(this.markers, function (marker) {
                mapBounds.extend(marker.getPosition());
            });
            this.gmap.fitBounds(mapBounds);

            google.maps.event.addListenerOnce(this.gmap, 'idle', function () {
                google.maps.event.trigger(self.gmap, 'resize');
                if (self.gmap.getZoom() > 17) self.gmap.setZoom(17);
            });
        }
        ,
        /**
         * Clear marker clusterer and list markers
         * @private
         */
        _clearMarkerClusters: function () {
            this.markerCluster.clearMarkers();
            this.markers = [];
        }
        ,
        /**
         * Render a sidebar for grouped markers info
         * @private
         */
        _renderSidebarGroup: function () {
            // console.log('Đây là add sidebar')
            if (this.modelInput != 'vehicle') {
                this.$('.o_map_left_sidebar').empty().removeClass('open').addClass('closed');
                this.$('.o_report_right_sidebar').empty().removeClass('open').addClass('closed');
            }
            if (this.markerGroupedInfo.length > 0) {
                this.$right_sidebar.empty().removeClass('closed').addClass('open');
//                var groupInfo = new SidebarGroup(this, {
//                    'groups': this.markerGroupedInfo
//                });
                var filters = [];
                var selected = [];
                this.markerGroupedInfo.forEach(function convert(item) {
                    filters.push({
                        active: item.active,
                        avatar_model: "fleet.vehicle",
                        color_index: false,
                        display: true,
                        label: item.title,
                        value: item.marker,
                        count: item.count
                    });
                    selected.push(item.title);
                });
                var sidebar = new SidebarFilter(this, {
                    'fieldName': SidebarGroup.fields,
                    'filters': filters,
                    avatar_field: "image_128",
                    'selected': selected,
                });
                /*
                groupInfo.appendTo(this.$right_sidebar);*/
                sidebar.appendTo(this.$right_sidebar);
                // console.log('click', this.markerGroupedInfo);
            } else {
                this.$right_sidebar.empty();
                if (!this.$right_sidebar.hasClass('closed')) {
                    this.$right_sidebar.removeClass('open').addClass('closed');
                }
            }
            /*vehicle info*/
            if (this.markerCarInfo.length > 0) {
                var filters = [];
                    this.markerCarInfo.forEach(function convert(item) {
                    filters.push({
                        name: item.name,
                        position: item.position,
                        id: item.id,
                        iot: item.iot_type
                    });
                });
                var sidebarv2 = new SidebarFilterLeft(this, {
                    'fieldName': SidebarGroupv2.fields,
                    'filters': filters,
                    avatar_field: "image_128",
                });
                sidebarv2.appendTo(this.$left_sidebar);

            } else {
                this.$left_sidebar.empty();
                if (!this.$left_sidebar.hasClass('closed')) {
                    this.$left_sidebar.removeClass('open').addClass('closed');
                }
            }
        }
        ,
        /**
         * Sets the current state and updates some internal attributes accordingly.
         *
         * @private
         * @param {Object} state
         */
        _setState: function (state) {
            this.state = state;
            // console.log('state here', state);
            var groupByFieldAttrs = state.fields[state.groupedBy[0]];
            var groupByFieldInfo = state.fieldsInfo.map[state.groupedBy[0]];
            // Deactivate the drag'n'drop if the groupedBy field:
            // - is a date or datetime since we group by month or
            // - is readonly (on the field attrs or in the view)
            var draggable = false;
            if (groupByFieldAttrs) {
                if (groupByFieldAttrs.type === "date" || groupByFieldAttrs.type === "datetime") {
                    draggable = false;
                } else if (groupByFieldAttrs.readonly !== undefined) {
                    draggable = !(groupByFieldAttrs.readonly);
                }
            }
            if (groupByFieldInfo) {
                if (draggable && groupByFieldInfo.readonly !== undefined) {
                    draggable = !(groupByFieldInfo.readonly);
                }
            }
            this.groupedByM2O = groupByFieldAttrs && (groupByFieldAttrs.type === 'many2one');
        }
        ,
    });

    var SidebarFilterM2O = relational_fields.FieldMany2One.extend({
        _getSearchBlacklist: function () {
            return this._super.apply(this, arguments).concat(this.filter_ids || []);
        },
    });

    var SidebarFilterLeft = Widget.extend(FieldManagerMixin, {
        template: 'MapView.sidebar.left',
        // custom_events: _.extend({}, FieldManagerMixin.custom_events, {
        //     field_changed: '_onFieldChanged',
        // }),
        /**
         * @constructor
         * @param {Widget} parent
         * @param {Object} options
         * @param {string} options.fieldName
         * @param {Object[]} options.filters A filter is an object with the
         *   following keys: id, value, label, active, avatar_model, color,
         *   can_be_removed
         * @param {Object} [options.favorite] this is an object with the following
         *   keys: fieldName, model, fieldModel
         */
        init: function (parent, options) {
            this._super.apply(this, arguments);
            FieldManagerMixin.init.call(this);
            this.filters = options.filters;
        },
        /**
         * @override
         */
        willStart: function () {
            var self = this;
            var defs = [this._super.apply(this, arguments)];
            return Promise.all(defs);
        },
        /**
         * @override
         */
        start: function () {
            this._super();
            if (this.many2one) {
                this.many2one.appendTo(this.$el);
                this.many2one.filter_ids = _.without(_.pluck(this.filters, 'value'), 'all');
            }
            this.$el.on('click', '.btn-event', this._onClickEvent.bind(this));
            this.$el.on('click', '.btnSaveGeoFence', this._onClickSaveGeoFence.bind(this));
            this.$el.on('click', 'li .tab-vehicle', this._onClickVehicle.bind(this));
            this.$el.on('click', 'li img', this._onClickCallOrMessage.bind(this));
            this.$el.on('click', 'li buzzer', this._onClickBuzzer.bind(this));
            this.$el.on('click', 'li .fa-phone-square', this._onClickCall.bind(this));


            $(document).on("click", ".btn-modal", function () {
                onChooseVehicleNotClick = $(this).data('id');
            });
            $(document).on('shown.bs.modal', this.$el.get(2), function () {
                if (selectedShape != null) {
                    $('#deleteOverlayButton').remove();
                    selectedShape.setMap(null)
                    $('#info_distance').text(0);
                    $('#info_distance').val(0);
                    $('#lat_geofence').val(0);
                    $('#lng_geofence').val(0);

                }
                var refresh = function () {
                    var center = map.getCenter();
                    google.maps.event.trigger(map, "resize");
                    map.setCenter(center);
                }
                setTimeout(refresh, 200);
                open = true;
            });
            $('body').on('DOMSubtreeModified', $('#info_distance'), function () {
                var distance = $('#info_distance').val();
                distance > 0 ? $(".btnSaveGeoFence").removeAttr("disabled") : $(".btnSaveGeoFence").attr("disabled", "disabled")
            });

            // create new map config-geofence
            // Get Map Geo Center
            var center = {lat: 21.01483, lng: 105.78074};
            var map, selectedShape, drawingManager, mapOptions = {};
            var listenerFiltersApplied = false;
            var circleOptions = {
                fillColor: "#e20000",
                fillOpacity: 0,
                strokeColor: "#e20000",
                strokeWeight: 4,
                strokeOpacity: 1,
                clickable: false,
                editable: true,
                suppressUndo: true,
                zIndex: 999
            };

            function setInitialMapOptions() {
                mapOptions = {
                    zoom: 8,
                    center: center,
                    styles: [
                        // {"featureType": "road", elementType: "geometry", stylers: [{visibility: "off"}]},	//turns off roads geometry
                        // {"featureType": "road", elementType: "labels", stylers: [{visibility: "off"}]},	//turns off roads labels
                        // {"featureType": "poi", elementType: "labels", stylers: [{visibility: "off"}]},  //turns off points of interest lines
                        {"featureType": "poi", elementType: "geometry", stylers: [{visibility: "off"}]},  //turns off points of interest geometry
                        {"featureType": "transit", elementType: "labels", stylers: [{visibility: "off"}]},  //turns off transit lines labels
                        {"featureType": "transit", elementType: "geometry", stylers: [{visibility: "off"}]},	//turns off transit lines geometry
                        {
                            "featureType": "administrative.land_parcel",
                            elementType: "labels",
                            stylers: [{visibility: "off"}]
                        },  //turns off administrative land parcel labels
                        {
                            "featureType": "administrative.land_parcel",
                            elementType: "geometry",
                            stylers: [{visibility: "off"}]
                        },  //turns off administrative land parcel geometry
                        // {"featureType": "water", elementType: "geometry", stylers: [{color: '#d1e1ff'}]},  //sets water color to a very light blue
                        // {"featureType": "landscape", elementType: "geometry", stylers: [{color: '#fffffa'}]},  //sets landscape color to a light white color
                    ],
                    mapTypeControl: false,
                    panControl: true,
                    panControlOptions: {
                        position: google.maps.ControlPosition.RIGHT_CENTER
                    },
                    streetViewControl: false,
                    scaleControl: false,
                    zoomControl: true,
                    zoomControlOptions: {
                        style: google.maps.ZoomControlStyle.SMALL,
                        position: google.maps.ControlPosition.RIGHT_BOTTOM
                    },
                    minZoom: 2
                };
            }

            function getMapObject(mapOptions, mapCenter) {
                var map = new google.maps.Map(mapCenter, mapOptions);
                return map;
            }

            function getDrawingManagerObject(drawingManagerOptions) {
                var drawingManager = new google.maps.drawing.DrawingManager({
                    drawingMode: null,
                    drawingControl: true,
                    drawingControlOptions: {
                        position: google.maps.ControlPosition.TOP_RIGHT,
                        drawingModes: [
                            google.maps.drawing.OverlayType.CIRCLE,
                        ]
                    },
                    circleOptions: circleOptions,
                    // polygonOptions: polygonOptions
                });
                drawingManager.setMap(map);
                return drawingManager;
            }

            /* -- Overlay Functions Begin Here -- */
            function onOverlayComplete(shape) {
                addDeleteButtonToOverlay(shape);
                addOverlayListeners(shape);
                if (listenerFiltersApplied) {
                    listenerFiltersApplied = false;
                }
                if (shape.type == google.maps.drawing.OverlayType.CIRCLE) {
                    if (selectedShape != null) {
                        selectedShape.setMap(null)
                        $('#deleteOverlayButton').remove();
                    }
                    selectedShape = shape.overlay
                    $('.gmnoprint').css("display", "none")
                }

            }

            function addOverlayListeners(shape) {
                // Filters already applied.
                if (listenerFiltersApplied) {
                    return;
                }
                /*if (shape.type == google.maps.drawing.OverlayType.POLYGON) {
                    setBoundsChangedListener(shape);
                }*/
                if (shape.type == google.maps.drawing.OverlayType.CIRCLE) {
                    setCenterChangedListener(shape);
                    setRadiusChangedListener(shape);
                }
            }

            function setCenterChangedListener(shape) {
                google.maps.event.addListener(shape.overlay, 'center_changed', function () {
                    listenerFiltersApplied = true;
                    onOverlayComplete(shape);
                });
            }

            function setRadiusChangedListener(shape) {
                google.maps.event.addListener(shape.overlay, 'radius_changed', function () {
                    listenerFiltersApplied = true;
                    onOverlayComplete(shape);
                });
            }

            function addDeleteButtonToOverlay(shape) {
                var deleteOverlayButton = new DeleteOverlayButton();
                if (("deleteButton" in shape) && (shape.deleteButton != null)) {
                    shape.deleteButton.div.remove();
                    shape.deleteButton = deleteOverlayButton;
                } else {
                    shape.deleteButton = deleteOverlayButton;
                }
                if (shape.type == google.maps.drawing.OverlayType.CIRCLE) {
                    var radiusInKms = convertDistance(Math.round(shape.overlay.getRadius()), "metres", "kms");
                    $('#info_distance').text(radiusInKms * 1000);
                    $('#info_distance').val(radiusInKms * 1000);

                    var lat = shape.overlay.getCenter().lat();
                    var lng = shape.overlay.getCenter().lng()
                    $('#lat_geofence').val(lat.toFixed(6));
                    $('#lng_geofence').val(lng.toFixed(6));

                    var circleCenter = new google.maps.LatLng(shape.overlay.getCenter().lat(), shape.overlay.getCenter().lng());
                    var deleteOverlayButtonPosition = circleCenter.destinationPoint(30, radiusInKms);
                    deleteOverlayButton.open(map, deleteOverlayButtonPosition, shape);
                } /*else if (shape.type == google.maps.drawing.OverlayType.POLYGON) {
                    deleteOverlayButton.open(map, shape.overlay.getPath().getArray()[0], shape);
                }*/
            }

            /* -- Overlay Functions End Here -- */

            function convertDistance(distanceValue, actualDistanceUnit, expectedDistanceUnit) {
                var distanceInKms = 0;
                switch (actualDistanceUnit) {
                    case "miles":
                        distanceInKms = distanceValue / 0.62137;
                        break;
                    case "kms":
                        distanceInKms = distanceValue;
                        break;
                    case "metres":
                        distanceInKms = distanceValue / 1000;
                        break;
                    default:
                        distanceInKms = undefined;
                }

                switch (expectedDistanceUnit) {
                    case "miles":
                        return distanceInKms * 0.62137;
                    case "kms":
                        return distanceInKms;
                    case "metres":
                        return distanceInKms * 1000;
                    default:
                        return undefined;
                }
            }

            function DeleteOverlayButton() {
                this.div = document.createElement('div');
                this.div.id = 'deleteOverlayButton';
                this.div.className = 'deleteOverlayButton';
                this.div.title = 'Delete';
                this.div.innerHTML = '<span id="x">X</span>';
                var button = this;
                google.maps.event.addDomListener(this.div, 'click', function () {
                    button.removeShape();
                    button.div.remove();
                });
            }

            function initializeDeleteOverlayButtonLibrary() {
                /* This needs to be initialized by initMap() */
                DeleteOverlayButton.prototype = new google.maps.OverlayView();

                /**
                 * Add component to map.
                 */
                DeleteOverlayButton.prototype.onAdd = function () {
                    var deleteOverlayButton = this;
                    var map = this.getMap();
                    this.getPanes().floatPane.appendChild(this.div);
                };

                /**
                 * Clear data.
                 */
                DeleteOverlayButton.prototype.onRemove = function () {
                    google.maps.event.removeListener(this.divListener_);
                    this.div.parentNode.removeChild(this.div);
                    // Clear data
                    this.set('position');
                    this.set('overlay');
                };

                /**
                 * Deletes an overlay.
                 */
                DeleteOverlayButton.prototype.close = function () {
                    this.setMap(null);
                };

                /**
                 * Displays the Button at the position(in degrees) on the circle's circumference.
                 */
                DeleteOverlayButton.prototype.draw = function () {
                    var position = this.get('position');
                    var projection = this.getProjection();
                    if (!position || !projection) {
                        return;
                    }
                    var point = projection.fromLatLngToDivPixel(position);
                    this.div.style.top = point.y + 'px';
                    this.div.style.left = point.x + 'px';
                    /*if (this.get('overlay').type == google.maps.drawing.OverlayType.POLYGON) {
                        this.div.style.marginTop = '-16px';
                        this.div.style.marginLeft = '0px';
                    }*/
                };

                /**
                 * Displays the Button at the position(in degrees) on the circle's circumference.
                 */
                DeleteOverlayButton.prototype.open = function (map, deleteOverlayButtonPosition, overlay) {
                    this.set('position', deleteOverlayButtonPosition);
                    this.set('overlay', overlay);
                    this.setMap(map);
                    this.draw();
                };

                /**
                 * Deletes the shape it is associated with.
                 */
                DeleteOverlayButton.prototype.removeShape = function () {
                    var position = this.get('position');
                    var shape = this.get('overlay');
                    $('.gmnoprint').css("display", "block")
                    $('#info_distance').text(0)
                    $('#info_distance').val(0)

                    $('#lat_geofence').val(0);
                    $('#lng_geofence').val(0);
                    if (shape != null) {
                        shape.overlay.setMap(null);
                        return;
                    }
                    this.close();
                };

                Number.prototype.toRadians = function () {
                    return this * Math.PI / 180;
                }

                Number.prototype.toDegrees = function () {
                    return this * 180 / Math.PI;
                }

                /* Based the on the Latitude/Longitude spherical geodesy formulae & scripts
                   at http://www.movable-type.co.uk/scripts/latlong.html
                */
                google.maps.LatLng.prototype.destinationPoint = function (bearing, distance) {
                    distance = distance / 6371;
                    bearing = bearing.toRadians();
                    var latitude1 = this.lat().toRadians(), longitude1 = this.lng().toRadians();
                    var latitude2 = Math.asin(Math.sin(latitude1) * Math.cos(distance) + Math.cos(latitude1) * Math.sin(distance) * Math.cos(bearing));
                    var longitude2 = longitude1 + Math.atan2(Math.sin(bearing) * Math.sin(distance) * Math.cos(latitude1), Math.cos(distance) - Math.sin(latitude1) * Math.sin(latitude2));
                    if (isNaN(latitude2) || isNaN(longitude2)) return null;
                    return new google.maps.LatLng(latitude2.toDegrees(), longitude2.toDegrees());
                }
            }

            setInitialMapOptions();
            map = getMapObject(mapOptions, this.$('.o_map_geofence_view').get(0));
            this.gmap = map
            drawingManager = getDrawingManagerObject();
            google.maps.event.addListener(drawingManager, 'overlaycomplete', onOverlayComplete);
            /* google.maps.event.addListener(drawingManager, 'drawingmode_changed', function () {
                 if ((drawingManager.getDrawingMode() == google.maps.drawing.OverlayType.CIRCLE) && (selectedShape != null)) {
                     selectedShape.setMap(null);
                     $('#deleteOverlayButton').remove();
                 }

             });*/
            initializeDeleteOverlayButtonLibrary(drawingManager);
        },
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        _onClickBuzzer: function (e) {
            var self = this;
            var $input = $(e.currentTarget);
            console.log($input)
            var body = {}
            var url = 'http://' + url_iot + '/api/commands/send;jsessionid=' + session.jsession_iot
            if ($input.get(0).attributes.name.value == 0) {
                $input.get(0).setAttribute("name", "1");
                $input.removeClass("fa-bell")
                $input.addClass("fa-bell-slash").css('color', 'red');
                body = {
                    "id": 0,
                    "deviceId": $input.get(0).attributes.vehicle.value,
                    "description": "",
                    "type": "engineStop",
                    "attributes": {}
                }
                _sendCommand(self, url, body)
            } else {
                $input.get(0).setAttribute("name", "0");
                $input.addClass("fa-bell").css('color', 'yellow');
                $input.removeClass("fa-bell-slash")
                body = {
                    "id": 0,
                    "deviceId": $input.get(0).attributes.vehicle.value,
                    "description": "",
                    "type": "engineResume",
                    "attributes": {}
                }
                _sendCommand(self, url, body)
            }
            console.log('buzzer');
        },
        _onClickCallOrMessage: function (e) {
            var $input = $(e.currentTarget);
            var deviceId = $input[0].attributes.title.value || 0
            var chat = this._rpc({
                route: '/chat/send_message',
                params: {
                    deviceid: $input[0].attributes.title.value || 0,
                },
            }).then(result => {
                let room_id = result
                var topsss = screen.height - 510;
                var left = screen.width - 400;
                var pop_up = window.open('https://chat.aggregatoricapaci.com/#/room/' + room_id, '_blank', "toolbar=no,scrollbars=no,resizable=no,titlebar=no,top=" + topsss + ",left=" + left + ",width=450,height=400")
                var message_key = window.btoa('' + ';' + session.user_id);
                console.log('_blank', session)
                pop_up.postMessage(JSON.stringify({
                    key: 'token',
                    access_token: session.mx_access_token,
                    user_id: session.user_id,
                    device_id: '',
                    current_language: 'en_US',
                    message_key: message_key,
                    home_server: session.mx_hs_url,
                    routerNavigate: 'home'
                }), "*");
            });
        },
        _onClickCall: function (e) {
            var $input = $(e.currentTarget);
            alert('call');
        },
        _onClickSaveGeoFence: (e) => {
            var enterGeo = 0;
            var exitGeo = 0;
            var self = this;
            var body = {}
            var $input = $(e.currentTarget);
            if ($('#isEnterGeoFence:checkbox:checked').length > 0) {
                enterGeo++;
            }
            if ($('#isExitGeoFence:checkbox:checked').length > 0) {
                exitGeo++;
            }
            console.log(enterGeo, 'xx')
            console.log(exitGeo, 'yy')
            body = {
                "id": 0,
                "deviceId": onChooseVehicleNotClick,
                "description": "string",
                "type": "geoFence",
                "attributes": {
                    "data": $('#selected_box_id').val() + "," + $('#lat_geofence').val() + "," + $('#lng_geofence').val() + "," + $('#info_distance').val() + "," + enterGeo + "," + exitGeo
                }
            }
            var url = 'http://' + url_iot + '/api/commands/send;jsessionid=' + session.jsession_iot;
            _sendCommand(self, url, body)
            $('#mapModal').modal('toggle');
        },
        _onClickEvent: function (e) {
            var self = this;
            var $input = $(e.currentTarget);
            console.log('buzzer');
            var body = {}
            var url = 'http://' + url_iot + '/api/commands/send;jsessionid=' + session.jsession_iot
            switch ($input[0].name) {
                case EVENT_VEHICLE.BUZZER_ON:
                    body = {
                        "id": 0,
                        "deviceId": $input[0].id,
                        "description": "",
                        "type": "engineStop",
                        "attributes": {}
                    }
                    _sendCommand(self, url, body)
                    break;
                case EVENT_VEHICLE.BUZZER_OFF:
                    body = {
                        "id": 0,
                        "deviceId": $input[0].id,
                        "description": "",
                        "type": "engineResume",
                        "attributes": {}
                    }
                    _sendCommand(self, url, body)
                    break;
                case EVENT_VEHICLE.CUSTOM_COMMAND:
                    body = {
                        "id": 0,
                        "deviceId": $input[0].id,
                        "description": "string",
                        "type": "custom",
                        "attributes": {
                            "data": $input[0].value
                        }
                    }
                    _sendCommand(self, url, body)
                    break;
                case EVENT_VEHICLE.DRAW_GEOFENCE:
                    console.log('xxxx')
                    break;
            }
        },
        _onClickVehicle: function (e) {
            var self = this;
            window.isClickVehicle = true //set is click hidden cluser

            /* handler css*/
            $('ul.navbar-nav > li').removeClass('active');
            $(e.currentTarget.parentElement).addClass('active');
            var $input = $(e.currentTarget);
            onChooseVehicle = $input[0].attributes.id.value || 0
            var vehicleId = $input[0].attributes.id.value || 0
            $('.o_map_vehicle_info').remove()
            $('.topInfoVehicle').remove()
            $('.o_map_left_sidebar ').css({'overflow-x': 'unset'})
            $('.o_map_devices').css({'height': '50%', 'overflow': 'auto'})
            $('<div style="background:#5fa2dd" class="topInfoVehicle"><div class="p-2"><span style="color:white;font-size:17px">State</span></div></div>').insertAfter('.o_map_devices')
            $('.detailsDevice').css({'height': 'calc(44% - 3em)', 'overflow': 'auto'})
            $('.detailsDevice').show();
            $('#report_container').empty()
            $('#right_sidebar_report').css("display", "block")
            var positions = [];
            console.log(session)
            positions.push({
                accuracy: 0,
                address: 0,
                altitude: 0,
                course: 0,
                deviceid: 0,
                devicetime: 0,
                latitude: 0,
                longitude: 0,
                network: 0,
                speed: 0,
            })
            var vehicleDetails = new SidebarLeftVehicle(this, {
                'position': positions,
            });
            vehicleDetails.appendTo('.detailsDevice')
            rpc.query({
                model: 'fleet.vehicle',
                method: 'search_read',
                args: [[['id', '=', vehicleId]]],
            }).then((device) => {
                mapCenter.panTo({lat: device[0].latitude, lng: device[0].longitude});
                mapCenter.setZoom(18)
                mapCenter.setOptions({maxZoom: 20});
                $('#capacity_available').text(parseFloat(device[0].available_capacity).toFixed(2) + ' ' + session.weight_unit)
                $('#address').text(device[0].latitude + ' - ' + device[0].longitude)
                rpc.query({
                    model: 'tc.positions',
                    method: 'search_read',
                    args: [[['id', '=', device[0].positionid]]],
                }).then((position) => {
                    if (position.length > 0) {
                        $('#address').text(position[0].latitude + ' - ' + position[0].longitude)
                        $('#altitude').text(position[0].altitude)
                        $('#course').text(position[0].course)
                        $('#deviceTime').text(position[0].deviceTime)
                        // $('#latitude').text(position[0].latitude)
                        // $('#longitude').text(position[0].longitude)
                        // $('#deviceID').text(position[0].deviceid)
                        $('#speed').text(position[0].speed)
                    }
                })
            })

            /* draw routing today */
            if (this.directionsDisplay != null) {
                this.directionsDisplay.setMap(null);
                this.directionsDisplay = null;
            }

            let current_datetime = new Date()
            let formatted_date = current_datetime.getFullYear() + "-" + self._appendLeadingZeroes(current_datetime.getMonth() + 1) + "-" + self._appendLeadingZeroes(current_datetime.getDate())

            //TODO : test thu draw 2 lần 23 point
            session.rpc('/routing_plan_day/get_driver_routing_plan_by_vehicle', {
                vehicle_id: vehicleId,
                date_plan: formatted_date,
                type: 1
            }).then((routing_day) => {
                console.log(routing_day)
                if (window.gRenderers) {
                    window.gRenderers.forEach((render) => {
                        render.setMap(null)
                        render = null
                    })
                    window.dMarker.forEach((marker) => {
                        marker.setMap(null)
                    })
                }
                if (routing_day.records.length > 0) {
                    var ways = [];
                    routing_day.records.forEach((routing) => {
                        ways.push({
                            lat: routing.latitude,
                            lng: routing.longitude,
                            order_n: routing.order_number_routing,
                            address: routing.address,
                            name: routing.warehouse_name,
                            phone: routing.phone,
                            stopover: true
                        })
                    })
                    var waypts = this._removeDuplicate(ways, rpd => rpd.name);
                    this.directionsService = new google.maps.DirectionsService();
                    var lngs = waypts.map(function (place) {
                        return place.lng;
                    });
                    var lats = waypts.map(function (place) {
                        return place.lat;
                    });
                    mapCenter.fitBounds({
                        west: Math.min.apply(null, lngs),
                        east: Math.max.apply(null, lngs),
                        north: Math.min.apply(null, lats),
                        south: Math.max.apply(null, lats),
                    });

                    for (var i = 0; i < waypts.length; i++) {
                        var dmarker;
                        var order_number = 0;
                        if (waypts[i].order_n) {
                            order_number = waypts[i].order_n.split(",").sort(function (a, b) {
                                return a - b
                            })
                        } // sort array
                        var infoWindow = new google.maps.InfoWindow();
                        // draw marker start - end routing
                        if (order_number.includes("1")) {
                            dmarker = new google.maps.Marker({
                                position: waypts[i],
                                map: mapCenter,
                                title: waypts[i].name + '<br>' + waypts[i].address + '<br>' + waypts[i].phone,
                                /*label: {
                                    color: 'black',
                                    fontWeight: 'bold',
                                    text: order_number.toString(),
                                },*/
                                icon: {
                                    url: '/web_google_maps/static/src/img/markers/start.png',
                                    labelOrigin: new google.maps.Point(16, 20)
                                }
                            });
                        } else if (order_number.includes(ways.length.toString())) {
                            dmarker = new google.maps.Marker({
                                position: waypts[i],
                                map: mapCenter,
                                title: waypts[i].name + '<br>' + waypts[i].address + '<br>' + waypts[i].phone,
                                icon: {
                                    url: '/web_google_maps/static/src/img/markers/finish-line.png',
                                    labelOrigin: new google.maps.Point(16, 20)
                                }
                            });
                        } else {
                            dmarker = new google.maps.Marker({
                                position: waypts[i],
                                map: mapCenter,
                                title: waypts[i].name + '<br>' + waypts[i].address + '<br>' + waypts[i].phone,
                                icon: {
                                    url: '/web_google_maps/static/src/img/markers/warehouse.png',
                                    labelOrigin: new google.maps.Point(16, 20)
                                }
                            });
                        }
                        if (!window.dMarker)
                            window.dMarker = [];
                        window.dMarker.push(dmarker);

                        google.maps.event.addListener(dmarker, "click", function (evt) {
                            infoWindow.setContent(this.get('title'));
                            infoWindow.open(mapCenter, this);
                        });
                    }
                    // Divide route to several parts because max waypts limit is 25 (23 waypoints + 1 origin + 1 destination)
                    for (var i = 0, parts = [], max = 25 - 1; i < waypts.length; i = i + max)
                        parts.push(waypts.slice(i, i + max + 1));

                    var service_callback = function (response, status) {
                        if (status != 'OK') {
                            console.log('Directions request failed due to ' + status);
                            return;
                        }

                        var renderer = new google.maps.DirectionsRenderer;

                        if (!window.gRenderers)
                            window.gRenderers = [];
                        window.gRenderers.push(renderer);
                        renderer.setMap(mapCenter);
                        renderer.setOptions({suppressMarkers: true, preserveViewport: true});
                        renderer.setDirections(response);
                    };
                    // Send requests to service to get route (for waypts count <= 25 only one request will be sent)
                    for (var i = 0; i < parts.length; i++) {
                        // Waypoints does not include first station (origin) and last station (destination)
                        var waypoints = [];
                        for (var j = 1; j < parts[i].length - 1; j++)
                            waypoints.push({location: parts[i][j], stopover: true});
                        // Service options

                        var service_options = {
                            origin: parts[i][0],
                            destination: parts[i][parts[i].length - 1],
                            waypoints: waypoints,
                            travelMode: 'DRIVING'
                        };
                        // Send request
                        this.directionsService.route(service_options, service_callback);
                    }
                    var sidebar_right = new SidebarFilterRight(this, {
                        'filters': routing_day.records,
                        'waypts': waypts
                    });
                    var reportContainer = $('#report_container');
                    sidebar_right.appendTo(reportContainer)

                }
            })
            mapClearMarker.markers.forEach(function (marker) {
                if (marker._odooRecord.data.id != onChooseVehicle) {
                    marker.setVisible(false);
                } else {
                    marker.setVisible(true);
                }
            });
        }
        , _appendLeadingZeroes: function (n) {
            if (n <= 9) {
                return "0" + n;
            }
            return n
        },
        _removeDuplicate: function (data, key) {
            return [...new Map(data.map(x => [key(x), x])).values()]
        },
    });

    var SidebarFilterRight = Widget.extend(FieldManagerMixin, {
        template: 'MapView.sidebar.right',
        init: function (parent, options) {
            this._super.apply(this, arguments);
            FieldManagerMixin.init.call(this);
            this.filters = options.filters;
            let output = []
            for (let i = 0; i < this.filters.length; i++) {
                if (!output[output.length - 1] || output[output.length - 1].value.warehouse_name
                    != this.filters[i].warehouse_name)
                    output.push({value: this.filters[i], warehouse: [this.filters[i]]})
                else
                    output[output.length - 1].warehouse.push(this.filters[i])
                // output[output.length - 1].order_number++;
            }
            console.log(output)
            //lst warehouse today
            this.wareHouses = output
        },
        /**
         * @override
         */
        willStart: function () {
            var self = this;
            var defs = [this._super.apply(this, arguments)];
            return Promise.all(defs);
        },
        /**
         * @override
         */
        start: function () {
            this._super();
            if (this.many2one) {
                this.many2one.appendTo(this.$el);
                this.many2one.filter_ids = _.without(_.pluck(this.filters, 'value'), 'all');
            }
            this.$el.on('click', '.hover_show_position', this._onClickShowPositionRouting.bind(this));
            this.$el.on('click', '.hover_show_chat', this._onClickShowChat.bind(this));
        },
        _onClickShowPositionRouting: function (e) {
            var self = this;
            var $input = $(e.currentTarget);
            var lat = $input.get(0).attributes.lat.value
            var lng = $input.get(0).attributes.lng.value
            mapCenter.panTo({lat: parseFloat(lat), lng: parseFloat(lng)});
            mapCenter.setZoom(18)
            mapCenter.setOptions({maxZoom: 20});

        },
        _onClickShowChat: function (e) {
            var self = this;
            var $input = $(e.currentTarget);
            var cus = $input.get(0).attributes.cus.value
            console.log(cus, '1231231')
            var chat = this._rpc({
                route: '/chat/send_message_partner',
                params: {
                    phone: cus
                },
            }).then(result => {
                let room_id = result
                var topsss = screen.height - 510;
                var left = screen.width - 400;
                var pop_up = window.open('https://chat.aggregatoricapaci.com/#/room/' + room_id, '_blank', "toolbar=no,scrollbars=no,resizable=no,titlebar=no,top=" + topsss + ",left=" + left + ",width=450,height=400")
                var message_key = window.btoa('' + ';' + session.user_id);
                console.log('_blank', session)
                pop_up.postMessage(JSON.stringify({
                    key: 'token',
                    access_token: session.mx_access_token,
                    user_id: session.user_id,
                    device_id: '',
                    current_language: 'en_US',
                    message_key: message_key,
                    home_server: session.mx_hs_url,
                    routerNavigate: 'home'
                }), "*");
            });

        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
    });

    var SidebarLeftVehicle = Widget.extend(FieldManagerMixin, {
        template: 'MapView.Vehicle_info',

        init: function (parent, options) {
            this._super.apply(this, arguments);
            FieldManagerMixin.init.call(this);
            this.position = options.position
        },
        /**
         * @override
         */
        willStart: function () {
            var self = this;
            var defs = [this._super.apply(this, arguments)];
            return Promise.all(defs);
        },
        /**
         * @override
         */
        start: function () {
            this._super();
        }
    });

    var SidebarFilter = Widget.extend(FieldManagerMixin, {
        template: 'MapView.sidebar.filter',
        custom_events: _.extend({}, FieldManagerMixin.custom_events, {
            field_changed: '_onFieldChanged',
        }),
        /**
         * @constructor
         * @param {Widget} parent
         * @param {Object} options
         * @param {string} options.fieldName
         * @param {Object[]} options.filters A filter is an object with the
         *   following keys: id, value, label, active, avatar_model, color,
         *   can_be_removed
         * @param {Object} [options.favorite] this is an object with the following
         *   keys: fieldName, model, fieldModel
         */
        init: function (parent, options) {
            this._super.apply(this, arguments);
            FieldManagerMixin.init.call(this);

            this.title = options.title;
            this.fields = options.fields;
            this.fieldName = options.fieldName;
            this.write_model = options.write_model;
            this.write_field = options.write_field;
            this.avatar_field = options.avatar_field;
            this.avatar_model = options.avatar_model;
            this.filters = options.filters;
            this.label = options.label;
            this.getColor = options.getColor;
            this.isSwipeEnabled = true;
            this.selected = options.selected;
        },
        /**
         * @override
         */
        willStart: function () {
            var self = this;
            var defs = [this._super.apply(this, arguments)];

            if (this.write_model || this.write_field) {
                var def = this.model.makeRecord(this.write_model, [{
                    name: this.write_field,
                    relation: this.fields[this.fieldName].relation,
                    type: 'many2one',
                }]).then(function (recordID) {
                    self.many2one = new SidebarFilterM2O(self,
                        self.write_field,
                        self.model.get(recordID),
                        {
                            mode: 'edit',
                            attrs: {
                                placeholder: "+ " + _.str.sprintf(_t("Add %s"), self.title),
                                can_create: false
                            },
                        });
                });
                defs.push(def);
            }
            return Promise.all(defs);

        },
        /**
         * @override
         */
        start: function () {
            this._super();
            if (this.many2one) {
                this.many2one.appendTo(this.$el);
                this.many2one.filter_ids = _.without(_.pluck(this.filters, 'value'), 'all');
            }
            this.$el.on('click', '.o_remove', this._onFilterRemove.bind(this));
            this.$el.on('click', '.o_map_filter_items input', this._onFilterActive.bind(this));
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {OdooEvent} event
         */
        _onFieldChanged: function (event) {
            var self = this;
            event.stopPropagation();
            var createValues = {'user_id': session.uid};
            var value = event.data.changes[this.write_field].id;
            createValues[this.write_field] = value;
            this._rpc({
                model: this.write_model,
                method: 'create',
                args: [createValues],
            })
                .then(function () {
                    self.trigger_up('changeFilter', {
                        'fieldName': self.fieldName,
                        'value': value,
                        'active': true,
                    });
                });
        },
        /**
         * @private
         * @param {MouseEvent} e
         */
        _onFilterActive: function (e) {
            var $input = $(e.currentTarget);
            var checked = $input.prop('checked');
            var title = $input[0].nextElementSibling.children[2].title;

            // console.log('_onFilterActive', $input);
            this.trigger_up('changeFilter', {
                'fieldName': self.fieldName,
                'value': title,
                'active': checked,
            });
            $(".o_map_filter_left").remove();
        },
        /**
         * @private
         * @param {MouseEvent} e
         */
        _onFilterRemove: function (e) {
            var self = this;
            var $filter = $(e.currentTarget).closest('.o_map_filter_item');
            // console.log('_onFilterRemove', $filter);
            Dialog.confirm(this, _t("Do you really want to delete this filter from favorites ?"), {
                confirm_callback: function () {
                    self._rpc({
                        model: self.write_model,
                        method: 'unlink',
                        args: [[$filter.data('id')]],
                    })
                        .then(function () {
                            self.trigger_up('changeFilter', {
                                'fieldName': self.fieldName,
                                'id': $filter.data('id'),
                                'active': false,
                                'value': $filter.data('value'),
                            });
                        });
                },
            });
        },
        getAvatars: function (record, fieldName, imageField) {
            var field = this.state.fields[fieldName];
            if (!record[fieldName]) {
                return [];
            }
            if (field.type === 'one2many' || field.type === 'many2many') {
                return _.map(record[fieldName], function (id) {
                    return '<img src="/web/image/' + field.relation + '/' + id + '/' + imageField + '" />';
                });
            } else if (field.type === 'many2one') {
                return ['<img src="/web/image/' + field.relation + '/' + record[fieldName][0] + '/' + imageField + '" />'];
            } else {
                var value = this._format(record, fieldName);
                var color = this.getColor(value);
                if (isNaN(color)) {
                    return ['<span class="o_avatar_square" style="background-color:' + color + ';"/>'];
                } else {
                    return ['<span class="o_avatar_square o_map_color_' + color + '"/>'];
                }
            }
        },

        _format: function (record, fieldName) {
            var field = this.state.fields[fieldName];
            if (field.type === "one2many" || field.type === "many2many") {
                return field_utils.format[field.type]({data: record[fieldName]}, field);
            } else {
                return field_utils.format[field.type](record[fieldName], field, {forceString: true});
            }
        },
        _renderFilters: function () {
            // Dispose of filter popover
            this.$('.o_map_filter_item').popover('dispose');
            _.each(this.filters || (this.filters = []), function (filter) {
                filter.destroy();
            });
            if (this.state.fullWidth) {
                return;
            }
            return this._renderFiltersOneByOne();
        },
        _renderFiltersOneByOne: function (filterIndex) {
            filterIndex = filterIndex || 0;
            var arrFilters = _.toArray(this.state.filters);
            var prom;
            if (filterIndex < arrFilters.length) {
                var options = arrFilters[filterIndex];
                if (!_.find(options.filters, function (f) {
                    return f.display == null || f.display;
                })) {
                    return this._renderFiltersOneByOne(filterIndex + 1);
                }

                var self = this;
                options.getColor = this.getColor.bind(this);
                options.fields = this.state.fields;
                var filter = new SidebarFilter(self, options);
                prom = filter.appendTo(this.$right_sidebar).then(function () {
                    // Show filter popover
                    if (options.avatar_field) {
                        _.each(options.filters, function (filter) {
                            if (filter.value !== 'all') {
                                var selector = _.str.sprintf('.o_map_filter_item[data-value=%s]', filter.value);
                                this.$right_sidebar.find(selector).popover({
                                    animation: false,
                                    trigger: 'hover',
                                    html: true,
                                    placement: 'top',
                                    title: filter.label,
                                    delay: {show: 300, hide: 0},
                                    content: function () {
                                        return $('<img>', {
                                            src: _.str.sprintf('/web/image/%s/%s/%s', options.avatar_model, filter.value, options.avatar_field),
                                            class: 'mx-auto',
                                        });
                                    },
                                });
                            }
                        });
                    }
                    return self._renderFiltersOneByOne(filterIndex + 1);
                });
                this.filters.push(filter);
            }
            return Promise.resolve(prom);
        },
        /**
         * Note: this is not dead code, it is called by two template
         *
         * @param {any} key
         * @returns {integer}
         */
        getColour: function (key) {
            if (!key) {
                return;
            }
            if (this.color_map[key]) {
                return this.color_map[key];
            }
            // check if the key is a css color
            if (typeof key === 'string' && key.match(/^((#[A-F0-9]{3})|(#[A-F0-9]{6})|((hsl|rgb)a?\(\s*(?:(\s*\d{1,3}%?\s*),?){3}(\s*,[0-9.]{1,4})?\))|)$/i)) {
                return this.color_map[key] = key;
            }
            var index = (((_.keys(this.color_map).length + 1) * 5) % 24) + 1;
            this.color_map[key] = index;
            return index;
        },
    });

    return MapRenderer;

});