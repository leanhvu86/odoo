odoo.define('web_widget_time_countdown.TimeDelta', function (require) {
    "use strict";

    var field_registry = require('web.field_registry');
    var fields = require('web.basic_fields');

    var core = require('web.core');
    var _t = core._t;
    var FieldTimeCountDown = fields.FieldChar.extend({
        template: 'FieldCountDown',
        widget_class: 'oe_form_field_time_delta',

        init: function () {
            console.log('12313')
            this._super.apply(this, arguments);
            // console.log(this.value.format('DD-MM-YYYY HH:mm:ss'))

        },

        _renderReadonly: function () {
                        console.log('12313')
            var date = this.value.toDate()
            var countDownDate = new Date(date).getTime();
            var parentThis = this;
            setInterval(function () {
                    var now = new Date().getTime();
                    //   Find the distance between now and the count down date
                    var distance = countDownDate - now;

                    // Time calculations for days, hours, minutes and seconds
                    var days = Math.floor(distance / (1000 * 60 * 60 * 24));
                    var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                    var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                    var seconds = Math.floor((distance % (1000 * 60)) / 1000);
                    var viewTime = days.toString() + "d " + hours.toString() + "h " + minutes.toString() + "m " + seconds.toString() + "s ";
                    if (distance < 0) {
                        viewTime = "EXPIRED"
                    }
                    parentThis.$el.text(viewTime);
                }, 1000
            )
        }
    });

    var FieldMinuteCountUp = fields.FieldChar.extend({
        template: 'FieldCountMinuteUp',
        widget_class: 'oe_form_field_time_delta',
        init: function () {
            console.log('12312')
            this._super.apply(this, arguments);
            // console.log(this.value.format('DD-MM-YYYY HH:mm:ss'))
        },

        _renderReadonly: function () {
            console.log('123131')
            var date = this.value.toDate()
            var countDownDate = new Date(date).getTime();
            var parentThis = this;
            console.log('longdeptrai')
            parentThis.$el.text('longdeptrai');
        }
    });

    field_registry
        .add('time_countdown', FieldTimeCountDown)
        .add('count_minute', FieldMinuteCountUp);
    return {
        FieldTimeCountDown: FieldTimeCountDown,
        FieldMinuteCountUp: FieldMinuteCountUp
    };

});