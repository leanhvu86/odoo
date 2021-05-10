import logging

from odoo import models

logger = logging.getLogger(__name__)

class RoutingPlanDayService(models.Model):
    _name = 'sharevan.routing.plan.day.service'
    _description = 'routing plan day service'
    _inherit = 'sharevan.routing.plan.day.service'
