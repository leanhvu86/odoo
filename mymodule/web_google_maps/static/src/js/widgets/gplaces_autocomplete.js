odoo.define('web_google_maps.GplaceAutocompleteFields', function (require) {
    'use strict';

    var BasicFields = require('web.basic_fields');
    var core = require('web.core');
    var QWeb = core.qweb;
    var _t = core._t;
    var _lt = core._lt;
    var Widget = require('web.Widget');
    var FormView = require('web.FormView');

    var view_registry = require('web.view_registry');
    var registry = require('web.field_registry');
    var widgetRegistry = require('web.widget_registry');
    var utils = require('web.utils');
    var BasicView = require('web.BasicView');
    var BasicController = require('web.BasicController');
    var BasicRenderer = require('web.BasicRenderer');

    var AbstractView = require('web.AbstractView');
    var AbstractModel = require('web.AbstractModel');
    var AbstractController = require('web.AbstractController');
    var AbstractRenderer = require('web.AbstractRenderer');
    var session = require('web.session');
    var ajax = require('web.ajax');

    var map;
    var key;
    var odoo_markers = [];
    var GMapRoute;
    var GMapMarker;
    var GMaps;
    var marker;
    var mapCenter;
    var GMapsModel;
    var GMapsController;
    var GMapsRenderer;

    var Utils = require('web_google_maps.Utils');
    var _t = core._t;
    var latitude_field;
    var longitude_field;
    var old_latitude_field;
    var old_longitude_field;
    var GplaceAutocomplete = BasicFields.InputField.extend({
        tagName: 'span',
        supportedFieldTypes: ['char'],
        /**
         * @override
         */
        init: function () {
            this._super.apply(this, arguments);
            this.places_autocomplete = false;
            this.component_form = Utils.GOOGLE_PLACES_COMPONENT_FORM;
            this.address_form = Utils.ADDRESS_FORM;
            this.fillfields_delimiter = {
                street: " ",
                street2: ", ",
            };
            this.fillfields = {};
            this.lng = true;
            this.lat = true;
            this.autocomplete_settings = null;
        },
        willStart: function () {
            var self = this;
            this.setDefault();
            var getSettings = this._rpc({
                route: '/web/google_autocomplete_conf'
            }).then(function (res) {
                self.autocomplete_settings = res;
            });
            return $.when(this._super.apply(this, arguments), getSettings);
        },
        /**
         * @override
         */
        start: function () {
            return this._super.apply(this, arguments).then(this.prepareWidgetOptions.bind(this));
        },
        /**
         * Set widget default value
         */
        setDefault: function () {
        },
        /**
         * get fields type
         */
        getFillFieldsType: function () {
            return [];
        },
        /**
         * Prepare widget options
         */
        prepareWidgetOptions: function () {
            if (this.mode === 'edit') {
                // update 'fillfields', 'component_form', 'delimiter' if exists
                if (this.attrs.options) {
                    if (this.attrs.options.hasOwnProperty('component_form')) {
                        this.component_form = _.defaults({}, this.attrs.options.component_form, this.component_form);
                    }
                    if (this.attrs.options.hasOwnProperty('delimiter')) {
                        this.fillfields_delimiter = _.defaults({}, this.attrs.options.delimiter, this.fillfields_delimiter);
                    }
                    if (this.attrs.options.hasOwnProperty('lat')) {
                        this.lat = this.attrs.options.lat;
                    }
                    if (this.attrs.options.hasOwnProperty('lng')) {
                        this.lng = this.attrs.options.lng;
                    }
                    if (this.attrs.options.hasOwnProperty('address_form')) {
                        this.address_form = _.defaults({}, this.attrs.options.address_form, this.address_form);
                    }
                }

                this.target_fields = this.getFillFieldsType();
                this.initGplacesAutocomplete().then(function (self) {
                    self._geolocate();
                });
            }
        },
        /**
         * Geolocate
         * @private
         */
        _geolocate: function () {
            var self = this;
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function (position) {
                    var geolocation = {
                        lat: position.coords.latitude,
                        lng: position.coords.longitude
                    };

                    var circle = new google.maps.Circle({
                        center: geolocation,
                        radius: position.coords.accuracy
                    });
                    if (self.places_autocomplete) {
                        self.places_autocomplete.setBounds(circle.getBounds());
                    }
                });
            }
        },
        /**
         * @private
         */
        _prepareValue: function (model, field_name, value) {
            var model = model || false;
            var field_name = field_name || false;
            var value = value || false;
            return Utils.fetchValues(model, field_name, value);
        },
        /**
         * @private
         */
        _populateAddress: function (place, fillfields, delimiter) {
            var place = place || false;
            var fillfields = fillfields || this.fillfields;
            var delimiter = delimiter || this.fillfields_delimiter;
            return Utils.gmaps_populate_address(place, fillfields, delimiter);
        },
        /**
         * Map google address into Odoo fields
         * @param {*} place
         * @param {*} fillfields
         */
        _populatePlaces: function (place, fillfields) {
            var place = place || false;
            var fillfields = fillfields || this.fillfields;
            return Utils.gmaps_populate_places(place, fillfields);
        },
        /**
         * Get country's state
         * @param {*} model
         * @param {*} country
         * @param {*} state
         */
        _getCountryState: function (model, country, state) {
            var model = model || false;
            var country = country || false;
            var state = state || false;
            return Utils.fetchCountryState(model, country, state);
        },
        /**
         * Set country's state
         * @param {*} model
         * @param {*} country
         * @param {*} state
         */
        setCountryState: function (model, country, state) {
            var self = this;
            if (model && country && state) {
                this._getCountryState(model, country, state).then(function (result) {
                    var state = {
                        [self.address_form.state_id]: result,
                    }
                    self._onUpdateWidgetFields(state);
                });
            }
        },
        /**
         * @private
         */
        _setGeolocation: function (latitude, longitude) {
            var res = {};
            if (_.intersection(_.keys(this.record.fields), [this.lat, this.lng]).length === 2) {
                res[this.lat] = latitude;
                res[this.lng] = longitude;
            }
            return res;
        },
        /**
         * @private
         */
        _onUpdateWidgetFields: function (values) {
            var values = values || {};
            this.trigger_up('field_changed', {
                dataPointID: this.dataPointID,
                changes: values,
                viewType: this.viewType,
            });
        },
        /**
         * Initialize google autocomplete
         * return promise
         */
        initGplacesAutocomplete: function () {
            return $.when();
        },
        /**
         * @override
         */
        destroy: function () {
            if (this.places_autocomplete) {
                this.places_autocomplete.unbindAll();
            }
            // Remove all PAC container in DOM if any
            $('.pac-container').remove();
            return this._super();
        }

    });


    GMapMarker = Widget.extend({
        jsLibs: [],
        template: "gmap_marker",

        init: function (view, record, node) {
            // key = '';  // de citit cheia
            // if (typeof google == 'undefined') {
            //     this.jsLibs.push('http://maps.googleapis.com/maps/api/js?key=' + key)
            // }
            var self = this;
            console.log('view', record.model);
            console.log('view', record.res_id);
            console.log('view', node);
            this._super.apply(this, arguments);

            this.field_lat = node.attrs.lat;
            this.field_lng = node.attrs.lng;
            this.shown = $.Deferred();
            this.data = record.data;
            this.mode = view.mode || "readonly";
            this.record = record;
            this.view = view;

        },

        willStart: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                if (typeof google !== 'object' || typeof google.maps !== 'object') {
                    self._rpc({
                        route: '/google/google_maps_api_key',
                    }).then(function (data) {
                        var data_json = JSON.parse(data);
                        self.key = data_json.google_maps_api_key;
                        var google_url = 'http://maps.googleapis.com/maps/api/js?key=' + self.key;
                        //self.jsLibs.push(google_url);
                        window.google_on_ready = self.on_ready;
                        $.getScript(google_url + '&callback=google_on_ready');
                    });
                }
            });
        },

        start: function () {
            var self = this;
            console.log('change', this.$el[0])
            console.log('change', view_registry)

            return this._super().then(function () {
                if (typeof google == 'object') {
                    self.on_ready();
                }
            });
        },


        on_ready: function () {
            var lat = this.data[this.field_lat];
            var lng = this.data[this.field_lng];

            var myLatlng = new google.maps.LatLng(lat, lng);
            var bounds = new google.maps.LatLngBounds();

            var mapOptions = {
                zoom: 15,
                center: myLatlng
            };

            var div_gmap = this.$el[0];

            map = new google.maps.Map(div_gmap, mapOptions);
            this.marker = new google.maps.Marker({
                position: myLatlng,
                map: map,
                draggable: this.mode == 'edit' ? true : false,
            });

            var my_self = this;

            google.maps.event.addListener(this.marker, 'dragend', function (NewPoint) {
                lat = NewPoint.latLng.lat();
                lng = NewPoint.latLng.lng();
                my_self.update_latlng(lat, lng);
            });
            google.maps.event.addListener(map, "click", function (NewPoint) {
                lat = NewPoint.latLng.lat();
                lng = NewPoint.latLng.lng();
                my_self.update_latlng(lat, lng);
            });

            this.view.on("field_changed:" + this.field_lat, this, this.display_result);
            this.view.on("field_changed:" + this.field_lng, this, this.display_result);


            //bounds.extend(myLatlng);
            //map.fitBounds(bounds);       # auto-zoom
            //map.panToBounds(bounds);     # auto-center

            google.maps.event.trigger(map, 'resize');
        },

        update_latlng: function (lat, lng) {

            this.data[this.field_lat] = lat;
            this.data[this.field_lng] = lng;


            var def = $.Deferred();
            var changes = {};
            changes[this.field_lat] = lat;
            changes[this.field_lng] = lng;

            this.trigger_up('field_changed', {
                dataPointID: this.record.id,
                changes: changes,
                onSuccess: def.resolve.bind(def),
                onFailure: def.reject.bind(def),
            });
            this.display_result();
        },

        display_result: function () {
            var lat = this.data[this.field_lat];
            var lng = this.data[this.field_lng];
            var myLatlng = new google.maps.LatLng(lat, lng);
            map.setCenter(myLatlng);
            this.marker.setPosition(myLatlng);
            google.maps.event.trigger(map, 'resize')

        },


    });
    var model_check;
    GMapRoute = Widget.extend({

        jsLibs: [],
        template: "gmap_route",

        init: function (view, record, node) {
            // key = '';  // de citit cheia
            // if (typeof google == 'undefined') {
            //     this.jsLibs.push('http://maps.googleapis.com/maps/api/js?key=' + key)
            // }
            var self = this;
            console.log('gmap_route1', record.model);
            console.log('gmap_route1', record.res_id);
            console.log('gmap_route1', node);
            this.model_check= record.model;
            this._super.apply(this, arguments);


            this.field_lat = node.attrs.lat;
            this.field_lng = node.attrs.lng;
            this.field_vehicle = node.attrs.vehicle;
            this.field_date_plan = node.attrs.date;
            this.shown = $.Deferred();
            this.data = record.data;
            this.mode = view.mode || "readonly";
            this.record = record;
            this.view = view;

        },

        willStart: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                if (typeof google !== 'object' || typeof google.maps !== 'object') {
                    self._rpc({
                        route: '/google/google_maps_api_key',
                    }).then(function (data) {
                        var data_json = JSON.parse(data);
                        self.key = data_json.google_maps_api_key;
                        var google_url = 'http://maps.googleapis.com/maps/api/js?key=' + self.key;
                        //self.jsLibs.push(google_url);
                        window.google_on_ready = self.on_ready;
                        $.getScript(google_url + '&callback=google_on_ready');
                    });
                }
            });
        },

        start: function () {
            var self = this;
            console.log('change', this.$el[0])
            console.log('change', view_registry)
            return this._super().then(function () {
                if (typeof google == 'object') {
                    self.on_ready();
                }
            });
        },


        on_ready: function () {
            var lat = this.data[this.field_lat];
            var lng = this.data[this.field_lng];

            var myLatlng = new google.maps.LatLng(lat, lng);
            var bounds = new google.maps.LatLngBounds();

            var mapOptions = {
                zoom: 15,
                center: myLatlng
            };

            var div_gmap = this.$el[0];

            map = new google.maps.Map(div_gmap, mapOptions);
            this.marker = new google.maps.Marker({
                position: myLatlng,
                map: map
            });
            mapCenter = map;
            var my_self = this;
//            google.maps.event.addListener(this.marker, 'dragend', function (NewPoint) {
//                lat = NewPoint.latLng.lat();
//                lng = NewPoint.latLng.lng();
//                my_self.update_latlng(lat, lng);
//            });
//            google.maps.event.addListener(map, "click", function (NewPoint) {
//                lat = NewPoint.latLng.lat();
//                lng = NewPoint.latLng.lng();
//                my_self.update_latlng(lat, lng);
//            });

            this.view.on("field_changed:" + this.field_lat, this, this.display_result);
            this.view.on("field_changed:" + this.field_lng, this, this.display_result);

            //bounds.extend(myLatlng);
            //map.fitBounds(bounds);       # auto-zoom
            //map.panToBounds(bounds);     # auto-center

            google.maps.event.trigger(map, 'resize');
            //TODO : test thu draw 2 lần 23 point
            var scan_routing = utils.get_cookie('load_routing_map');
            console.log('scan_routing',scan_routing)
            if (this.model_check ==='sharevan.routing.vehicle'&& scan_routing== '1'){
                setInterval(() => {
                    var reload_load_routing_map = utils.get_cookie('reload_load_routing_map');
                    if (reload_load_routing_map== '1'){
                        this.load_routing();
                    }
                }, 1000);
            }else{
                console.log('load normal')
                this.load_routing();
            }
        },
         load_routing: function () {
            let current_datetime = new Date()
            let formatted_date = current_datetime.getFullYear() + "-" + this._appendLeadingZeroes(current_datetime.getMonth() + 1)
                + "-" + this._appendLeadingZeroes(current_datetime.getDate())
            var vehicle = this.data[this.field_vehicle];
            var date_plan = this.data[this.field_date_plan];
            console.log('date_plan', vehicle)
            console.log('formatted_date', this.data)
            if (date_plan!== undefined && date_plan!== false&&vehicle!== undefined&& vehicle.res_id!== undefined){
                    session.rpc('/routing_plan_day/get_driver_routing_plan_by_vehicle', {
                    vehicle_id: vehicle.res_id,
                    date_plan: date_plan.format("YYYY-MM-DD").toString(),
                    type: 1
                    }).then((routing_day) => {
                        utils.set_cookie('load_routing_map', '0');
                        utils.set_cookie('reload_load_routing_map', '0');
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
                                    name: routing.address + ' - ' + routing.warehouse_name,
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
                                        title: waypts[i].name + '<br>' + 'Order number: ' + order_number.toString(),
                                        label: {
                                            color: 'black',
                                            fontWeight: 'bold',
                                            fontSize :'12px',
                                            text: order_number.toString(),
                                        },
                                        icon: {
                                            url: '/web_google_maps/static/src/img/markers/start.png',
                                            labelOrigin: new google.maps.Point(16, 20)
                                        }
                                    });
                                } else if (order_number.includes(ways.length.toString())) {
                                    dmarker = new google.maps.Marker({
                                        position: waypts[i],
                                        map: mapCenter,
                                        title: waypts[i].name + '<br>' + 'Order number:' + order_number.toString(),
                                        label: {
                                            color: 'black',
                                            fontWeight: 'bold',
                                            fontSize :'12px',
                                            text: order_number.toString(),
                                        },
                                        icon: {
                                            url: '/web_google_maps/static/src/img/markers/finish-line.png',
                                            labelOrigin: new google.maps.Point(16, 20)
                                        }
                                    });
                                } else {
                                    dmarker = new google.maps.Marker({
                                        position: waypts[i],
                                        map: mapCenter,
                                        title: waypts[i].name + '<br>' + 'Order number:' + order_number.toString(),
                                        label: {
                                            color: 'black',
                                            fontWeight: 'bold',
                                            fontSize :'12px',
                                            text: order_number.toString(),
                                        },
                                        icon: {
                                            url: '/web_google_maps/static/src/img/markers/warehouse/red.png',
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
                    }else{
                        window.gRenderers = [];
                        window.dMarker = [];
                    }
                });
            }
        },
         _appendLeadingZeroes: function (n) {
            if (n <= 9) {
                return "0" + n;
            }
            return n
        },
        _removeDuplicate: function (data, key) {
            return [...new Map(data.map(x => [key(x), x])).values()]
        },

        update_latlng: function (lat, lng) {

            this.data[this.field_lat] = lat;
            this.data[this.field_lng] = lng;


            var def = $.Deferred();
            var changes = {};
            changes[this.field_lat] = lat;
            changes[this.field_lng] = lng;

            this.trigger_up('field_changed', {
                dataPointID: this.record.id,
                changes: changes,
                onSuccess: def.resolve.bind(def),
                onFailure: def.reject.bind(def),
            });
            this.display_result();
        },

        display_result: function () {
            var lat = this.data[this.field_lat];
            var lng = this.data[this.field_lng];
            var myLatlng = new google.maps.LatLng(lat, lng);
            map.setCenter(myLatlng);
            this.marker.setPosition(myLatlng);
            google.maps.event.trigger(map, 'resize')

        },

    });

    widgetRegistry.add('gmap_route', GMapRoute);

