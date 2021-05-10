# -*- coding: utf-8 -*-
from mymodule.share_van_order.controllers.api.base import BaseApi
from odoo import http


class BillPackageApi:
    MODEL = 'sharevan.bill.package'

    @staticmethod
    def create_bill_package(billPackage):
        instance = BaseApi.getInstance(BillPackageApi.MODEL, billPackage)

        return http.request.env[BillPackageApi.MODEL].create(instance)

# @staticmethod
# def create_bill_lading_detail(self, detail):
