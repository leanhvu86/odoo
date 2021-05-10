# -*- coding: utf-8 -*-

from odoo import http
from mymodule.base_next.models.bidding_vehicle import BiddingVehicle
from mymodule.constants import Constants
from mymodule.constants.Constants import RES_PARTNER
from mymodule.share_van_order.controllers.api.bidding_order_api import BiddingOrderApi
from odoo import http
from odoo.http import request

class DistanceComputeController(http.Controller):
    def test(self):
        print()