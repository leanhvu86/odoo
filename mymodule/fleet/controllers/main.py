from addons.web.controllers import main
from odoo import http, tools
from odoo.exceptions import ValidationError
from odoo.http import content_disposition, dispatch_rpc, request, serialize_exception as _serialize_exception, Response
import json
import operator

from odoo import http
from odoo.http import content_disposition, request
from .. import models

class ExportFormat(object):

    def content_type(self):
        """ Provides the format's content type """
        raise NotImplementedError()

    def filename(self, base):
        """ Creates a valid filename for the format (with extension) from the
         provided base name (exension-less)
        """
        raise NotImplementedError()

    def from_data(self, fields, rows):
        """ Conversion method from Odoo's export data to whatever the
        current export class outputs

        :params list fields: a list of fields to export
        :params list rows: a list of records to export
        :returns:
        :rtype: bytes
        """
        print("test pápmasg")

    def from_group_data(self, fields, groups):
        raise NotImplementedError()

    def base(self, data, token):
        params = json.loads(data)
        model, fields, ids, domain, import_compat = \
            operator.itemgetter('model', 'fields', 'ids', 'domain', 'import_compat')(params)

        field_names = [f['name'] for f in fields]
        if import_compat:
            columns_headers = field_names
        else:
            columns_headers = [val['label'].strip() for val in fields]

        Model = request.env[model].with_context(**params.get('context', {}))
        Model = Model.with_context(import_compat=import_compat)
        records = Model.browse(ids) if ids else Model.search(domain, offset=0, limit=False, order=False)
        export_data = records.export_data(field_names).get('datas', [])
        response_data = self.from_data(columns_headers, export_data)
        return request.make_response(response_data,
                                     headers=[('Content-Disposition',
                                               content_disposition(self.filename(model))),
                                              ('Content-Type', self.content_type)],
                                     cookies={'fileToken': token})


class ExcelExport(ExportFormat, http.Controller):
    @http.route('/fleet_vehicle/template/xlsx', type='json', auth="user")
    def download_template(self, data):
        print(data)


class FleetDriver(http.Controller):

    @http.route('/fleet_vehicle/get_driver_schedule', type='json', auth="user")
    def get_driver_schedule(self, **kwargs):
        driver_id = None
        from_date = None
        to_date = None
        for arg in kwargs:
            if arg == 'driver_id':
                driver_id = kwargs.get(arg)
            if arg == 'from_date':
                from_date = kwargs.get(arg)
            if to_date == 'to_date':
                to_date = kwargs.get(arg)
        records = http.request.env['fleet.vehicle.assignation.log']. \
            web_search_read([['driver_id', '=', driver_id],
                             ['date_start', '>=', from_date], ['date_end', '<=', to_date]],
                            fields=None, offset=0, limit=10, order='')
        return records

