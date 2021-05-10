from mymodule.base_next.controllers.api.file_controller import FileApi
from mymodule.share_van_order.models.bill_package_routing import BillPackageRoutingPlan
from odoo import models, api, fields, http
from odoo.addons.base.models.ir_attachment import IrAttachment

INSERT_QUERY = "INSERT INTO ir_attachment_sharevan_bill_package_routing_plan_rel " \
               " VALUES ( %s , %s ) "

class BillPackageRoutingImport(models.Model):
    _name = 'sharevan.bill.package.routing.import'
    _description = 'bill package routing when import'
    _inherit = 'sharevan.bill.package.routing.import'

    routing_plan_code = fields.Char('Routing code')
    name = fields.Char('Name code')
    routing_package_plan = fields.Many2one('sharevan.bill.package.routing.plan', 'Routing Package plan')
    qr_code = fields.Image("Image", max_width=512, max_height=512, relate='routing_package_plan.qr_code')
    qr_char_confirms = fields.Char(string = "List char comfirm")


    @api.model
    def create(self, vals):
        if vals.get('name_seq', 'New') == 'New':
            name_seq = self.env['ir.sequence'].next_by_code(
                'self.sharevan.bill.package.plan') or 'New'
            qr_code = FileApi.build_qr_code(name_seq)
            # plan = {
            #     'routing_plan_day_id': vals['routing_plan_day_id'],
            #     'product_type_id': vals['product_type_id'],
            #     'total_weight': vals['total_weight'],
            #     'quantity': vals['quantity_import'],
            #     'item_name': vals['item_name'],
            #     'length': vals['length'],
            #     'width': vals['width'],
            #     'height': vals['height'],
            #     'capacity': vals['capacity'],
            #     'qr_code': qr_code,
            #     'name': name_seq,
            #     'note': vals['note'],
            #     'qr_char': name_seq
            # }
            # result = http.request.env[BillPackageRoutingPlan._name].create(plan)
            # val = {
            #     'res_model': 'sharevan.bill.package.routing.plan',
            #     'name': name_seq,
            #     'res_id': 0,
            #     # 'company_id': routingPlan['company_id'],
            #     'type': 'binary',
            #     'datas': FileApi.build_qr_code(name_seq)
            # }
            # rec = http.request.env[IrAttachment._name].create(val)
            # http.request.cr.execute(INSERT_QUERY, (result['id'], rec['id'],))
            # vals['routing_package_plan'] = result['id']
            vals['qr_char'] = name_seq
            vals['name'] = name_seq
        res = super(BillPackageRoutingImport, self).create(vals)
        return res

