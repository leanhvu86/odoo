odoo.define('web_widget_timepicker', function (require) {
    'use strict';

    var field_registry = require('web.field_registry');
    var field_utils = require('web.field_utils');
    var basic_fields = require('web.basic_fields');
    var datepicker = require('web.datepicker');
    var FieldDate = basic_fields.FieldDate;


    var TimeWidget = datepicker.DateWidget.extend({
        type_of_date: "float_time",

        _onShow: function () {
            if (this.$input.val().length !== 0 && this.isValid()) {
                var value = this.$input.val();
                this.picker.date(new moment(value, this.options.format));
                this.$input.select();
            }

             console.log("getValue",formatted_value);
        },

        setValue: function (value) {

             console.log("setValue",formatted_value);
            this.set({'value': value});
            var formatted_value = value ? this._formatClient(value) : null;
            console.log("Affter formated",formatted_value);
            this.$input.val(formatted_value);
            if (this.picker) {
                var fdate = new moment(formatted_value, this.options.format);
                this.picker.date(fdate && fdate.isValid()
                    ? fdate : new moment());
            }
        },

        getValue: function () {
            var value = this.get('value');
             console.log("getValue",value);
            return value ? this._formatClient(value) : null;
        },

        changeDatetime: function () {
            console.log("changeDatetime");
            if (this.isValid()) {
                var oldValue = this.getValue();
                if(oldValue == null){
                    oldValue = 0;
                }
                this._setValueFromUi();
                var newValue = this.getValue();
                this.trigger_up("datetime_changed");
            }
        },
    });

    var FieldTimePicker = FieldDate.extend({
        supportedFieldTypes: ['float'],
        floatTimeFormat: "HH:mm",

        init: function () {
            this._super.apply(this, arguments);
            var defDate = null;
            if (this.value) {
                defDate = new moment(this._formatValue(this.value),
                    this.floatTimeFormat);
            }
            // Hard-Coded Format: Field is an float and conversion only accept
            // HH:mm format
            this.datepickerOptions = _.extend(this.datepickerOptions, {
                format: this.floatTimeFormat,
                defaultDate: defDate && defDate.isValid()
                    ? defDate : new moment(),
            });
        },

        _isSameValue: function (value) {
            return value === this.value;
        },

        _makeDatePicker: function () {
            return new TimeWidget(this, this.datepickerOptions);
        },

        _formatValue: function (value) {
            return field_utils.format.float_time(value);
        },

        _parseValue: function (value) {
            return field_utils.parse.float_time(value);
        },
    });

    field_registry.add('timepicker', FieldTimePicker);
    return {
        TimeWidget: TimeWidget,
        FieldTimePicker: FieldTimePicker,
    };
});