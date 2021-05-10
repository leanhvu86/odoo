odoo.define('web_google_maps.RouteRenderer', function (require) {
    'use strict';

    var BasicRenderer = require('web.BasicRenderer');
    var core = require('web.core');
    var QWeb = require('web.QWeb');
    var session = require('web.session');
    var utils = require('web.utils');
    var Widget = require('web.Widget');
    var KanbanRecord = require('web.KanbanRecord');
    var mapCenter; //map current
    var qweb = core.qweb;
    var map;
    var MARKER_COLORS = [
        'green', 'yellow', 'blue', 'light-green',
        'red', 'magenta'
//        , 'black', 'purple', 'orange',
//        'pink', 'grey', 'brown', 'cyan', 'white'
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
    var polylines = [];
    var allCoordinates = [];

    var MapRecord = KanbanRecord.extend({
        init: function (parent, state, options) {
            this._super.apply(this, arguments);
            this.fieldsInfo = state.fieldsInfo.route;
            console.log('MapRecord', state.fieldsInfo);
            console.log('MapRecord', this.fieldsInfo);
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

    var RouteRenderer = BasicRenderer.extend({
        className: 'o_chat_view',
        template: 'ChatView.ChatView',
        /**
         * @override
         */
        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            this.mapLibrary = params.mapLibrary;
//            this.modelInput = params.model;
//            console.log(this.modelInput)
            this.widgets = [];
            this.mapThemes = MAP_THEMES;
            console.log('render initial');
            console.log('render initial _param', params);
            console.log('render initial state', state);

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
        },
        _initLibraryProperties: function (params) {
            if (this.mapLibrary === 'drawing') {
                this.drawingMode = params.drawingMode || 'shape_type';
                this.drawingPath = params.drawingPath || 'shape_paths';
                this.shapesLatLng = [];
            } else if (this.mapLibrary === 'geometry') {
                this.defaultMarkerColor = 'red';
                this.markerGroupedInfo = [];
                this.markers = [];
//                if(this.modelInput!==undefined){
//                    this.iconUrl = '/web_google_maps/static/src/img/markers/'+this.modelInput+'/';
//                }else{
                this.iconUrl = '/web_google_maps/static/src/img/markers/';
//                }
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
            console.log("render Update state App", state);
//            tạm thời stop update state của view khi dùng route- với map ok với route thì tèo
            this._setState(state);
            var checkStatus = false;
            for (let check of state.domain) {
                if (check[0] === 'status') {
                    checkStatus = true;
                    console.log('state.domain', check[0])
                }
            }
            if (checkStatus === true) {
                this.directionsDisplay.setMap();
            } else {
                this.directionsDisplay.setMap(this.gmap);
                this.display_result();
            }
            return this._super.apply(this, arguments);
        },
        /**
         * @override
         */
        start: function () {
            console.log("render Initial App");
            this._initMap();
            return this._super();
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
            this.$('.o_chat_view').empty();
            this.gmap = new google.maps.Map(this.$('.o_chat_view').get(0), {
                mapTypeId: "terrain",
                minZoom: 3,
                maxZoom: 20,
                fullscreenControl: true,
                mapTypeControl: true
            });
            mapCenter = this.gmap
            this._getMapTheme();
            if (this.mapLibrary === 'geometry') {
                this._initMarkerCluster();
            }
            this.$right_sidebar = this.$('.o_map_right_sidebar');
            this.directionsService = new google.maps.DirectionsService();
            this.directionsDisplay = new google.maps.DirectionsRenderer({
                map: this.gmap,
                preserveViewport: true,
                draggable: false
//ẩn các marker của direction service
                , suppressMarkers: true
            });
            // draggable để k chọn được tuyến, suppress markers: để ẩn marker đi
            this.directionsDisplay.setMap(this.gmap);
        },
        _initMarkerCluster: function () {
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
//          set icon tren ban do
            if (color) {
                options.icon = this.iconUrl + color.trim() + '.png';
            }
            var marker = new google.maps.Marker(options);
            this.markers.push(marker);
            this._clusterAddMarker(marker);
        },
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
        },
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

            if (currentRecords.length > 0) {
                currentRecords.forEach(function (_record) {
                    _content = self._generateMarkerInfoWindow(_record);
                    markerRecords.push(_content);
                    _content.appendTo(markerContent);
                });
            }

            var markerIwContent = this._generateMarkerInfoWindow(marker._odooRecord);

            markerIwContent.appendTo(markerContent);
            console.log('markerContent', markerContent);
            console.log('markerIwContent', markerIwContent);

            markerDiv.appendChild(markerContent);
            this.infoWindow.setContent(markerDiv);
            this.infoWindow.open(this.gmap, marker);
        },
        /* _shapeInfoWindow: function (record, event) {
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
         },*/
        /**
         * @private
         */
        _generateMarkerInfoWindow: function (record) {
            console.log('_generateMarkerInfoWindow', record);
            var markerIw = new MapRecord(this, record, this.recordOptions);
            return markerIw;
        },
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
        },
        /**
         * Default location
         */
        _getDefaultCoordinate: function () {
            return new google.maps.LatLng(0.0, 0.0);
        },
        _renderGrouped: function () {
            var self = this;
            var defaultLatLng = this._getDefaultCoordinate();
            var color, latLng, lat, lng;
            console.log('render Group data', this.state.data);
            _.each(this.state.data, function (record) {
                color = self._getGroupedMarkerColor();
                record.markerColor = color;
                _.each(record.data, function (rec) {
                    lat = rec.data['latitude'] || 0.0;
                    lng = rec.data['longitude'] || 0.0;
                    if (lat === 0.0 && lng === 0.0) {
                        self._createMarker(defaultLatLng, rec, color);
                    } else {
                        latLng = new google.maps.LatLng(lat, lng);
                        self._createMarker(latLng, rec, color);
                    }
                });
                self.markerGroupedInfo.push({
                    'title': record.value || 'Undefined',
                    'count': record.count,
                    'marker': self.iconUrl + record.markerColor.trim() + '.png'
                });
            });
            if (this.state.data.length === 0) {
                this.directionsDisplay.setMap();
            }
        },
        _renderUngrouped: function () {
            var self = this;
            var defaultLatLng = this._getDefaultCoordinate();
            var color, latLng, lat, lng;

            for (let i = 0; i < this.state.data.length; i++) {
                let record = this.state.data[i];
                color = self._getIconColor(record);
                console.log(color)
                lat = record.data['latitude'] || 0.0;
                lng = record.data['longitude'] || 0.0;
                if (lat === 0.0 && lng === 0.0) {
                    self._createMarker(defaultLatLng, record, color);
                } else {
                    if (i === 0 || i === this.state.data.length - 1 || record.data.status === '0') {
                        console.log('render UnGroup data', i);
                        latLng = new google.maps.LatLng(lat, lng);
                        record.markerColor = color;
                        self._createMarker(latLng, record, color);
                    }
                }
            }
            ;
            if (this.state.data.length === 0) {
                this.directionsDisplay.setMap();
            }
//            this.display_result();
        },
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
        },
        /*   _drawPolygon: function (record) {
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
           },*/
        /*      _drawCircle: function (record) {
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
              },*/
        /**
         * Draw rectangle
         * @param {Object} record
         */
        /*   _drawRectangle: function (record) {
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
           },*/
        /**
         * Draw shape into the map
         */
        /*    _renderShapes: function () {
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
            },*/
        /**
         * @private
         * @param {Array} ShapesToKeep contains list of id
         * Remove shapes from the maps without deleting the shape
         * will keep those shapes in cache
         */
        /*   _cleanShapesInCache: function (shapesToKeep) {
               _.each(this.shapesCache, function (shape, id) {
                   if (shapesToKeep.indexOf(id) === -1) {
                       shape.setMap(null);
                   }
               });
           },*/
        /**
         * @override
         */
        _renderView: function () {
            var self = this;
//            if (this.mapLibrary === 'geometry') {
            console.log('render view');
            this.display_result();
            this.markerGroupedInfo.length = 0;
            this._clearMarkerClusters();
            this._renderMarkers();
            this._clusterMarkers();
            return this._super.apply(this, arguments)
                .then(self._renderSidebarGroup.bind(self))
                .then(self.mapGeometryCentered.bind(self));
//            }
//            else if (this.mapLibrary === 'drawing') {
//                this.shapesLatLng.length = 0;
//                this._renderShapes();
//                return this._super.apply(this, arguments).then(this.mapShapesCentered.bind(this));
//            }
//            return this._super.apply(this, arguments);
        },


        display_result: function () {
            if (this.updating) {
                return;
            }
            var self = this;
            var wayPointArray = [];
            this.polylines = [];
            if (this.state.data === undefined || this.state.data.length === 0) return;
            var from_lat = this.state.data[0].data.latitude;
            var from_lng = this.state.data[0].data.longitude;
            var to_lat = this.state.data[this.state.data.length - 1].data.latitude;
            var to_lng = this.state.data[this.state.data.length - 1].data.longitude;

            if (from_lat === 0 | from_lng === 0 | to_lat === 0 | to_lng === 0) {
                return;
            }
            var from_Latlng = new google.maps.LatLng(from_lat, from_lng);
            var to_Latlng = new google.maps.LatLng(to_lat, to_lng);
            if (this.state.data.length > 2) {
                for (let i = 1; i < this.state.data.length - 1; i++) {
                    wayPointArray.push({
//                         location: Latlng,
                        lat: this.state.data[i].data.latitude,
                        lng: this.state.data[i].data.longitude,
                    });
                }
            }


            var request;
            var mapOptions = {
                zoom: 8,
                center: from_Latlng
            };

            console.log('wayPointArray', wayPointArray);

            const flightPath = new google.maps.Polyline({
                path: wayPointArray,
                geodesic: true,
                strokeColor: "#FF0000",
                strokeOpacity: 1.0,
                strokeWeight: 2,
            });
            flightPath.setMap(mapCenter);
//             if (wayPointArray !== undefined && wayPointArray.length > 0) {
//                 var lngs = wayPointArray.map(function (station) {
//                     return station.lng;
//                 });
//                 var lats = wayPointArray.map(function (station) {
//                     return station.lat;
//                 });
//                 mapCenter.fitBounds({
//                     west: Math.min.apply(null, lngs),
//                     east: Math.max.apply(null, lngs),
//                     north: Math.min.apply(null, lats),
//                     south: Math.max.apply(null, lats),
//                 });
//                 for (var i = 0; i < wayPointArray.length; i++) {
//                     new google.maps.Marker({
//                         position: wayPointArray[i],
//                         map: mapCenter,
//                         title: wayPointArray[i].name
//                     });
//                 }
//                 var service_callback = function (response, status) {
//                     if (status != 'OK') {
//                         console.log('Directions request failed due to ' + status);
//                         return;
//                     }
//                     var renderer = new google.maps.DirectionsRenderer;
//                     if (!window.gRenderers)
//                         window.gRenderers = [];
//                     window.gRenderers.push(renderer);
//                     renderer.setMap(mapCenter);
//                     renderer.setOptions({suppressMarkers: true, preserveViewport: true});
//                     renderer.setDirections(response);
//                     /* this.setMap(mapCenter);
//                      this.setOptions({suppressMarkers: false, preserveViewport: true});
//                      this.setDirections(response);*/
//                 };
//
//                 // Divide route to several parts because max waypts limit is 25 (23 waypoints + 1 origin + 1 destination)
//                 for (var i = 0, parts = [], max = 25 - 1; i < wayPointArray.length; i = i + max) {
//                     parts.push(wayPointArray.slice(i, i + max + 1));
//
//                 }
//                 // Send requests to service to get route (for waypts count <= 25 only one request will be sent)
//                 for (var i = 0; i < parts.length; i++) {
//                     // Waypoints does not include first station (origin) and last station (destination)
//                     var waypoints = [];
//                     for (var j = 1; j < parts[i].length - 1; j++)
//                         waypoints.push({location: parts[i][j], stopover: false});
//                     // Service options
//                     var service_options = {
//                         origin: parts[i][0],
//                         destination: parts[i][parts[i].length - 1],
//                         waypoints: waypoints,
//                         travelMode: 'WALKING'
//                     };
//                     // Send request
//                     this.directionsService.route(service_options, service_callback);
//                 }
//
// //                request = {
// //                origin: from_Latlng,
// //                destination: to_Latlng,
// //                waypoints: wayPointArray,
// //                travelMode: google.maps.TravelMode.DRIVING
// //                };
//             } else {
//                 request = {
//                     origin: from_Latlng,
//                     destination: to_Latlng,
//                     travelMode: google.maps.TravelMode.DRIVING
//                 };
//             }
// //            self.directionsService.route(request, function (response, status) {
// //                console.log("Res",response);
// //                if (status == google.maps.DirectionsStatus.OK) {
// //                    self.directionsDisplay.setDirections(response);
// //                     // combine the bounds of the responses
// //                    self.computeTotal(response);
// //                    self.mapGeometryCentered.bind(self);
// //                }else{
// //                    alert('ROUTE HAS NO RESULTS OR DONE ALREADY')
// //                }
// //                console.log('response',response);
// //            });
            google.maps.event.trigger(this.gmap, 'resize');
        },


        computeTotal: function (result) {
            var self = this;
            var distance = 0;
            var duration = 0;
            var route = result.routes[0];
            this.gmap.fitBounds(result.routes[0].bounds);
            polylines.forEach(polyline => {
                polyline.setMap(null);
            })
            for (var i = 0; i < route.legs.length; i++) {
                distance += route.legs[i].distance.value;
                duration += route.legs[i].duration.value;

                var min = 0;
                min = route.legs[i].steps[0].distance;
                var index = 0;
                // check index có distance min để vẽ polyline trùng với route
                for (var j = 1; j < route.legs[i].steps.length - 1; j++) {
                    if (route.legs[i].steps[j].distance < min) {
                        index = j;
                        min = route.legs[i].steps[j].distance;
                    }
                }
                var coordinates = new Array();
                coordinates.push(route.legs[i].steps[index].start_location)
                coordinates.push(route.legs[i].steps[index].end_location)
                var polyline = new google.maps.Polyline({
                    path: coordinates,
                    strokeColor: '#FF0000',
                    strokeOpacity: 0.5,
                    strokeWeight: 3,
                    geodesic: true,
                    icons: [{repeat: '50px', icon: {path: google.maps.SymbolPath.FORWARD_OPEN_ARROW}}]
                });
                polyline.setMap(this.gmap);
                polylines.push(polyline);
            }
            distance = distance / 1000.0;
            duration = duration / 60 / 60;
//            var title = document.getElementById('title').innerHtml = "<a>"+'Tổng số' + distance +' km'+"</a>";
            console.log('checking route', distance + ' km ', duration + ' hour');
        },

        /**
         * Cluster markers
         * @private
         */
        _clusterMarkers: function () {
            this.markerCluster.addMarkers(this.markers);
        },
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
        },
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
        },
        /**
         * Clear marker clusterer and list markers
         * @private
         */
        _clearMarkerClusters: function () {
            this.markerCluster.clearMarkers();
            this.markers = [];
        },
        /**
         * Render a sidebar for grouped markers info
         * @private
         */
        _renderSidebarGroup: function () {
            if (this.markerGroupedInfo.length > 0) {
                this.$right_sidebar.empty().removeClass('closed').addClass('open');
                var groupInfo = new SidebarGroup(this, {
                    'groups': this.markerGroupedInfo
                });
                groupInfo.appendTo(this.$right_sidebar);
            } else {
                this.$right_sidebar.empty();
                if (!this.$right_sidebar.hasClass('closed')) {
                    this.$right_sidebar.removeClass('open').addClass('closed');
                }
            }
        },
        /**
         * Sets the current state and updates some internal attributes accordingly.
         *
         * @private
         * @param {Object} state
         */
        _setState: function (state) {
            this.state = state;
            console.log('setState', state);
            if (state.groupedBy.length > 0) {
                var groupByFieldAttrs = state.fields[state.groupedBy[0]];
                var groupByFieldInfo = state.fieldsInfo.route[state.groupedBy[0]];
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
        },
    });

    return RouteRenderer;

});