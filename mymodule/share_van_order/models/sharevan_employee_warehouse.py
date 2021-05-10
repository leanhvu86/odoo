import logging

from odoo import models

logger = logging.getLogger(__name__)


class EmployeeWorkingCalendar(models.Model):
    _name = 'sharevan.employee.warehouse'
    _description = 'employee warehouse calendar'
    _inherit = 'sharevan.employee.warehouse'