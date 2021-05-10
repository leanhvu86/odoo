odoo.define('website_order_customer.OrderSearchForm', function (require) {
    "use strict";
    /*
        follow template in search_views.xml
        * require: use class like bellow for root div and input your model
        class="o_order_search_form" model=""
    */
    var Widget = require('web.Widget');
    var core = require('web.core');
    var QWeb = core.qweb;
    var session = require('web.session');
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');

    publicWidget.registry.SearchWarehouse = publicWidget.Widget.extend({
        selector: '.o_order_search_form',
        events: {
            'click .search-button': '_onClickSearch',
            'click ul.pagination > li': '_onClickPager',
            'keydown .order-input': '_onInputKeyDown',
            'click .view_details': '_onViewDetails',
        },

        init: function (parent, data, options, recordOptions) {
            this._super(parent);
            this.db_id = data.id;
            this.data_records = data.data;
            this.data = data;
            this.headers = [];
            this.current_page = 1;
            this.loaded_page = 1;
            this.total_page = 0;
            this.page_size = 10;
            console.log("Init table", this);
        },

        start: function () {
            this._getHeadersValue();
            this.model = this.target.getAttribute("model");
            var method = this.target.getAttribute("method");
            this.search_method = method != null && method.length > 0 ?
                this.target.getAttribute("method") : "search_read";

            ajax.loadXML('/website_order_customer/static/src/xml/static_templates.xml', QWeb);
        },

        _onClickSearch: function (ev) {
            this.current_page = 1;
            ev.stopPropagation();
            this._doSearch();
        },

        _doSearch: function () {
            var self = this;
            var listInput = self.$(".order-input");
            var tableContent = self.$(".table tbody")[0];
            tableContent.classList.add("loading");
            if (self.data.length > 0) {
                var loader = self.$(".loader")[0];
                loader.style.display = '';
            }
            var args = [];
            var domain = [];
            var count = self.search_method == null ? false: true;
            var orderBy = [{name: 'id', asc: false}];
            var offset = (self.current_page - 1) * self.page_size;
            for (var i = 0; i < listInput.length; i++) {
                var key = listInput[i].getAttribute("name");
                var value = listInput[i].value;
                if (value && value.length > 0) {
                    domain.push([key, 'ilike', value]);
                }
            }
            args = self.search_method == 'search_read' ? [domain]: [domain, self.headers, offset, self.page_size, orderBy, count];
            this._rpc({
                model: self.model,
                method: self.search_method == 'search_read' ? 'search_count': self.search_method,
                args: args,
            }).then(function (res) {
                self.total_page = Math.ceil(res / self.page_size);
                console.log("Total page", self.total_page);
                self._updatePager();
                if (self.total_page == 0 && self.search_method == 'search_read') {
                    return;
                }
            });
            args = self.search_method == 'search_read' ? args = null: [domain, self.headers, offset, self.page_size, orderBy, false];
            console.log("Args",args);
            return self._rpc({
                model: self.model,
                method: self.search_method,
                context: session.user_context,
                domain: domain,
                args: args,
                limit: self.page_size,
                orderBy: orderBy,
                offset: offset,
                fields: self.headers,
            }).then(function (res) {
                console.log("Result", res);
                self.data = res;
                self._renderRows();
                self._updatePager();
                self.loaded_page = self.current_page;
            });
        },

        _onClickPager: function (ev) {
            ev.stopPropagation();
            var self = this;
            var target = ev.currentTarget.querySelector('a');
            if (target.classList.contains("selected"))
                return;
            if (target.classList.contains('first')) {
                self.current_page = 1;
            } else if (target.classList.contains('last')) {
                self.current_page = self.total_page;
            } else {
                if (target.innerHTML) {
                    self.current_page = parseInt(target.innerHTML);
                }
            }
            if (self.loaded_page == self.current_page)
                return;
            self._doSearch(ev);
        },

        //  Render a row for every
        _renderRows: function () {
            var fields = this.headers;
            var listRow = [];
            var tableContent = this.$("table tbody")[0];
            tableContent.innerHTML = "";
            tableContent.classList.remove("loading");
            var loader = this.$(".loader")[0];
            loader.style.display = 'none';
            var rows = QWeb.render('order_data_rows', {
                list: this.data,
                headers: this.headers,
            });
            // rows.filter('.view-details').on('click', this._onViewDetails());
            tableContent.innerHTML = rows;
        },

        _onViewWarehouseDetails: function (ev) {
            var self = this;
            //init lib
            ajax.jsonRpc('/share_van_order/get_warehouse_by_id', 'call', {
                'warehouseId': 15
            }).then(function (result) {
                var $rendered_html = $(QWeb.render('website_order_customer.warehouse_details', {
                    warehouse: result.records
                }));
                var div_gmap = $(self.$el[0]).find("#load_lib_map")[0];
                var gmap = $rendered_html.find("#map_container")[0]
                var map, myMarker, myLatlng;
                if (div_gmap.innerHTML == "0") { //load lib 1 lan
                    var google_url = 'http://maps.googleapis.com/maps/api/js?key=' + 'AIzaSyDbIf1-IDfQ0DGaOvAfu5lNZ0bZm0VaisM';
                    window.google_map_on_ready = _findMapView
                    $.getScript(google_url + '&callback=google_map_on_ready');
                    div_gmap.innerHTML = "1"
                } else {
                    _findMapView()
                }

                function _findMapView() {
                    map = new google.maps.Map(gmap, {
                        center: {lat: 21.0525414, lng: 105.7454841},
                        zoom: 12,
                    })
                    myLatlng = new google.maps.LatLng(21.0525414, 105.7454841);
                    myMarker = new google.maps.Marker({
                        position: myLatlng
                    });
                    myMarker.setMap(map);
                    $("#bd-example-modal-lg").on("shown.bs.modal", function () {
                        var refresh = function () {
                            console.log('refresh')
                            var center = map.getCenter();
                            google.maps.event.trigger(map, "resize");
                            map.setCenter(center);
                        }
                        setTimeout(refresh, 200);
                        open = true;
                    });
                    /*$(document).on('shown.bs.modal', $(''), function () {
                        var refresh = function () {
                            console.log('refresh')
                            var center = map.getCenter();
                            google.maps.event.trigger(map, "resize");
                            map.setCenter(center);
                        }
                        setTimeout(refresh, 200);
                        open = true;
                    });*/
                }

                $('#bd-example-modal-lg .modal-content').append($rendered_html);

            }).then(() => {
                $('#bd-example-modal-lg').modal('toggle');
            })
        },

        _onViewDetails: function (ev) {
            $(body).append($(QWeb.render('website_order_customer.modal_details')));
            switch (this.model) {
                case 'sharevan.bill.lading.detail':
                    this._onViewOrderDetails(ev);
                    break;
                case 'sharevan.warehouse':
                    this._onViewWarehouseDetails(ev);
                    break;
            }
            $('#bd-example-modal-lg').on('hidden.bs.modal', function () {
                $('#bd-example-modal-lg').remove()
            })
        },

        _onViewOrderDetails: function (ev) {
            var row_id = $(ev.currentTarget).parents().attr('id')
            ajax.jsonRpc('/share_van_order/get_bill_lading_details', 'call', {
                'bill_ladding_id': 1124
            }).then(function (result) {
                var $rendered_html = $(QWeb.render('website_order_customer.order_details', {
                    values: result.records[0],
                    currency: localStorage.getItem('currency')
                }));
                $('#bd-example-modal-lg .modal-content').append($rendered_html);
            }).then(() => {
                $('#bd-example-modal-lg').modal('show');
            })
        },

        _getHeadersValue: function () {
            var listHeaders = this.$("table .table-thead tr th");
            var headers_value = []
            for (let header of listHeaders) {
                var temp = header.getAttribute('name');
                if (temp) {
                    headers_value.push(temp);
                }
            }
            this.headers = headers_value;
        },

        _onInputKeyDown: function (ev) {
            switch (ev.which) {
                case $.ui.keyCode.ENTER:
                    ev.preventDefault();
                    ev.stopPropagation();
                    this._doSearch();
                    break;
            }
        },

        /*
            if search result is empty, hide pager
            else remove every selected, set number for pager buttons and set selected button
        */
        _updatePager: function () {
            var self = this;
            var pagination = self.$('.pagination')[0];
            var selected = null;
            var listPage = self.$('.pagination li a:not(.first):not(.last)');
            if (self.total_page == 0) {
                pagination.style.setProperty("display", "none", "important");
                return;
            } else {
                pagination.style.display = "";
                if (self.total_page > 2){
                    listPage[2].style.setProperty("display", "");
                    listPage[1].style.setProperty("display", "");
                } else if (self.total_page > 1){
                    listPage[2].style.setProperty("display", "none");
                    listPage[1].style.setProperty("display", "");
                } else if (self.total_page == 1){
                    listPage[2].style.setProperty("display", "none");
                    listPage[1].style.setProperty("display", "none");
                }
            }
            for (let page of listPage) {
                page.classList.remove("selected")
            }
            if (self.current_page == 1) {
                listPage[0].innerHTML = "1";
                listPage[0].classList.add("selected")
                listPage[1].innerHTML = "2";
                listPage[2].innerHTML = "3";
            } else if (self.current_page == self.total_page) {
                var index = 0;
                for (var i = self.total_page - 2; i <= self.total_page; i++) {
                    if (i<1) continue;
                    listPage[index].innerHTML = i;
                    index++;
                }
                if (self.total_page <= 3){
                    listPage[self.total_page-1].classList.add("selected");
                } else {
                    listPage[2].classList.add("selected");
                }
            } else {
                var index = 0;
                for (var i = self.current_page - 1; (i <= self.current_page + 1) && (i <= self.total_page); i++) {
                    listPage[index].innerHTML = i;
                    index++;
                }
                for (var i = self.total_page + 1; i <= self.current_page + 1; i++) {
                    listPage[index].display = "none";
                    index++;
                }
                listPage[1].classList.add("selected");
            }
        }
    });
});