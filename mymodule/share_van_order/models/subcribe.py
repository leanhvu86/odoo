# -*- coding: utf-8 -*-

from odoo import models


class Subscribe(models.Model):
    _name = "sharevan.subscribe"
    _description = 'Subscribe the bill of lading regularly'
    _order = 'subscribe_code'
    _inherit = "sharevan.subscribe"

class DriverAssignRouting(models.Model):
    _name = 'sharevan.driver.assign.routing'
    _inherit = 'sharevan.driver.assign.routing'
    _description = 'Driver assign routing in market place'
