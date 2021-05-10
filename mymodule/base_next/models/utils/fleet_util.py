import random

from odoo import models, fields


def luhn_residue(digits):
    return sum(sum(divmod(int(d) * (1 + i % 2), 10))
               for i, d in enumerate(digits[::-1])) % 10


def get_imei():
    part = ''.join(str(random.randrange(0, 9)) for _ in range(15))
    res = luhn_residue('{}{}'.format(part, 0))
    return '{}{}'.format(part, -res % 10)


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
