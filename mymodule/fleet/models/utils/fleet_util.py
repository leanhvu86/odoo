from odoo import models, fields


class FleetVehicleState(models.Model):
    _name = 'fleet.vehicle.state'
    _order = 'sequence asc'
    _description = 'Vehicle Status'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(help="Used to order the note stages")
    code = fields.Char()
    _sql_constraints = [('fleet_state_name_unique', 'unique(name)', 'State name already exists')]

    @staticmethod
    def get_id_by_code(self, code):
        stage = self.env['fleet.vehicle.state'].search([('code', '=', code)], limit=1)
        if stage:
            return stage.id