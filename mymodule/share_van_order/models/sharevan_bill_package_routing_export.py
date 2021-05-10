from odoo import models, api, fields


class BillPackageRoutingExport(models.Model):
    _name = 'sharevan.bill.package.routing.export'
    MODEL = 'sharevan.bill.package.routing.export'
    _description = 'bill package routing when export'
    _inherit = 'sharevan.bill.package.routing.export'

    routing_package_plan = fields.Many2one('sharevan.bill.package.routing.plan', 'Routing Package plan')
    qr_code = fields.Image("Image", max_width=512, max_height=512, relate='routing_package_plan.qr_code')
    qr_char_confirms = fields.Char(string = "List char comfirm")


    @api.model
    def create(self, vals):
        # vals['qr_char'] = vals['routing_package_plan'].qr_char
        res = super(BillPackageRoutingExport, self).create(vals)
        return res


