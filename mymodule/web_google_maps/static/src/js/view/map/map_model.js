odoo.define('web_google_maps.MapModel', function(require) {
    'use strict';

    var BasicModel = require('web.BasicModel');

    var MapModel = BasicModel.extend({

        /**
         * @override
         */
        reload: function (id, options) {
             console.log('reload ...MapModel id =',id , 'option ==', options);
            if (options && options.groupBy && !options.groupBy.length) {
                options.groupBy = this.defaultGroupedBy;
            }
            return this._super.apply(this, arguments);
        },
        /**
         * @override
         */
        load: function (params) {
            console.log('Load....MapModel',params);
            this.defaultGroupedBy = params.groupBy;
            params.groupedBy = (params.groupedBy && params.groupedBy.length) ? params.groupedBy : this.defaultGroupedBy;
            return this._super(params);
        },
        /**
         * Ensures that there is no nested groups in Map (only the first grouping
         * level is taken into account).
         *
         * @override
         */
        _readGroup: function (list) {
            console.log('read Group list', list);
            var self = this;
            if (list.groupedBy.length > 1) {
                list.groupedBy = [list.groupedBy[0]];
            }
            return this._super.apply(this, arguments);
        }
    });

    return MapModel;

});
