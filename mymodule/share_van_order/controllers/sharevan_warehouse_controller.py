from odoo import http


class SharevanWarehouseController(http.Controller):

    @http.route('/sharevan_warehouse/template/xlsx', type='http', auth='public')
    def export_warehouse_xlsx(self):
        return http.request.env['sharevan.warehouse'].get_template()
