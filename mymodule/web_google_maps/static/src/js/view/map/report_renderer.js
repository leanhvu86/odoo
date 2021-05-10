odoo.define('web_google_maps.ReportRenderer', function (require) {
    'use strict';

    var BasicRenderer = require('web.BasicRenderer');
    var core = require('web.core');
    var QWeb = require('web.QWeb');
    var session = require('web.session');
    var utils = require('web.utils');
    var Widget = require('web.Widget');
    var KanbanRecord = require('web.KanbanRecord');

    var qweb = core.qweb;

    var session = require('web.session');

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

    var ReportRenderer = BasicRenderer.extend({
        className: 'o_report_view',
        template: 'ReportView.ReportView',
        /**
         * @override
         */
        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            this.widgets = [];

            this.qweb = new QWeb(session.debug, {
                _s: session.origin
            }, false);
            var templates = findInNode(this.arch, function (n) {
                return n.tag === 'templates';
            });
            this.recordOptions = _.extend({}, params.record_options, {
                qweb: this.qweb,
                viewType: 'report',
            });
            this.state = state;
            this.shapesCache = {};
        },
        start: function () {
            console.log("render Initial App");
            this._initReport();
            return this._super();
        },

        /**
         * Initialize report
         * @private
         */
        _initReport: function () {
            var message_key = self.btoa('' + ';' + session.user_id);
            console.log('_blank', session)
            var report = this._rpc({
                route: '/power-bi/embed',
                method: 'search_read',
                params: {},
            }).then(result => {
                    console.log(result)
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
                    var reportContainer = this.$('#reportView')[0];
                    // Embed the report and display it within the div container.
                    var report = powerbi.embed(reportContainer, config);
                }
            )

            // this.$('.o_report_view').append(
            //     $('<iframe  allow="camera *;microphone *" frameborder="0" width="100%"  height="600" src="https://chat.aggregatoricapaci.com/#/home"/>')
            // );
        },

    });

    return ReportRenderer;

});