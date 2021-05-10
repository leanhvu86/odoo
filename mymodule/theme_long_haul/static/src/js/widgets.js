odoo.define('theme_long_haul.widgets', (require) => {
    "use strict";
    var core = require('web.core');
    var publicWidget = require('web.public.widget');
    var googleScriptLoaded = $.Deferred();
    var map;
    var _t = core._t;

    publicWidget.registry.google_map = publicWidget.Widget.extend({
        selector: '.googleMap, .item_bidding',
        events: {
            'click .map': '_onClickClose',
        },
        _onClickClose: function (ev) {
            var self = this;
            var div_gmap = $(this.$el[0]).find("#load")[0];
            if (div_gmap.innerHTML == "0") {
                var google_url = 'http://maps.googleapis.com/maps/api/js?key=' + 'AIzaSyDbIf1-IDfQ0DGaOvAfu5lNZ0bZm0VaisM';
                window.google_on_ready = self.on_ready;
                $.getScript(google_url + '&callback=google_on_ready');
                div_gmap.innerHTML = "1"
            }
        },
        start: function () {
        },
        on_ready: function () {
            var self = this;
            var div_gmap = $(this.$el[0]).find(".googleMap")[0];
            // var div_gmap = document.getElementById('map_container')
            //  var div_gmap = div_gmapx[0];
            //   this.field_from_lat = '21.036747';
            //   this.field_from_lng = '105.7682911';
            //   this.field_to_lat = '21.0204036';
            //   this.field_to_lng = '105.7744628';
            var from_lat = div_gmap.attributes.from_latitude.value;
            var from_lng = div_gmap.attributes.from_longitude.value;
            var to_lat = div_gmap.attributes.to_latitude.value;
            var to_lng = div_gmap.attributes.to_longitude.value;
            var param = this.param;

            // var div_gmap = this.$el[0];

            var from_Latlng = new google.maps.LatLng(from_lat, from_lng);
            var to_Latlng = new google.maps.LatLng(to_lat, to_lng);

            var mapOptions = {
                zoom: 8,
                center: from_Latlng
            };
            // $("div").children(".selected")
            // document.getElementById('map_container')
            // var $target = $(event.target);
            // if ($target.is("li")) {
            //     $target.children("ul").toggle();
            // }
            map = new google.maps.Map(div_gmap, mapOptions);

            this.directionsService = new google.maps.DirectionsService();
            this.directionsDisplay = new google.maps.DirectionsRenderer();
            this.directionsDisplay.setMap(map);

            var request = {
                origin: from_Latlng,
                destination: to_Latlng,
                travelMode: 'DRIVING'
            }
            self.directionsService.route(request, function (result, status) {
                if (status == "OK") {
                    self.directionsDisplay.setDirections(result);
                }
            });
        },
        /**
         * @override
         */
        destroy: function () {
            this._super.apply(this, arguments);
            if (this.$loadingWarning) {
                this.$loadingWarning.remove();
            }
        },
    });

    return {
        googleScriptLoaded: googleScriptLoaded,
    };
})