import logging

from odoo import models

logger = logging.getLogger(__name__)


class Hub(models.Model):
    _name = 'sharevan.hub'
    _inherit = 'sharevan.hub'
    _description = 'hub'
