odoo.define('web_google_maps.MapController', function (require) {
    'use strict';

    var Context = require('web.Context');
    var core = require('web.core');
    var BasicController = require('web.BasicController');
    var Domain = require('web.Domain');
    var session = require('web.session');

    var _t = core._t;
    var qweb = core.qweb;
    var id;
    var options = {
        context: {},
        domain: [],
        groupBy: [],
        groupOffSet: 0,
        offSet: 0,
        orderBy: null
    };

    var MapController = BasicController.extend({
        custom_events: _.extend({}, BasicController.prototype.custom_events, {
            button_clicked: '_onButtonClicked',
            kanban_record_delete: '_onRecordDelete',
            kanban_record_update: '_onUpdateRecord',
            kanban_column_archive_records: '_onArchiveRecords',
            changeFilter: '_onChangeFilter',
        }),
        /**
         * @override
         * @param {Object} params
         */
        init: function (parent, model, renderer, params) {
            this._super.apply(this, arguments);
            this.viewType = params.viewType;
            this.on_create = params.on_create;
            this.hasButtons = params.hasButtons;
        },
        /**
         * @private
         * @param {Widget} kanbanRecord
         * @param {Object} params
         */
        _reloadAfterButtonClick: function (kanbanRecord, params) {
            var self = this;
            var recordModel = this.model.localData[params.record.id];
            var group = this.model.localData[recordModel.parentID];
            var parent = this.model.localData[group.parentID];

            this.model.reload(params.record.id).then(function (db_id) {
                var data = self.model.get(db_id);
                kanbanRecord.update(data);

                // Check if we still need to display the record. Some fields of the domain are
                // not guaranteed to be in data. This is for example the case if the action
                // contains a domain on a field which is not in the Kanban view. Therefore,
                // we need to handle multiple cases based on 3 variables:
                // domInData: all domain fields are in the data
                // activeInDomain: 'active' is already in the domain
                // activeInData: 'active' is available in the data

                var domain = (parent ? parent.domain : group.domain) || [];
                var domInData = _.every(domain, function (d) {
                    return d[0] in data.data;
                });
                var activeInDomain = _.pluck(domain, 0).indexOf('active') !== -1;
                var activeInData = 'active' in data.data;

                // Case # | domInData | activeInDomain | activeInData
                //   1    |   true    |      true      |      true     => no domain change
                //   2    |   true    |      true      |      false    => not possible
                //   3    |   true    |      false     |      true     => add active in domain
                //   4    |   true    |      false     |      false    => no domain change
                //   5    |   false   |      true      |      true     => no evaluation
                //   6    |   false   |      true      |      false    => no evaluation
                //   7    |   false   |      false     |      true     => replace domain
                //   8    |   false   |      false     |      false    => no evaluation

                // There are 3 cases which cannot be evaluated since we don't have all the
                // necessary information. The complete solution would be to perform a RPC in
                // these cases, but this is out of scope. A simpler one is to do a try / catch.

                if (domInData && !activeInDomain && activeInData) {
                    domain = domain.concat([
                        ['active', '=', true]
                    ]);
                } else if (!domInData && !activeInDomain && activeInData) {
                    domain = [
                        ['active', '=', true]
                    ];
                }
                console.log('domain', domain)
                console.log('activeInDomain', activeInDomain)
                try {
                    var visible = new Domain(domain).compute(data.evalContext);
                } catch (e) {
                    return;
                }
                if (!visible) {
                    kanbanRecord.destroy();
                }
            });
        },
        /**
         * @private
         * @param {OdooEvent} event
         */
        _onButtonClicked: function (event) {
            event.stopPropagation();
            var attrs = event.data.attrs;
            var record = event.data.record;
            if (attrs.context) {
                attrs.context = new Context(attrs.context)
                    .set_eval_context({
                        active_id: record.res_id,
                        active_ids: [record.res_id],
                        active_model: record.model,
                    });
            }
            this.trigger_up('execute_action', {
                action_data: attrs,
                env: {
                    context: record.getContext(),
                    currentID: record.res_id,
                    model: record.model,
                    resIDs: record.res_ids,
                },
                on_closed: this._reloadAfterButtonClick.bind(this, event.target, event.data),
            });
        },
        /**
         * @todo should simply use field_changed event...
         *
         * @private
         * @param {OdooEvent} ev
         */
        /**
         * The interface allows in some case the user to archive a column. This is
         * what this handler is for.
         *
         * @private
         * @param {OdooEvent} event
         */
        _onArchiveRecords: function (event) {
            var self = this;
            var active_value = !event.data.archive;
            var column = event.target;
            var record_ids = _.pluck(column.records, 'db_id');
            if (record_ids.length) {
                this.model
                    .toggleActive(record_ids, active_value, column.db_id)
                    .then(function (db_id) {
                        var data = self.model.get(db_id);
                        self._updateEnv();
                    });
            }
        },
        _onChangeFilter: function (event) {
            console.log(event);
            this.reload();
        },
        /**
         * @private
         * @param {OdooEvent} event
         */
        _onRecordDelete: function (event) {
            this._deleteRecords([event.data.id]);
        },
        _onUpdateRecord: function (ev) {
            var changes = _.clone(ev.data);
            ev.data.force_save = true;
            this._applyChanges(ev.target.db_id, changes, ev);
        },
        renderButtons: function ($node) {
            if (this.hasButtons) {
                this.$buttons = $(qweb.render('MapView.buttons', {
                    widget: this
                }));

                if (this.viewType === 'route') {
//                    this.$buttons.on('click', 'button.o-map-button-load-data', this._onSubmit.bind(this));
                    this.$buttons.find('button.o-map-button-new').css({"display": "none"});
                    this.$buttons.find('button.o-map-button-center-map').css({"display": "none"});
                    this.$buttons.find('button.o-map-button-alert-map').css({"display": "none"});
                } else {
                    this.$buttons.find('.search-form').css({"display": "none"});
                    this.$buttons.on('click', 'button.o-map-button-new', this._onButtonNew.bind(this));
                    this.$buttons.on('click', 'button.o-map-button-center-map', this._onButtonMapCenter.bind(this));
                    this.$buttons.on('click', 'button.o-map-button-alert-map', this._onButtonAlert.bind(this));
                    // this.$buttons.on('click', 'button.o-map-button-report', this._onButtonShowReport.bind(this));
                }
                this.$buttons.appendTo($node);
            }
        },
        _onButtonShowReport: function (events) {
            event.stopPropagation();
            this.renderer._showReport();
        },
        _onButtonMapCenter: function (event) {
            window.isClickVehicle = false //set lại vehicle k được chọn để view all vehicle
            this.renderer._showAllVehicle()
            event.stopPropagation();
            if (this.renderer.mapLibrary === 'geometry') {
                this.renderer.mapGeometryCentered();
            } else if (this.renderer.mapLibrary === 'drawing') {
                this.renderer.mapShapesCentered();
            }
        },
        _onButtonNew: function (event) {
            event.stopPropagation();
            this.trigger_up('switch_view', {
                view_type: 'form',
                res_id: undefined
            });
        },
        _onButtonAlert: function (event) {
            alert("ko click");
        },
        _onSubmit: function (event) {
            console.log(event.data)
            const element = this.$buttons.find('input.o_map_from_date').get();
            console.log(element[0].value, element[1].value)
            console.log('_onSubmit', this)
            console.log('_onSubmit', this.model)
            options.domain = [];
            if (element[0].value !== undefined && element[0].value !== '') options.domain.push(['create_date', '>=', element[0].value]);
            if (element[1].value !== undefined && element[1].value !== '') options.domain.push(['create_date', '<', element[1].value]);
            console.log(options)
            this.model.reload(this.handle, options)
        },
    });

    return MapController;
});