//core.form_custom_registry.add('gmap_marker', GMapMarker);
    widgetRegistry.add('gmap_marker', GMapMarker);

    var GplacesAddressAutocompleteField = GplaceAutocomplete.extend({
        className: 'o_field_char o_field_google_address_autocomplete',
        /**
         * @override
         */
        setDefault: function () {
            this._super.apply(this, arguments);
            this.fillfields = {
                [this.address_form.street]: ['street_number', 'route'],
                [this.address_form.street2]: ['administrative_area_level_4', 'administrative_area_level_5'],
                [this.address_form.city_name]: ['locality', 'administrative_area_level_1'],
                [this.address_form.zip]: 'postal_code',
                [this.address_form.state_id]: ['administrative_area_level_1', 'locality'],
                [this.address_form.country_id]: 'country',
                [this.address_form.district]: ['administrative_area_level_2'],
                [this.address_form.ward]: ['administrative_area_level_3']
            };
        },
        /**
         * @override
         */
        prepareWidgetOptions: function () {
            if (this.mode === 'edit' && this.attrs.options) {
                if (this.attrs.options.hasOwnProperty('fillfields')) {
                    this.fillfields = _.defaults({}, this.attrs.options.fillfields, this.fillfields);
                }
            }
            this._super();
        },
        /**
         * Get fields attributes
         * @override
         */
        getFillFieldsType: function () {
            var self = this,
                res = this._super();
            if (this._isValid) {
                _.each(Object.keys(this.fillfields), function (field_name) {
                    res.push({
                        name: field_name,
                        type: self.record.fields[field_name].type,
                        relation: self.record.fields[field_name].relation
                    });
                });
            }
            return res;
        },
        /**
         * Callback function for places_change event
         */
        handlePopulateAddress: function () {
            var place = this.places_autocomplete.getPlace();
            if (place.hasOwnProperty('address_components')) {
                var google_address = this._populateAddress(place);
                this.populateAddress(place, google_address);
                console.log(google_address);
                console.log(place)
                this.$input.val(place.name);
            }
        },
        /**
         * Populate address form the Google place
         * @param {*} place
         * @param {*} parse_address
         */
        populateAddress: function (place, parse_address) {
            var self = this;
            var requests = [];
            var index_of_state = _.findIndex(this.target_fields, function (f) {
                return f.name === self.address_form.state_id
            });
            var target_fields = this.target_fields.slice();
            var field_state = index_of_state > -1 ? target_fields.splice(index_of_state, 1)[0] : false;

            _.each(target_fields, function (field) {
                requests.push(self._prepareValue(field.relation, field.name, parse_address[field.name]));
            });

            console.log(this);

            requests.push(self._prepareValue(false, 'latitude', place.geometry.location.lat()));
            requests.push(self._prepareValue(false, 'longitude', place.geometry.location.lng()));
            if (map !== undefined) {
                var myLatlng = new google.maps.LatLng(place.geometry.location.lat(), place.geometry.location.lng());
                if (this.marker === undefined) {
                    this.marker = new google.maps.Marker({
                        position: myLatlng,
                        map: map,
                        draggable: false,
                        //                draggable: this.mode == 'edit' ? true : false,
                    });
                } else {
                    this.marker.setMap(null);
                    this.marker = new google.maps.Marker({
                        position: myLatlng,
                        map: map,
                        draggable: false,
                        //                draggable: this.mode == 'edit' ? true : false,
                    });
                }
                map.setCenter(myLatlng);

            }
            // Set geolocation
            var partner_geometry = this._setGeolocation(place.geometry.location.lat(), place.geometry.location.lng());
            _.each(partner_geometry, function (val, field) {
                requests.push(self._prepareValue(false, field, val));
            });

            $.when.apply($, requests).done(function () {
                var changes = {};
                _.each(arguments, function (data) {
                    _.each(data, function (val, key) {
                        if (typeof val === 'object') {
                            changes[key] = val;
                        } else {
                            changes[key] = self._parseValue(val);
                        }
                    });
                });

                self._onUpdateWidgetFields(changes);
                if (field_state) {
                    var country = _.has(changes, self.address_form.country_id) ? changes[self.address_form.country_id]['id'] : false;
                    var state_code = parse_address[self.address_form.state_id];
                    self.setCountryState(field_state.relation, country, state_code);
                }
            });
        },
        initGplacesAutocomplete: function () {
            var self = this;
            var def = $.Deferred();
            setTimeout(function () {
                if (!self.places_autocomplete) {
                    self.places_autocomplete = new google.maps.places.Autocomplete(self.$input.get(0), {
                        types: ['address'],
                        fields: ['address_components', 'name', 'geometry']
                    });
                    if (self.autocomplete_settings) {
                        self.places_autocomplete.setOptions(self.autocomplete_settings);
                    }
                }
                // When the user selects an address from the dropdown, populate the address fields in the form.
                self.places_autocomplete.addListener('place_changed', self.handlePopulateAddress.bind(self));
                def.resolve(self);
            }, 300);
            return def.promise();
        },
        /**
         * @override
         */
        isValid: function () {
            this._super.apply(this, arguments);
            var self = this,
                unknown_fields;

            unknown_fields = _.filter(_.keys(self.fillfields), function (field) {
                return !self.record.fields.hasOwnProperty(field);
            });
            if (unknown_fields.length > 0) {
                self.do_warn(_t('The following fields are invalid:'), _t('<ul><li>' + unknown_fields.join('</li><li>') + '</li></ul>'));
                this._isValid = false;
            }
            return this._isValid;
        },
        /**
         * @override
         */
        destroy: function () {
            if (this.places_autocomplete) {
                google.maps.event.clearInstanceListeners(this.places_autocomplete);
            }
            return this._super();
        }
    });

    var GplacesAutocompleteField = GplaceAutocomplete.extend({
        className: 'o_field_char o_field_google_places_autocomplete',
        setDefault: function () {
            this._super.apply(this);
            this.fillfields = {
                general: {
                    name: 'name',
                    website: 'website',
                    phone: ['international_phone_number', 'formatted_phone_number']
                },
                address: {
                    street: ['street_number', 'route'],
                    street2: ['administrative_area_level_3', 'administrative_area_level_4', 'administrative_area_level_5'],
                    city_name: 'locality',
                    zip: 'postal_code',
                    state_id: 'administrative_area_level_1',
                    country_id: 'country'
                }
            };
        },
        prepareWidgetOptions: function () {
            if (this.mode === 'edit' && this.attrs.options) {
                if (this.attrs.options.hasOwnProperty('fillfields')) {
                    if (this.attrs.options.fillfields.hasOwnProperty('address')) {
                        this.fillfields['address'] = _.defaults({}, this.attrs.options.fillfields.address, this.fillfields.address);
                    }
                    if (this.attrs.options.fillfields.hasOwnProperty('general')) {
                        this.fillfields['general'] = _.defaults({}, this.attrs.options.fillfields.general, this.fillfields.general);
                    }
                    if (this.attrs.options.fillfields.hasOwnProperty('geolocation')) {
                        this.fillfields['geolocation'] = this.attrs.options.fillfields.geolocation;
                    }
                }
            }
            this._super();
        },
        getFillFieldsType: function () {
            var self = this,
                res = this._super();
            if (this._isValid) {
                _.each(this.fillfields, function (option) {
                    _.each(Object.keys(option), function (field_name) {
                        res.push({
                            name: field_name,
                            type: self.record.fields[field_name].type,
                            relation: self.record.fields[field_name].relation
                        });
                    });
                });
            }
            return res;
        },
        _setGeolocation: function (lat, lng) {
            var res = {};
            if (this.lat && this.lng) {
                return this._super(lat, lng);
            } else if (this.fillfields.geolocation) {
                _.each(this.fillfields.geolocation, function (alias, field) {
                    if (alias === 'latitude') {
                        res[field] = lat;
                    }
                    if (alias === 'longitude') {
                        res[field] = lng;
                    }
                });
            }
            return res;
        },
        handlePopulateAddress: function () {
            var self = this;
            var place = this.places_autocomplete.getPlace();
            if (place.hasOwnProperty('address_components')) {
                var values = {};
                var requests = [];
                var index_of_state = _.findIndex(this.target_fields, function (f) {
                    return f.name === self.address_form.state_id
                });
                var target_fields = this.target_fields.slice();
                var field_state = index_of_state > -1 ? target_fields.splice(index_of_state, 1)[0] : false;
                // Get address
                var google_address = this._populateAddress(place, this.fillfields.address, this.fillfields_delimiter);
                _.extend(values, google_address);
                // Get place (name, website, phone)
                var google_place = this._populatePlaces(place, this.fillfields.general);
                _.extend(values, google_place);
                // Set place geolocation
                var google_geolocation = self._setGeolocation(place.geometry.location.lat(), place.geometry.location.lng());
                _.extend(values, google_geolocation);

                _.each(target_fields, function (field) {
                    requests.push(self._prepareValue(field.relation, field.name, values[field.name]));
                });
                requests.push(self._prepareValue(false, 'partner_latitude', place.geometry.location.lat()));
                requests.push(self._prepareValue(false, 'partner_longitude', place.geometry.location.lng()));
                $.when.apply($, requests).done(function () {
                    var changes = {}
                    _.each(arguments, function (data) {
                        _.each(data, function (val, key) {
                            if (typeof val === 'object') {
                                changes[key] = val;
                            } else {
                                changes[key] = self._parseValue(val);
                            }
                        });
                    });
                    self._onUpdateWidgetFields(changes);
                    if (field_state) {
                        var country = _.has(changes, self.address_form.country_id) ? changes[self.address_form.country_id]['id'] : false;
                        var state_code = google_address[self.address_form.state_id];
                        self.setCountryState(field_state.relation, country, state_code);
                    }
                });
                this.$input.val(place.name);
            }
        },
        initGplacesAutocomplete: function () {
            var self = this;
            var def = $.Deferred();
            setTimeout(function () {
                if (!self.places_autocomplete) {
                    self.places_autocomplete = new google.maps.places.Autocomplete(self.$input.get(0), {
                        types: ['establishment'],
                        fields: ['address_components', 'name', 'website', 'geometry',
                            'international_phone_number', 'formatted_phone_number'],
                    });
                    if (self.autocomplete_settings) {
                        self.places_autocomplete.setOptions(self.autocomplete_settings);
                    }
                }
                // When the user selects an address from the dropdown, populate the address fields in the form.
                self.places_autocomplete.addListener('place_changed', self.handlePopulateAddress.bind(self));
                def.resolve(self);
            }, 300);
            return def.promise();
        },
        /**
         * @override
         */
        isValid: function () {
            this._super.apply(this, arguments);
            var self = this,
                unknown_fields;
            for (var option in this.fillfields) {
                unknown_fields = _.filter(_.keys(this.fillfields[option]), function (field) {
                    return !self.record.fields.hasOwnProperty(field);
                });
                if (unknown_fields.length > 0) {
                    self.do_warn(_t('The following fields are invalid:'), _t('<ul><li>' + unknown_fields.join('</li><li>') + '</li></ul>'));
                    this._isValid = false;
                }
            }
            return this._isValid;
        },
        /**
         * @override
         */
        destroy: function () {
            if (this.places_autocomplete) {
                google.maps.event.clearInstanceListeners(this.places_autocomplete);
            }
            return this._super();
        }
    });

    return {
        GplacesAddressAutocompleteField: GplacesAddressAutocompleteField,
        GplacesAutocompleteField: GplacesAutocompleteField
    };

});