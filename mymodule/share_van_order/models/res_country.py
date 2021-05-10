from odoo import models, _, http, fields

class Country(models.Model):
    _name = 'res.country'
    MODEL = 'res.country'
    _description = 'Country'
    _inherit = 'res.country'

    status = fields.Selection([('running', 'Running'),
                               ('deleted', 'Deleted')], 'Status', default="running",
                              help=' 1:running , 2:deleted')

    def unlink(self):
        for id in self.ids:
            record = self.env['res.country'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })
        return self