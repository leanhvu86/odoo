from copy import deepcopy
from datetime import datetime
from datetime import timedelta

import googlemaps
import json as simplejson

from mymodule.base_next.controllers.api.base_method import BaseMethod
from mymodule.base_next.controllers.api.file_controller import FileApi
from mymodule.base_next.models.warehouse import Warehouse
from mymodule.constants import Constants
from mymodule.enum.AreaDistanceType import AreaDistanceType
from mymodule.enum.ClickActionType import ClickActionType
from mymodule.enum.MessageType import MessageType
from mymodule.enum.NotificationType import NotificationType
from mymodule.enum.RoutingDetailStatus import RoutingDetailStatus
from mymodule.enum.VehicleStatusAvailable import ProductType
from mymodule.enum.WarehouseType import WarehouseType
from mymodule.share_van_order.controllers.api import billing
from mymodule.share_van_order.controllers.api.base import BaseApi
from odoo import models, api, fields, _, http
from odoo.exceptions import ValidationError, UserError
from copy import copy
from datetime import date

# import datetime


try:
    import qrcode
except ImportError:
    qrcode = None
try:
    import base64
except ImportError:
    base64 = None
from io import BytesIO


class BillLading(models.Model):
    _name = 'sharevan.bill.lading'
    MODEL = 'sharevan.bill.lading'
    _description = 'bill of lading'

    name_seq = fields.Char(string='Bill of lading Code', required=True, copy=False, readonly=True,
                           index=True,
                           default=lambda self: _('New'))
    insurance_id = fields.Many2one('sharevan.insurance', 'Insurance', domain=[('status', '=', 'running')])
    total_weight = fields.Float('Total weight')
    total_amount = fields.Float('Provisional amount', default=0)
    startDateStr = fields.Char('startDateStr', store=False)
    tolls = fields.Float('Tolls')
    surcharge = fields.Float('Surcharge')
    total_volume = fields.Float('Total volume')
    vat = fields.Float('VAT(%)', digits=(2, 1))
    promotion_code = fields.Float('Promotion code')
    release_type = fields.Integer('Release type')
    total_parcel = fields.Integer('Total parcel')
    company_id = fields.Many2one('res.company', 'Customer', default=lambda self: self.env.company.id,
                                 domain=[('company_type', 'in', ('1', '2'))])
    award_company_id = fields.Many2one('sharevan.title.award', 'Award', index=True, domain=[('status', '=', 'running')])
    bill_lading_detail_ids = fields.One2many('sharevan.bill.lading.detail', 'bill_lading_id',
                                             string='Bill of lading detail', domain=[('status_order', '=', 'running')])
    start_date = fields.Date('Start Date', default=fields.Date.today(), required=True)
    end_date = fields.Date('End Date', default=fields.Date.today(), required=True)
    subscribe_id = fields.Many2one('sharevan.subscribe', 'Subscribe', index=True, domain=[('status', '=', 'running')])
    # subscribe = fields.Char('Subscribe code', related='recurrent_id.subscribe_id.name', store=False, readOnly=True)
    # field for view
    cycle_type = fields.Selection(
        [('1', 'Hàng ngày'), ('2', 'Hàng tuần'), ('3', 'Hàng tháng'), ('4', 'Giao nhanh'),
         ('5', 'Một lần')], 'Cycle type',
        default='5', required=True)
    week_choose = fields.Selection(
        [('0', 'Chủ nhật'), ('1', 'Thứ hai'), ('2', 'Thứ ba'),
         ('3', 'Thứ tư'), ('4', 'Thứ năm'), ('5', 'Thứ sáu'), ('6', 'Thứ bảy')], 'Week choose',
        default='1', store=False, compute="_compute_week_choose")
    chooseDay = fields.Date(default=datetime.today(), string="Choose date", store=False)
    # end declare for view

    # trường vô dụng để view

    day_of_week_view = fields.Selection(
        [('0', 'Chủ nhật'), ('1', 'Thứ hai'), ('2', 'Thứ ba'),
         ('3', 'Thứ tư'), ('4', 'Thứ năm'), ('5', 'Thứ sáu'), ('6', 'Thứ bảy')], 'Day Of Week',
        default='1', store=False,compute="_compute_day_of_week_view")

    frequency = fields.Integer(string='Frequency', default=5)
    qr_code = fields.Char(string='SO code')
    sbl_type = fields.Selection(
        [('DLP', 'DLP'), ('SO', 'SO')], 'Sbl type',
        default='DLP')
    day_of_week = fields.Integer(string='Day Of Week', default=0)
    day_of_month = fields.Integer(string='Day In Month', default=0)
    status = fields.Selection(
        [('running', 'Active'),
         ('deleted', 'Deactivated'),
         ('draft', 'Draft'),
         ('finished', 'Finished')],
        string='Status', context={'status': 'running'}, default='running', required=True)
    description = fields.Text('Description', default=' ')

    name = fields.Char(string='Bill of Lading Reference', required=True, copy=False, readonly=True,
                       index=True,
                       default=lambda self: _('New'))
    from_bill_lading_id = fields.Many2one('sharevan.bill.lading', 'From bill of lading', index=True)
    last_scan = fields.Datetime('Last scan')
    order_num = fields.Integer("Order num")
    total_service_amount = fields.Float('')
    total_insurance_amount = fields.Float('')
    total_amount_actual = fields.Float('')
    export_weight = 0.0
    export_volume = 0.0
    # doninzone||outzone
    inzone_num = fields.Integer('total bill of lading type inzone', default=0)
    outzone_num = fields.Integer('total bill of lading type outzone', default=0)
    price_not_discount = fields.Float("Price before discount")
    insurance_price = fields.Float("Insurance price")
    service_price = fields.Float("Service price")
    reason = fields.Selection(
        [('1', 'Customer not found'), ('2', 'Order package change'),
         ('3', 'Customer cancel'), ('4', 'System not satisfy')],
        string='Reason')

    @api.model
    def create(self, vals):
        vals['award_company_id'] = self.env.company.award_company_id.id
        if 'sbl_type' in vals and vals['sbl_type'] == "SO":
            list_bill_package = vals['bill_lading_detail_ids'][0][2]['bill_package_line']
            len_bill_package = len(list_bill_package)
            del_package = []
            next_id = []
            start = 1
            index = 0
            for bill in list_bill_package:
                if index in next_id:
                    start += 1
                    index += 1
                else:
                    for x in range(start, len_bill_package):
                        if bill[2]['product_type_id'] == list_bill_package[x][2]['product_type_id'] and \
                                bill[2]['net_weight'] == list_bill_package[x][2]['net_weight'] and \
                                bill[2]['length'] == list_bill_package[x][2]['length'] and \
                                bill[2]['width'] == list_bill_package[x][2]['width'] and \
                                bill[2]['height'] == list_bill_package[x][2]['height'] and \
                                bill[2]['item_name'] == list_bill_package[x][2]['item_name'] and \
                                bill[2]['commodities_type'] == list_bill_package[x][2]['commodities_type']:
                            bill[2]['quantity_package'] = bill[2]['quantity_package'] + list_bill_package[x][2][
                                'quantity_package']
                            next_id.append(x)
                    start += 1
                    index += 1
                    del_package.append(bill)
                    if start == len_bill_package + 1:
                        break
            list_bill_package = vals['bill_lading_detail_ids'][0][2]['bill_package_line'] = del_package
            list_bill_package = vals['bill_lading_detail_ids'][1][2]['bill_package_line'] = del_package
        else:
            vals['sbl_type'] = 'DLP'
        if 'subscribe_id' not in vals or vals['subscribe_id'] is False:
            vals['end_date'] = vals['start_date']
        else:
            search_res = self.env['sharevan.subscribe'].search([('id', '=', vals['subscribe_id'])])
            sub_value = search_res[0]['value']
            start_date = vals['start_date']
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            vals['end_date'] = start_date + timedelta(days=sub_value - 1)
        self._validate_create(vals)
        if vals.get('name_seq', 'New') == 'New':
            vals['name'] = BaseMethod.get_new_sequence('sharevan.bill.lading', 'SBL', 12, 'name_seq')
            vals['name_seq'] = vals['name']
            c_type = vals.get('cycle_type')
            if c_type == '1':
                vals['frequency'] = 1
                vals['day_of_week'] = 0
                vals['day_of_month'] = 0
            elif c_type == '2':
                vals['frequency'] = 2
                vals['day_of_week'] = int(vals.get('week_choose'))
                vals['day_of_month'] = 0
            elif c_type == '3':
                vals['frequency'] = 3
                vals['day_of_week'] = 0
            elif c_type in {'4', '5'}:
                vals['day_of_month'] = 0
                vals['day_of_week'] = 0
                vals['end_date'] = vals['start_date']
        need_cal = False
        if 'need_cal' in vals:
            need_cal = True
            del vals['need_cal']
            for detail in vals['bill_lading_detail_ids']:
                if 'areaDistances' in detail[2]:
                    detail[2].pop('areaDistances')
        vals['order_num'] = self._count_bols(vals)
        print('order_num: ', vals['order_num'])
        if 'frequency' in vals:
            vals['cycle_type'] = str(vals['frequency'])
        else:
            vals['frequency'] = 5
            vals['cycle_type'] = '5'
        result = super(BillLading, self).create(vals)
        # move this here to make it independent from calc_price
        if result:
            result._set_from_bldd_id()
        if need_cal:
            result.calc_price(vals)
        result.send_notification_success()
        return result

    def week_check(self, x):
        switcher = {
            0: 1,
            1: 2,
            2: 3,
            3: 4,
            4: 5,
            5: 6,
            6: 0
        }
        return switcher.get(x, 0)

    def _count_bols(self, vals):
        dem = 0
        date_check = datetime.strptime('2020-01-01', '%Y-%m-%d').date()
        print("start_date: ", vals['start_date'])
        print(type(vals['start_date']))
        print(type(vals['end_date']))
        x = str(vals['start_date'])
        y = str(vals['end_date'])
        x = x[0:10]
        y = y[0:10]
        print(type(x))
        print(type(y))
        start_date = datetime.strptime(x, '%Y-%m-%d').date()
        end_date = datetime.strptime(y, '%Y-%m-%d').date()
        day_of_week = None
        day_of_month = None
        if 'day_of_week' in vals:
            day_of_week = vals['day_of_week']
        if 'day_of_month' in vals:
            day_of_month = vals['day_of_month']
        # lay nam/thang/ngay cua start_date
        year_start = start_date.year
        month_start = start_date.month
        day_start = start_date.day
        # lay nam/thang/ngay cua end_date
        year_end = end_date.year
        month_end = end_date.month
        day_end = end_date.day
        if 'frequency' not in vals or vals['frequency'] in (4, 5):
            dem = 1
        elif vals['frequency'] == 1:
            d0 = date(year_start, month_start, day_start)
            d1 = date(year_end, month_end, day_end)
            count = (d1 - d0)
            dem = count.days + 1
        elif vals['frequency'] == 2:
            check = (start_date <= end_date)
            while check == True:
                day_check = start_date.weekday()
                day_check = self.week_check(day_check)
                if day_check == day_of_week:
                    dem = 1
                    break
                else:
                    start_date = start_date + timedelta(days=1)
                #   start_date = start_date + 1
                check = (start_date <= end_date)
            start_date = start_date + timedelta(days=7)
            # start_date = start_date + 7
            check = start_date <= end_date
            while check == True:
                dem = dem + 1
                start_date = start_date + timedelta(days=7)
                check = (start_date <= end_date)
        elif vals['frequency'] == 3:
            if year_end > year_start:
                while month_start <= 12:
                    date_check_str = str(year_start) + "-" + str(month_start) + "-" + str(day_of_month)
                    isValidDate = True
                    try:
                        date_check = datetime.strptime(str(date_check_str), "%Y-%m-%d").date()
                    except ValueError:
                        isValidDate = False
                    if isValidDate:
                        check = (date_check >= start_date)
                        print(check)
                        if check:
                            dem = dem + 1
                    month_start = month_start + 1
                year_start = year_start + 1
                while year_start < year_end:
                    if day_of_month < 29:
                        dem += 12
                    elif day_of_month == 29:
                        date_check_str = str(year_start) + "-02" + "-" + str(day_of_month)
                        isValidDate = True
                        try:
                            date_check = datetime.strptime(str(date_check_str), "%Y-%m-%d").date()
                        except ValueError:
                            isValidDate = False
                        if isValidDate:
                            dem += 12
                        else:
                            dem += 11
                    elif day_of_month == 30:
                        dem += 11
                    elif day_of_month == 31:
                        dem += 7
                    year_start = year_start + 1
                isValidDate = True
                date_check_str = str(year_end) + "-" + str(month_end) + "-" + str(day_of_month)
                try:
                    date_check = datetime.strptime(str(date_check_str), "%Y-%m-%d").date()
                except ValueError:
                    isValidDate = False
                if isValidDate:
                    check = (date_check < end_date)
                    print(check)
                    if check == True:
                        dem = dem + 1
                month_end = month_end - 1
                while month_end >= 1:
                    isValidDate = True
                    #    date_check_str = str(day_of_month) + "-" + str(month_end) + "-" + str(year_end)
                    date_check_str = str(year_end) + "-" + str(month_end) + "-" + str(day_of_month)
                    try:
                        date_check = datetime.strptime(str(date_check_str), "%Y-%m-%d").date()
                    except ValueError:
                        isValidDate = False
                    if isValidDate:
                        dem = dem + 1
                    month_end = month_end - 1
            elif year_end == year_start:
                date_check_str = str(year_end) + "-" + str(month_start) + "-" + str(day_of_month)
                isValidDate = True
                try:
                    date_check = datetime.strptime(str(date_check_str), "%Y-%m-%d").date()
                except ValueError:
                    isValidDate = False
                if isValidDate:
                    check = (date_check >= start_date)
                    if (check == True):
                        dem = dem + 1
                month_start = month_start + 1
                while month_start <= month_end:
                    date_check_str = str(year_end) + "-" + str(month_start) + "-" + str(day_of_month)
                    isValidDate = True
                    try:
                        date_check = datetime.strptime(str(date_check_str), "%Y-%m-%d").date()
                    except ValueError:
                        isValidDate = False
                    if isValidDate:
                        check = date_check <= end_date
                        if check:
                            dem = dem + 1
                    month_start = month_start + 1
        else:
            dem = 1
        return dem

    def write(self, vals):
        if 'subscribe_id' not in vals or vals['subscribe_id'] is False:
            start_date = vals['start_date'] if 'start_date' in vals else str(self.start_date)
            vals['end_date'] = str(datetime.strptime(start_date, "%Y-%m-%d").date())
        elif vals['subscribe_id']:
            search_res = self.env['sharevan.subscribe'].search([('id', '=', vals['subscribe_id'])])
            sub_value = search_res[0]['value']
            start_date = vals['start_date'] if 'start_date' in vals else str(self.start_date)
            vals['end_date'] = str(datetime.strptime(start_date, "%Y-%m-%d").date() + timedelta(days=sub_value - 1))
        self._validate_update(vals)
        need_cal = False
        list_detail = []
        if 'need_cal' in vals:
            need_cal = True
            del vals['need_cal']
            list_detail = vals['bill_lading_detail_ids']
        result = super(BillLading, self).write(vals)
        if result:
            self._set_from_bldd_id()
        if need_cal:
            vals['bill_lading_detail_ids'] = list_detail
            self.calc_price(vals)
        return result

    def _set_from_bldd_id(self):
        from_bld_id = 0
        inzone_num = 0
        outzone_num = 0
        for detail in self.bill_lading_detail_ids:
            if detail.warehouse_type == '0':
                from_bld_id = detail.id
                break
        for detail in self.bill_lading_detail_ids:
            order_type = detail.order_type
            if detail.warehouse_type == '1':
                if order_type == '0':
                    inzone_num += 1
                elif order_type == '1':
                    outzone_num += 1
                super(BillLadingDetail, detail).write({'from_bill_lading_detail_id': from_bld_id})
        super(BillLading, self).write({'inzone_num': inzone_num,
                                       'outzone_num': outzone_num})

    def calc_price(self, vals):
        bldd = self.get_direction(vals)
        bld = self.copy_data()[0]
        bld['bill_lading_detail_ids'] = bldd
        bld['id'] = self.id
        bill_lading_details = self.bill_lading_detail_ids
        res, bill_lading = billing.BillingApi.calc_price(bld)
        if not res:
            raise ValidationError("Price not found!")
        total_amount = bill_lading['total_amount']
        price_not_discount = bill_lading['price_not_discount']
        insurance_price = bill_lading['insurance_price']
        service_price = bill_lading['service_price']
        if isinstance(res, list) and len(res) > 0:
            for re in res:
                # total_amount += re['price']
                for detail in bill_lading_details:
                    if re['billPackages'][0]['bill_lading_detail_id'][0] == detail['id']:
                        param_update = {'price': re['price'], 'min_price': re['price'], 'max_price': re['price']}
                        super(BillLadingDetail, detail).write(param_update)
            # total_amount += self.tolls
            # total_amount += self.surcharge
            # total_amount = (total_amount * (100 + self.vat)) / 100
            super(BillLading, self).write({'total_amount': total_amount,
                                           'price_not_discount': price_not_discount,
                                           'insurance_price': insurance_price,
                                           'service_price': service_price})

    def get_direction(self, vals):
        if 'bill_lading_detail_ids' in vals:
            for bldd in vals['bill_lading_detail_ids']:
                if bldd[2] and 'areaDistances' in bldd[2]:
                    return bldd[2]
        api_key = http.request.env['ir.config_parameter'].sudo().get_param('google.api_key_geocode')
        gmaps = googlemaps.Client(key=api_key)
        now = datetime.now()
        type0_hub = None
        list_detail = []
        from_warehouse = None
        for detail in self.bill_lading_detail_ids:
            if detail.warehouse_type == '0':
                from_warehouse = detail
                from_lat = from_warehouse['latitude']
                from_long = from_warehouse['longitude']
                from_co = str(from_lat) + "," + str(from_long)
                type0_hub = detail.hub_id
                to_lat = type0_hub.latitude
                to_long = type0_hub.longitude
                to_co = str(to_lat) + "," + str(to_long)
                direction_result = gmaps.directions(from_co, to_co,
                                                    mode='driving',
                                                    avoid='ferries',
                                                    departure_time=now)
                if direction_result:
                    areaDistances = self._extract_direction_result(direction_result, 0, from_hub=type0_hub.name_seq)
                    read = {'billPackages': detail.bill_package_line.read(), 'billService': detail.service_id.read(),
                            'warehouse': detail.warehouse_id.read(), 'total_weight': detail.total_weight,
                            'areaDistances': areaDistances, 'warehouse_type': '0', 'express_distance': 1.0}
                    list_detail.append(read)
                break
        for detail in self.bill_lading_detail_ids:
            direction_result = None
            type0_depot = None
            type1_depot = None
            type1_hub = None
            bldd_type = 0
            detail.express_distance = 1.0
            if detail.warehouse_type == '1':
                from_lat = type0_hub.latitude
                from_long = type0_hub.longitude
                from_co = str(from_lat) + "," + str(from_long)
                way_point = []
                type1_hub = detail.hub_id
                # If change these waypoint or AreaDistanceType, change function _extract_direction_result() accordingly
                if type0_hub.id != type1_hub.id and from_warehouse.zone_area_id.id == detail.zone_area_id.id:
                    way_point.append(str(type1_hub.latitude) + "," + str(type1_hub.longitude))
                    bldd_type = 1
                elif type0_hub.id != type1_hub.id:
                    type0_depot = from_warehouse.depot_id
                    type1_depot = detail.depot_id
                    bldd_type = 2
                    if type1_depot.id != type0_depot.id:
                        way_point.append(str(type0_depot.latitude) + "," + str(type0_depot.longitude))
                        way_point.append(str(type1_depot.latitude) + "," + str(type1_depot.longitude))
                        bldd_type = 3
                    way_point.append(str(type1_hub.latitude) + "," + str(type1_hub.longitude))
                to_warehouse = detail
                to_lat = to_warehouse['latitude']
                to_long = to_warehouse['longitude']
                distance_values = FileApi.check_driver_waiting_time(from_warehouse['latitude'],
                                                                    from_warehouse['longitude'], to_lat, to_long)
                if distance_values:
                    detail.express_distance = round(distance_values['cost'] / 1000, 3)
                to_co = str(to_lat) + "," + str(to_long)
                direction_result = gmaps.directions(from_co, to_co, waypoints=way_point,
                                                    mode='driving',
                                                    avoid='ferries',
                                                    departure_time=now)
            if direction_result:
                areaDistances = self._extract_direction_result(direction_result, bldd_type, from_hub=type0_hub.name_seq,
                                                               to_hub=type1_hub.name_seq,
                                                               from_depot=type0_depot.name_seq if type0_depot else "",
                                                               to_depot=type1_depot.name_seq if type1_depot else "")
                read = {'billPackages': detail.bill_package_line.read(), 'billService': detail.service_id.read(),
                        'warehouse': detail.warehouse_id.read(), 'total_weight': detail.total_weight,
                        'areaDistances': areaDistances, 'warehouse_type': '1',
                        'express_distance': detail.express_distance}
                list_detail.append(read)
        return list_detail

    def _extract_direction_result(self, direction_result, type, **kwargs):
        # --- old type, new type = {1,2}
        # index = 1
        # if type in {0, 1}:  # type 0 go from warehouse-hub-warehouse
        #     index = 1
        # if type == 2:
        #     index = 2
        # elif type == 3:
        #     # type 1 go from warehouse-hub-depot-depot-hub-warehouse
        #     # area
        #     index = 3
        #     if type == 2 and index == 3:
        #         index = 6
        # if type == 3 and index == 2:
        #     index += 1
        index = 0
        result = []
        index = 1
        if type in {0, 1}:  # type 0 go from warehouse-hub-warehouse
            index = 1
        if type == 2:
            index = 2
        elif type == 3:
            # type 1 go from warehouse-hub-depot-depot-hub-warehouse
            # area
            index = 3
        for direction in direction_result[0]['legs']:
            if type == 2 and index == 3:
                index = 6
            if type == 3 and index == 2:
                index += 1
            from_name_seq = ""
            to_name_seq = ""
            if index == AreaDistanceType.warehouse_to_hub.value:  # starting warehouse
                to_name_seq = kwargs['from_hub']
            elif index == AreaDistanceType.hub_to_hub.value:
                from_name_seq = kwargs['from_hub']
                to_name_seq = kwargs['to_hub']
            elif index == AreaDistanceType.hub_to_depot.value:
                from_name_seq = kwargs['from_hub']
                to_name_seq = kwargs['from_depot']
            elif index == AreaDistanceType.depot_to_depot.value:
                from_name_seq = kwargs['from_depot']
                to_name_seq = kwargs['to_depot']
            elif index == AreaDistanceType.depot_to_hub.value:
                from_name_seq = kwargs['to_depot']
                to_name_seq = kwargs['to_hub']
            elif index == AreaDistanceType.hub_to_warehouse.value:  # Destination
                from_name_seq = kwargs['to_hub']
            obj = {
                "distance": direction['distance']['value'],
                "duration": direction['duration']['value'],
                "fromLocation": {
                    "latitude": direction['start_location']['lat'],
                    "longitude": direction['start_location']['lng']
                },
                "toLocation": {
                    "latitude": direction['end_location']['lat'],
                    "longitude": direction['end_location']['lng']
                },
                "type": index,
                "from_name_seq": from_name_seq,
                "to_name_seq": to_name_seq
            }
            index += 1
            result.append(obj)
        return result

    def _validate_update(self, vals):
        c_type = vals['cycle_type'] if 'cycle_type' in vals else 0
        if c_type not in {'4', '5'}:
            st_date = vals.get('start_date') or str(self.start_date)
            ed_date = vals.get('end_date') or str(self.end_date)
            if isinstance(st_date, str):
                st_date = datetime.strptime(st_date, "%Y-%m-%d")
            if isinstance(ed_date, str):
                ed_date = datetime.strptime(ed_date, "%Y-%m-%d")
            if ed_date and ed_date < st_date:
                raise ValidationError("End date must be greater than Start date")
        else:
            vals['end_date'] = vals['start_date']
        need_validate_bldd = False
        temp_vals = deepcopy(vals)
        count_deleted = 0
        if 'bill_lading_detail_ids' in temp_vals:
            need_validate_bldd = True
            for bldd in temp_vals['bill_lading_detail_ids']:
                if bldd[0] == 2:
                    count_deleted += 1
        elif not self.bill_lading_detail_ids:
            raise ValidationError("Cannot have bill of lading without bill of lading detail!")
        # compare deleted to current list.
        # also check if there are any bldd to replace deleted one
        if (count_deleted == len(self.bill_lading_detail_ids)) \
                and (len(temp_vals['bill_lading_detail_ids']) == len(self.bill_lading_detail_ids)):
            raise ValidationError("Cannot save bill of lading without detail!")
        if not need_validate_bldd:
            return
        for record in self.bill_lading_detail_ids:
            is_in = False
            for obj in temp_vals['bill_lading_detail_ids']:
                # 2 mean to be deleted
                if record.id == obj[1] and obj[0] != 2:
                    is_in = True
                    if obj[2]:
                        if 'warehouse_type' not in obj[2]:
                            obj[2]['warehouse_type'] = record.warehouse_type
                        if 'warehouse_id' not in obj[2]:
                            obj[2]['warehouse_id'] = record.warehouse_id.id
                    # bill package was not edited so copy current data to it
                    if not obj[2] or 'bill_package_line' not in obj[2]:
                        obj[2] = record.copy_data()[0]
                    # bill packages was edited so check for every package
                    # not include removed (-2) packages to pass for validate
                    elif 'bill_package_line' in obj[2]:
                        pkl = record.bill_package_line
                        new_list = []
                        for pk in obj[2]['bill_package_line']:
                            if pk[2] and pk[0] == 0:
                                new_list.append(pk)
                            elif not pk[2]:
                                for p in pkl:
                                    # pk[0] = 0 mean new
                                    # pk[0] = 2 mean deleting
                                    # pk[0] = 4 mean not changing
                                    # need more testing
                                    if p.id == pk[1] and pk[0] != 2:
                                        pk[2] = p.copy_data()[0]
                                        new_list.append(pk)
                                        break
                        obj[2]['bill_package_line'] = new_list
                    break
            if not is_in:
                converted_obj = record.copy_data()[0]
                temp_vals.append(converted_obj)
        self._validate_create(temp_vals)

        if 'total_parcel' in temp_vals and temp_vals['total_parcel'] > 0:
            vals['total_parcel'] = temp_vals['total_parcel']
        if 'total_weight' in temp_vals and temp_vals['total_weight'] > 0:
            vals['total_weight'] = temp_vals['total_weight']
        if 'total_volume' in temp_vals and temp_vals['total_volume'] > 0:
            vals['total_volume'] = temp_vals['total_volume']

    def _validate_create(self, vals):
        c_type = vals['cycle_type'] if 'cycle_type' in vals else 0
        if c_type not in {'4', '5'}:
            st_date = vals.get('start_date') or str(self.start_date)
            ed_date = vals.get('end_date') or str(self.end_date)
            if isinstance(st_date, str):
                st_date = datetime.strptime(st_date, "%Y-%m-%d")
            if isinstance(ed_date, str):
                ed_date = datetime.strptime(ed_date, "%Y-%m-%d")
            if ed_date and ed_date < st_date:
                raise ValidationError("End date must be greater than Start date")
        else:
            vals['end_date'] = vals['start_date']

        total_weight = 0.0
        total_volume = 0.0
        total_parcel = 0
        type_0 = 0
        export_weight = 0.0
        export_volume = 0.0
        export_parcel = 0
        converted_weight = 0
        denominator = int(http.request.env['ir.config_parameter'].sudo().get_param('weight.constant.order'))

        if 'bill_lading_detail_ids' in vals:
            list_detail = vals['bill_lading_detail_ids']
        else:
            raise ValidationError("Cannot save bill of lading without detail!")
        selected_warehouse = []
        for detail in list_detail:
            if detail[0] == 2:
                continue
            dt = detail
            if len(detail) > 0:
                dt = detail[2]
                vals['need_cal'] = True
            if 'bill_package_line' not in dt:
                if 'bill_package_import' in dt:
                    list_ids = []
                    new_list_import = []
                    for pk_import in dt['bill_package_import']:
                        if pk_import[1] not in list_ids:
                            list_ids.append(pk_import[1])
                        if pk_import[2]:
                            new_list_import.append(pk_import)
                    list_search = self.env['sharevan.bill.package'].search([('id', 'in', list_ids)])
                    dt['bill_package_line'] = new_list_import
                    dt.pop('bill_package_import')
                    for list_import in dt['bill_package_line']:
                        for res in list_search:
                            # no id mean it's already taken
                            if 'id' in res and list_import[1] == res.id:
                                obj = res.copy_data()[0]
                                quantity = list_import[2]['quantity_package']
                                list_import[2] = obj
                                list_import[2]['quantity_package'] = quantity

                else:
                    raise ValidationError("No package in detail!")
            # if package quantity = 0, don't add to this list
            # save this list instead to database later
            list_package = dt['bill_package_line']
            new_pk = []
            # check if this warehouse is already chosen
            if 'warehouse_id' in dt and dt['warehouse_id'] not in selected_warehouse:
                selected_warehouse.append(dt['warehouse_id'])
            elif 'warehouse_id' in dt:
                raise ValidationError('"{wh}" is chosen more than once!'.format(wh=dt['warehouse_name']))
            # calculate import weight, volume..
            if dt['warehouse_type'] == '0':
                if type_0 > 0:
                    raise ValidationError(_('There can only be 1 import bill of lading detail'))
                type_0 += 1
                detail_volume = 0
                for package in list_package:
                    if len(package) > 0 and package[0] != 2:
                        package = package[2]
                    quantity = package['quantity_package'] or 0
                    if quantity > 0:
                        new_pk.append([0, '', package])
                    total_parcel += quantity
                    total_weight += package['net_weight'] * quantity
                    detail_volume += package['length'] * package['width'] * package['height'] * quantity
                    converted_weight += (package['width'] * package['height'] * package[
                        'length'] * quantity) / denominator
                dt['total_volume'] = detail_volume
                total_volume += detail_volume
            # calculate weight, volume.. for comparison
            elif dt['warehouse_type'] == '1':
                list_package = dt['bill_package_line']
                detail_volume = 0
                for package in list_package:
                    if len(package) > 0:
                        package = package[2]
                    quantity = package['quantity_package'] or 0
                    if quantity > 0:
                        new_pk.append([0, '', package])
                        export_parcel += quantity
                        export_weight += package['net_weight'] * quantity
                        detail_volume += package['length'] * package['width'] * package['height'] * quantity
                dt['total_volume'] = detail_volume
                export_volume += detail_volume
            if len(detail) == 3 and 'bill_package_line' in detail[2]:
                detail[2]['bill_package_line'] = new_pk
        export_weight = round(export_weight, 4)
        total_weight = round(total_weight, 4)
        export_volume = round(export_volume, 3)
        total_volume = round(total_volume, 3)
        if export_weight != total_weight:
            raise ValidationError(_("Total export weight must be the same as import weight"))
        if total_weight == 0:
            raise ValidationError("Total weight must be > 0")
        if export_volume != total_volume:
            raise ValidationError(_("Total export volume must be the same as import volume"))
        if export_parcel != total_parcel:
            raise ValidationError(_("Total export parcel must be the same as import parcel"))

        vals['total_parcel'] = total_parcel
        if converted_weight > total_weight:
            vals['total_weight'] = converted_weight
        else:
            vals['total_weight'] = total_weight
        vals['total_volume'] = total_volume

    @api.onchange('chooseDay')
    def _onchange_chooseDay(self):
        choose_day = self['chooseDay']
        if choose_day:
            self['day_of_month'] = choose_day.day

    @api.onchange('week_choose')
    def _onchange_week_choose(self):
        week_choose = self['week_choose']
        if week_choose:
            self['day_of_week'] = int(week_choose)

    @api.onchange('subscribe_id')
    def _onchange_subscribe_id(self):
        for record in self:
            if record.cycle_type and record.cycle_type <= '3':
                record.end_date = record.start_date + timedelta(days=record.subscribe_id.value - 1)

    @api.onchange('start_date')
    def _onchange_start_date(self):
        for record in self:
            if record.start_date < datetime.today().date():
                record.start_date = datetime.today().date()
                raise ValidationError("Start date must be after today!")
            if record.cycle_type and record.cycle_type < '3':
                record.end_date = record.start_date + timedelta(days=record.subscribe_id.value - 1)

    @api.onchange('cycle_type')
    def _onchange_cycle_type(self):
        c_type = self['cycle_type']
        if c_type in '1':
            self['frequency'] = 1
            self['day_of_week'] = 0
            self['day_of_month'] = 0
        elif c_type == '2':
            self['frequency'] = 2
            self['day_of_week'] = int(self['week_choose'])
            self['day_of_month'] = 0
        elif c_type == '3':
            self['frequency'] = 3
            self['day_of_week'] = 0
            self['day_of_month'] = self.chooseDay.day
        elif c_type == '4':
            self['frequency'] = 4
            self['day_of_week'] = 0
            self['day_of_month'] = 0
            self['subscribe_id'] = False
        elif c_type == '5':
            self['frequency'] = 5
            self['day_of_week'] = 0
            self['day_of_month'] = 0
            self['subscribe_id'] = False

    def get_data_on_load(self):
        today = datetime.today()
        if self.day_of_month:
            d = datetime(today.year, today.month, int(self.day_of_month), today.hour, today.minute)
            self.chooseDay = d
        else:
            self.chooseDay = today
        # if self.frequency == 1:
        #     self.cycle_type = '1'
        # if self.frequency == 2:
        #     self.cycle_type = '2'
        # if self.frequency == 3:
        #     self.cycle_type = '3'
        print(self.chooseDay)

    # def default_encode(self, o):
    #
    #     if hasattr(o, '__dict__'):
    #         return o.__dict__
    #     return json.JSONEncoder.default(o)

    @api.onchange('bill_lading_detail_ids')
    def _on_change_bill_details(self):
        list_detail = self.bill_lading_detail_ids
        total_weight = 0.0
        total_volume = 0.0
        total_parcel = 0
        type_0 = 0
        export_weight = 0.0
        export_volume = 0.0
        for detail in list_detail:
            if detail.warehouse_type == '0':
                if type_0 > 0:
                    raise ValidationError(_('There can only be 1 import bill of lading detail'))
                type_0 += 1
                list_package = detail.bill_package_line
                key_ind = 1
                for package in list_package:
                    quantity = package.quantity_package or 0
                    total_parcel += quantity
                    total_weight += package.net_weight * quantity
                    total_volume += package.length * package.width * package.height * quantity
                    package.key_map = key_ind
                    key_ind += 1
                    package.total_quantity = quantity
            elif detail.warehouse_type == '1':
                list_package = detail.bill_package_line
                for package in list_package:
                    quantity = package.quantity_package or 0
                    export_weight += package.net_weight * quantity
                    export_volume += package.length * package.width * package.height * quantity
        self.export_weight = export_weight
        self.export_volume = export_volume
        self.total_parcel = total_parcel
        self.total_weight = total_weight
        self.total_volume = total_volume

        #     validated = False

    def _update_total(self):
        for bill_lading in self:
            org = self._origin
            org_total = org.total_amount
            new_total = org_total / (org.vat / 100 + 1)
            new_total -= org.tolls
            new_total -= org.surcharge

            new_total += bill_lading.tolls
            new_total += bill_lading.surcharge
            new_total = new_total * (1 + bill_lading.vat / 100)

            bill_lading.total_amount = new_total

    @api.onchange('vat')
    def _onchange_vat(self):
        for bill_lading in self:
            if bill_lading.vat < 0:
                bill_lading.vat = 0
            elif bill_lading.vat > 50:
                bill_lading.vat = 50
            self._update_total()

    @api.onchange('tolls')
    def _onchange_tolls(self):
        for bill_lading in self:
            if bill_lading.tolls < 0:
                bill_lading.tolls = 0
            else:
                self._update_total()

    @api.onchange('surcharge')
    def _onchange_sur(self):
        for bill_lading in self:
            if bill_lading.surcharge < 0:
                bill_lading.surcharge = 0
            else:
                self._update_total()

    def unlink(self):
        for bill_lading in self:
            print('bill_lading', bill_lading)
            if bill_lading.status in ('0', '2'):
                raise ValidationError(
                    _('You cannot delete a warehouse which is not NO-ACTIVE. You should refund it instead.'))

            record_ids = self.env['sharevan.bill.lading'].search([('name', '=', bill_lading.name)])
            for record in record_ids:
                super(BillLading, record).write({
                    'status': 'deleted'
                })
                record_bill_lading_detail_ids = self['bill_lading_detail_ids']
                for rc in record_bill_lading_detail_ids:
                    super(BillLadingDetail, rc).write({
                        'status_order': 'deleted'
                    })
        return self

    def get_list_by_date(self, date, status_order):
        query = """
            select * 
            from sharevan_bill_lading as t 
            where exists (select 1 from sharevan_bill_lading_detail d 
                          where t.id = d.bill_lading_id
                                and not(d.expected_from_time > %s 
                            and d.expected_to_time < %s) and status_order = 'running') and status = 'running'
                """
        # where_clause = []
        # where_clause.append("status "+ " = " +status_order)
        # self._cr.execute(query, (date, date,), where_clause)
        # where_clause = []
        self._cr.execute(query, (date, date,))
        rec = self._cr.fetchall()

        bill_ladings = self.browse([x[0] for x in rec]).read()
        detail_ids = []
        map_ladings = dict()
        map_details = dict()
        map_warehouse = dict()
        current_detail = dict()

        for r in bill_ladings:
            detail_ids.extend(r['bill_lading_detail_ids'])
            r['arrBillLadingDetail'] = []
            map_ladings[r['id']] = r
            current_detail[r['id']] = {}

        bill_lading_details = self.env[BillLadingDetail._name].browse(self._uniquify_list(detail_ids)).read()

        bill_packages_ids = []
        warehouse_ids = []
        for r in bill_lading_details:
            bill_packages_ids.extend(r['bill_package_line'])
            warehouse_ids.append(r['warehouse_id'][0])
            tmp_bill_lading = map_ladings[r['bill_lading_id'][0]]
            tmp_bill_lading['arrBillLadingDetail'].append(r)
            map_details[r['id']] = r
            r['billPackages'] = []
            r['warehouse'] = {}
            map_warehouse[r['warehouse_id'][0]] = r
            # tim current lading_detail
            if r['expected_from_time'] and r['expected_to_time'] \
                    and r['expected_from_time'] <= date <= r['expected_to_time']:
                tmp_bill_lading['currentBillDetail'] = r

        # lay du lieu package
        bill_packages = self.env[BillPackage._name].browse(self._uniquify_list(bill_packages_ids)).read()

        for r in bill_packages:
            tmp_bill_lading_detail = map_details[r['bill_lading_detail_id'][0]]
            if tmp_bill_lading_detail:
                tmp_bill_lading_detail['billPackages'].append(r)

        # lay du lieu warehouse
        warehouses = self.env[Warehouse._name].browse(self._uniquify_list(warehouse_ids)).read()
        for bld in bill_lading_details:
            for w in warehouses:
                if w['id'] == bld['warehouse_id'][0]:
                    bld['warehouse'] = w
                    break

        return bill_ladings

    def get_bill_lading_update(self, bill_lading_detail_id):
        record = http.request.env[BillLadingDetail._name].search \
            ([('id', '=', bill_lading_detail_id)])
        if record is None or len(record) == 0:
            raise ValidationError('Bill of lading change not found')
        record = http.request.env[BillLading._name].search \
            ([('id', '=', record[0]['bill_lading_id']['id'])])
        if record:
            bill_lading_id = record['id']
            order_package = {}
            if record['order_package_id']:
                order_package['id'] = record['order_package_id'].id
            insurance = {}
            if record['insurance_id']:
                insurance['id'] = record['insurance_id'].id
            val = {
                'from_bill_lading_id': record['id'],
                'total_weight': 0,
                'total_amount': 0,
                'name': record['name'],
                'tolls': 0,
                'surcharge': 0,
                'total_volume': 0,
                'vat': 0,
                'order_package': order_package,
                'insurance': insurance,
                'promotion_code': 0,
                'total_parcel': 0,
                'company_id': http.request.env.company.id,
                'start_date': datetime.utcnow(),
                'end_date': datetime.utcnow(),
                'frequency': 4,
                'description': '',
                'export_weight': 0,
                'export_volume': 0
            }
            arrBillLadingDetail = []
            query = """
                SELECT json_agg(t)
                    FROM (
                SELECT id, name_seq, bill_lading_id, total_weight, warehouse_id, warehouse_type, 
                    from_bill_lading_detail_id, description, 
                    TO_CHAR(expected_from_time, 'YYYY-MM-DD HH24:MI:SS') expected_from_time,
                    TO_CHAR(expected_to_time, 'YYYY-MM-DD HH24:MI:SS') expected_to_time,
                    name, status, approved_type, from_warehouse_id, latitude, longitude, area_id, 
                    zone_area_id, address, status_order, create_uid, 
                    TO_CHAR(create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, write_uid,
                    TO_CHAR(write_date, 'YYYY-MM-DD HH24:MI:SS') write_date,
                    warehouse_name,  max_price, min_price, price, trans_id,
                    depot_id, order_type, phone, hub_id
                FROM public.sharevan_bill_lading_detail where id = %s)t;
            """
            http.request.env[BillLadingDetail._name]._cr.execute(query, (bill_lading_detail_id,))
            records = http.request.env[BillLadingDetail._name]._cr.fetchall()
            if records[0]:
                if records[0][0]:
                    change_bill_lading_detai = records[0][0][0]
                    change_bill_lading_detai['name_seq'] = 'New'
                    change_bill_lading_detai['name'] = 'New'
                    get_sharevan_bill_lading_detail_sharevan_service_type_rel = """  
                        SELECT json_agg(t)
                            from
                            ( SELECT sharevan_bill_lading_detail_id, sharevan_service_type_id
                            FROM public.sharevan_bill_lading_detail_sharevan_service_type_rel rel 
                                where rel.sharevan_bill_lading_detail_id = %s ) t  """
                    self.env.cr.execute(get_sharevan_bill_lading_detail_sharevan_service_type_rel,
                                        (change_bill_lading_detai['id'],))
                    result_service_rel = self._cr.fetchall()
                    warehouse_infor = {}
                    if 'warehouse_id' in change_bill_lading_detai and change_bill_lading_detai['warehouse_id']:
                        get_warehouse = """
                            SELECT json_agg(t) from ( select ware.id ware_id, ware.name_seq ware_code, ware.name ware_name ,
                                ware.address ware_address, ware.latitude ware_latitude,ware.longitude ware_longitude,
                                ware.phone ware_phone, area.id, area.name,area.name_seq,area.code , 
                                zone.id zone_id ,zone.name zone_name, zone.name_seq zone_seq,zone.code zone_code,
                                hub.id hub_id,hub.name hub_name, hub.name_seq hub_seq,
                                hub.latitude hub_latitude,hub.longitude hub_longitude, hub.address hub_address,
                                depot.id depot_id,depot.name depot_name,depot.name_seq depot_seq,
                                depot.latitude depot_latitude,depot.longitude depot_longitude, depot.address depot_address
                            from sharevan_warehouse ware
                                join sharevan_area  area on ware.area_id = area.id
                                left join sharevan_zone zone on area.zone_area_id = zone.id
                                left join sharevan_hub hub on hub.id= area.hub_id
                                left join sharevan_depot depot on depot.id = zone.depot_id
                            where  ware.id = %s and ware.status = 'running' )t"""
                        self.env.cr.execute(get_warehouse,
                                            (change_bill_lading_detai['warehouse_id'],))
                        result_get_warehouse = self._cr.fetchall()
                        if result_get_warehouse[0]:
                            if result_get_warehouse[0][0]:
                                warehouse_infor = {
                                    'id': result_get_warehouse[0][0][0]['ware_id'],
                                    'warehouse_code': result_get_warehouse[0][0][0]['ware_code'],
                                    'name': result_get_warehouse[0][0][0]['ware_name'],
                                    'address': result_get_warehouse[0][0][0]['ware_address'],
                                    'latitude': result_get_warehouse[0][0][0]['ware_latitude'],
                                    'longitude': result_get_warehouse[0][0][0]['ware_longitude'],
                                    'phone': result_get_warehouse[0][0][0]['ware_phone'],
                                    'areaInfo': {
                                        'id': result_get_warehouse[0][0][0]['id'],
                                        'name': result_get_warehouse[0][0][0]['name'],
                                        'name_seq': result_get_warehouse[0][0][0]['name_seq'],
                                        'code': result_get_warehouse[0][0][0]['code'],
                                        'zoneInfo': {
                                            'id': result_get_warehouse[0][0][0]['zone_id'],
                                            'name': result_get_warehouse[0][0][0]['zone_name'],
                                            'name_seq': result_get_warehouse[0][0][0]['zone_seq'],
                                            'code': result_get_warehouse[0][0][0]['zone_code'],
                                            'depotInfo': {
                                                'id': result_get_warehouse[0][0][0]['depot_id'],
                                                'name': result_get_warehouse[0][0][0]['depot_name'],
                                                'name_seq': result_get_warehouse[0][0][0]['depot_seq'],
                                                'address': result_get_warehouse[0][0][0]['depot_address'],
                                                'latitude': result_get_warehouse[0][0][0]['depot_latitude'],
                                                'longitude': result_get_warehouse[0][0][0]['depot_longitude']
                                            }
                                        },
                                        'hubInfo': {
                                            'id': result_get_warehouse[0][0][0]['hub_id'],
                                            'name': result_get_warehouse[0][0][0]['hub_name'],
                                            'name_seq': result_get_warehouse[0][0][0]['hub_seq'],
                                            'address': result_get_warehouse[0][0][0]['hub_address'],
                                            'latitude': result_get_warehouse[0][0][0]['hub_latitude'],
                                            'longitude': result_get_warehouse[0][0][0]['hub_longitude']
                                        }
                                    }
                                }
                    else:
                        get_warehouse = """
                            SELECT json_agg(t) from ( select  area.id, area.name,area.name_seq,area.code , 
                                zone.id zone_id ,zone.name zone_name, zone.name_seq zone_seq,zone.code zone_code,
                                hub.id hub_id,hub.name hub_name, hub.name_seq hub_seq,
                                hub.latitude hub_latitude,hub.longitude hub_longitude, hub.address hub_address,
                                depot.id depot_id,depot.name depot_name,depot.name_seq depot_seq,
                                depot.latitude depot_latitude,depot.longitude depot_longitude, 
                                depot.address depot_address
                            from sharevan_area  area
                                left join sharevan_zone zone on area.zone_area_id = zone.id
                                left join sharevan_hub hub on hub.id= area.hub_id
                                left join sharevan_depot depot on depot.id = zone.depot_id
                            where  area.id = %s and area.zone_area_id = %s and area.status = 'running' )t"""
                        self.env.cr.execute(get_warehouse,
                                            (change_bill_lading_detai['area_id'],
                                             change_bill_lading_detai['zone_area_id'],))
                        result_get_warehouse = self._cr.fetchall()
                        if result_get_warehouse[0]:
                            if result_get_warehouse[0][0]:
                                warehouse_infor = {
                                    'id': '',
                                    'warehouse_code': '',
                                    'name': change_bill_lading_detai['warehouse_name'],
                                    'address': change_bill_lading_detai['address'],
                                    'latitude': change_bill_lading_detai['latitude'],
                                    'longitude': change_bill_lading_detai['longitude'],
                                    'phone': change_bill_lading_detai['phone'],
                                    'areaInfo': {
                                        'id': result_get_warehouse[0][0][0]['id'],
                                        'name': result_get_warehouse[0][0][0]['name'],
                                        'name_seq': result_get_warehouse[0][0][0]['name_seq'],
                                        'code': result_get_warehouse[0][0][0]['code'],
                                        'zoneInfo': {
                                            'id': result_get_warehouse[0][0][0]['zone_id'],
                                            'name': result_get_warehouse[0][0][0]['zone_name'],
                                            'name_seq': result_get_warehouse[0][0][0]['zone_seq'],
                                            'code': result_get_warehouse[0][0][0]['zone_code'],
                                            'depotInfo': {
                                                'id': result_get_warehouse[0][0][0]['depot_id'],
                                                'name': result_get_warehouse[0][0][0]['depot_name'],
                                                'name_seq': result_get_warehouse[0][0][0]['depot_seq'],
                                                'address': result_get_warehouse[0][0][0]['depot_address'],
                                                'latitude': result_get_warehouse[0][0][0]['depot_latitude'],
                                                'longitude': result_get_warehouse[0][0][0]['depot_longitude']
                                            }
                                        },
                                        'hubInfo': {
                                            'id': result_get_warehouse[0][0][0]['hub_id'],
                                            'name': result_get_warehouse[0][0][0]['hub_name'],
                                            'name_seq': result_get_warehouse[0][0][0]['hub_seq'],
                                            'address': result_get_warehouse[0][0][0]['hub_address'],
                                            'latitude': result_get_warehouse[0][0][0]['hub_latitude'],
                                            'longitude': result_get_warehouse[0][0][0]['hub_longitude']
                                        }
                                    }
                                }
                    result_service_rel_arr = []
                    if result_service_rel[0][0]:
                        for rec_service in result_service_rel[0][0]:
                            get_sharevan_service_type = """ 
                                SELECT json_agg(t)
                                    from
                                    ( SELECT id, name, price, vendor_id, service_code, status, description, 
                                        create_uid, TO_CHAR(create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, write_uid,
                                        TO_CHAR(write_date, 'YYYY-MM-DD HH24:MI:SS') write_date
                                        FROM public.sharevan_service_type service_type where service_type.id = %s ) t """
                            self.env.cr.execute(get_sharevan_service_type,
                                                (rec_service['sharevan_service_type_id'],))
                            result_get_sharevan_service_type = self._cr.fetchall()
                            result_service_rel_arr.append(result_get_sharevan_service_type[0][0][0])

                    get_bill_package = """ 
                        SELECT json_agg(t)
                            from
                            ( SELECT bill_package.id, bill_package.item_name, bill_package.bill_lading_detail_id, 
                                bill_package.net_weight, bill_package.quantity_package, bill_package.length,
                                bill_package.width, bill_package.height, bill_package.capacity, bill_package.description,
                                bill_package.product_type_id,p.name product_type_name,  bill_package.status, 
                                bill_package.create_uid, 
                                TO_CHAR(bill_package.create_date, 'YYYY-MM-DD HH24:MI:SS') create_date,
                                bill_package.write_uid, 
                                TO_CHAR(bill_package.write_date, 'YYYY-MM-DD HH24:MI:SS') write_date,
                                from_package.id from_package_id ,
                                from_package.net_weight from_package_net_weight,
                                from_package.quantity_package from_package_quantity_package , 
                                from_package.length from_package_length,
                                from_package.width from_package_width, 
                                from_package.height from_package_height,
                                from_package.product_type_id from_package_product_type_id
                            FROM public.sharevan_bill_package bill_package
                                join sharevan_product_type p on p.id = bill_package.product_type_id
                                join public.sharevan_bill_package from_package on from_package.id = bill_package.from_bill_package_id
                            where bill_package.bill_lading_detail_id = %s ) t """
                    self.env.cr.execute(get_bill_package, (change_bill_lading_detai['id'],))
                    result_get_bill_package = self._cr.fetchall()
                    list_bill_package_import = []
                    if result_get_bill_package[0]:
                        if result_get_bill_package[0][0]:
                            for result_bill_import in result_get_bill_package[0][0]:
                                vals = {
                                    'id': result_bill_import['id'],
                                    'item_name': result_bill_import['item_name'],
                                    'bill_lading_detail_id': result_bill_import['bill_lading_detail_id'],
                                    'net_weight': result_bill_import['net_weight'],
                                    'quantity_package': result_bill_import['quantity_package'],
                                    'length': result_bill_import['length'],
                                    'width': result_bill_import['width'],
                                    'height': result_bill_import['height'],
                                    'capacity': result_bill_import['capacity'],
                                    'description': result_bill_import['description'],
                                    'product_type_id': result_bill_import['product_type_id'],
                                    'productType': {'id': result_bill_import['product_type_id']},
                                    'product_type_name': result_bill_import['product_type_name'],
                                    'status': result_bill_import['status'],
                                    'create_uid': result_bill_import['create_uid'],
                                    'write_uid': result_bill_import['write_uid'],
                                    'create_date': result_bill_import['create_date'],
                                    'write_date': result_bill_import['write_date'],
                                    'from_bill_package_id': result_bill_import['from_package_id'],
                                    'origin_bill_package': {
                                        'id': result_bill_import['from_package_id'],
                                        'net_weight': result_bill_import['from_package_net_weight'],
                                        'quantity_package': result_bill_import['from_package_quantity_package'],
                                        'length': result_bill_import['from_package_length'],
                                        'width': result_bill_import['from_package_width'],
                                        'height': result_bill_import['from_package_height'],
                                        'product_type_id': result_bill_import['from_package_product_type_id'],
                                    }
                                }
                                list_bill_package_import.append(vals)
                    change_bill_lading_detai['warehouse'] = warehouse_infor
                    change_bill_lading_detai['billPackages'] = list_bill_package_import
                    change_bill_lading_detai['billService'] = result_service_rel_arr
                    arrBillLadingDetail.append(change_bill_lading_detai)

                    # lấy danh sách bill of lading detail trả hàng
                    query = """
                    SELECT json_agg(t)
                        FROM (
                    SELECT id, name_seq, bill_lading_id, total_weight, warehouse_id, warehouse_type, 
                        from_bill_lading_detail_id, description,
                        TO_CHAR(expected_from_time, 'YYYY-MM-DD HH24:MI:SS') expected_from_time,
                        TO_CHAR(expected_to_time, 'YYYY-MM-DD HH24:MI:SS') expected_to_time,
                        name, status, approved_type, from_warehouse_id, latitude, longitude, area_id, 
                        zone_area_id, address, status_order, create_uid, write_uid,
                        warehouse_name,  max_price, min_price, price, trans_id,
                        depot_id, order_type, phone, hub_id
                    FROM public.sharevan_bill_lading_detail where bill_lading_id = %s and warehouse_type ='1'
                        and status_order = 'running'
                    )t;
                    """
                    http.request.env[BillLadingDetail._name]._cr.execute(query, (bill_lading_id,))
                    records = http.request.env[BillLadingDetail._name]._cr.fetchall()
                    if records[0]:
                        if records[0][0]:
                            for rec_bill_detail in records[0][0]:
                                get_sharevan_bill_lading_detail_sharevan_service_type_rel = """  
                                SELECT json_agg(t)
                                    from
                                    ( SELECT sharevan_bill_lading_detail_id, sharevan_service_type_id
                                    FROM public.sharevan_bill_lading_detail_sharevan_service_type_rel rel 
                                        where rel.sharevan_bill_lading_detail_id = %s ) t  """
                                self.env.cr.execute(get_sharevan_bill_lading_detail_sharevan_service_type_rel,
                                                    (rec_bill_detail['id'],))
                                result_service_rel = self._cr.fetchall()
                                warehouse_infor = {}
                                if 'warehouse_id' in change_bill_lading_detai and change_bill_lading_detai[
                                    'warehouse_id']:
                                    get_warehouse = """
                                        SELECT json_agg(t) from ( select ware.id ware_id, ware.name_seq ware_code, ware.name ware_name ,
                                            ware.address ware_address, ware.latitude ware_latitude,ware.longitude ware_longitude,
                                            ware.phone ware_phone, area.id, area.name,area.name_seq,area.code , 
                                            zone.id zone_id ,zone.name zone_name, zone.name_seq zone_seq,zone.code zone_code,
                                            hub.id hub_id,hub.name hub_name, hub.name_seq hub_seq,
                                            hub.latitude hub_latitude,hub.longitude hub_longitude, hub.address hub_address,
                                            depot.id depot_id,depot.name depot_name,depot.name_seq depot_seq,
                                            depot.latitude depot_latitude,depot.longitude depot_longitude, depot.address depot_address
                                        from sharevan_warehouse ware
                                            join sharevan_area  area on ware.area_id = area.id
                                            left join sharevan_zone zone on area.zone_area_id = zone.id
                                            left join sharevan_hub hub on hub.id= area.hub_id
                                            left join sharevan_depot depot on depot.id = zone.depot_id
                                        where  ware.id = %s and ware.status = 'running' )t"""
                                    self.env.cr.execute(get_warehouse,
                                                        (rec_bill_detail['warehouse_id'],))
                                    result_get_warehouse = self._cr.fetchall()
                                    if result_get_warehouse[0]:
                                        if result_get_warehouse[0][0]:
                                            warehouse_infor = {
                                                'id': result_get_warehouse[0][0][0]['ware_id'],
                                                'warehouse_code': result_get_warehouse[0][0][0]['ware_code'],
                                                'name': result_get_warehouse[0][0][0]['ware_name'],
                                                'address': result_get_warehouse[0][0][0]['ware_address'],
                                                'latitude': result_get_warehouse[0][0][0]['ware_latitude'],
                                                'longitude': result_get_warehouse[0][0][0]['ware_longitude'],
                                                'phone': result_get_warehouse[0][0][0]['ware_phone'],
                                                'areaInfo': {
                                                    'id': result_get_warehouse[0][0][0]['id'],
                                                    'name': result_get_warehouse[0][0][0]['name'],
                                                    'name_seq': result_get_warehouse[0][0][0]['name_seq'],
                                                    'code': result_get_warehouse[0][0][0]['code'],
                                                    'zoneInfo': {
                                                        'id': result_get_warehouse[0][0][0]['zone_id'],
                                                        'name': result_get_warehouse[0][0][0]['zone_name'],
                                                        'name_seq': result_get_warehouse[0][0][0]['zone_seq'],
                                                        'code': result_get_warehouse[0][0][0]['zone_code'],
                                                        'depotInfo': {
                                                            'id': result_get_warehouse[0][0][0]['depot_id'],
                                                            'name': result_get_warehouse[0][0][0]['depot_name'],
                                                            'name_seq': result_get_warehouse[0][0][0]['depot_seq'],
                                                            'address': result_get_warehouse[0][0][0]['depot_address'],
                                                            'latitude': result_get_warehouse[0][0][0]['depot_latitude'],
                                                            'longitude': result_get_warehouse[0][0][0][
                                                                'depot_longitude']
                                                        }
                                                    },
                                                    'hubInfo': {
                                                        'id': result_get_warehouse[0][0][0]['hub_id'],
                                                        'name': result_get_warehouse[0][0][0]['hub_name'],
                                                        'name_seq': result_get_warehouse[0][0][0]['hub_seq'],
                                                        'address': result_get_warehouse[0][0][0]['hub_address'],
                                                        'latitude': result_get_warehouse[0][0][0]['hub_latitude'],
                                                        'longitude': result_get_warehouse[0][0][0]['hub_longitude']
                                                    }
                                                }
                                            }
                                else:
                                    get_warehouse = """
                                        SELECT json_agg(t) from ( select  area.id, area.name,area.name_seq,area.code , 
                                            zone.id zone_id ,zone.name zone_name, zone.name_seq zone_seq,zone.code zone_code,
                                            hub.id hub_id,hub.name hub_name, hub.name_seq hub_seq,
                                            hub.latitude hub_latitude,hub.longitude hub_longitude, hub.address hub_address,
                                            depot.id depot_id,depot.name depot_name,depot.name_seq depot_seq,
                                            depot.latitude depot_latitude,depot.longitude depot_longitude, 
                                            depot.address depot_address
                                        from sharevan_area  area
                                            left join sharevan_zone zone on area.zone_area_id = zone.id
                                            left join sharevan_hub hub on hub.id= area.hub_id
                                            left join sharevan_depot depot on depot.id = zone.depot_id
                                        where  area.id = %s and area.zone_area_id = %s and area.status = 'running' )t"""
                                    self.env.cr.execute(get_warehouse,
                                                        (rec_bill_detail['area_id'],
                                                         rec_bill_detail['zone_area_id'],))
                                    result_get_warehouse = self._cr.fetchall()
                                    if result_get_warehouse[0]:
                                        if result_get_warehouse[0][0]:
                                            warehouse_infor = {
                                                'id': '',
                                                'warehouse_code': '',
                                                'name': change_bill_lading_detai['warehouse_name'],
                                                'address': change_bill_lading_detai['address'],
                                                'latitude': change_bill_lading_detai['latitude'],
                                                'longitude': change_bill_lading_detai['longitude'],
                                                'phone': change_bill_lading_detai['phone'],
                                                'areaInfo': {
                                                    'id': result_get_warehouse[0][0][0]['id'],
                                                    'name': result_get_warehouse[0][0][0]['name'],
                                                    'name_seq': result_get_warehouse[0][0][0]['name_seq'],
                                                    'code': result_get_warehouse[0][0][0]['code'],
                                                    'zoneInfo': {
                                                        'id': result_get_warehouse[0][0][0]['zone_id'],
                                                        'name': result_get_warehouse[0][0][0]['zone_name'],
                                                        'name_seq': result_get_warehouse[0][0][0]['zone_seq'],
                                                        'code': result_get_warehouse[0][0][0]['zone_code'],
                                                        'depotInfo': {
                                                            'id': result_get_warehouse[0][0][0]['depot_id'],
                                                            'name': result_get_warehouse[0][0][0]['depot_name'],
                                                            'name_seq': result_get_warehouse[0][0][0]['depot_seq'],
                                                            'address': result_get_warehouse[0][0][0]['depot_address'],
                                                            'latitude': result_get_warehouse[0][0][0]['depot_latitude'],
                                                            'longitude': result_get_warehouse[0][0][0][
                                                                'depot_longitude']
                                                        }
                                                    },
                                                    'hubInfo': {
                                                        'id': result_get_warehouse[0][0][0]['hub_id'],
                                                        'name': result_get_warehouse[0][0][0]['hub_name'],
                                                        'name_seq': result_get_warehouse[0][0][0]['hub_seq'],
                                                        'address': result_get_warehouse[0][0][0]['hub_address'],
                                                        'latitude': result_get_warehouse[0][0][0]['hub_latitude'],
                                                        'longitude': result_get_warehouse[0][0][0]['hub_longitude']
                                                    }
                                                }
                                            }

                                result_service_rel_arr = []
                                if result_service_rel[0][0]:
                                    for rec_service in result_service_rel[0][0]:
                                        get_sharevan_service_type = """ 
                                            SELECT json_agg(t)
                                                from ( SELECT id, name, price, vendor_id, service_code, status, description,
                                                        create_uid, TO_CHAR(create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, 
                                                        write_uid,TO_CHAR(write_date, 'YYYY-MM-DD HH24:MI:SS') write_date
                                            FROM public.sharevan_service_type service_type where service_type.id = %s ) t """
                                        self.env.cr.execute(get_sharevan_service_type,
                                                            (rec_service['sharevan_service_type_id'],))
                                        result_get_sharevan_service_type = self._cr.fetchall()
                                        result_service_rel_arr.append(result_get_sharevan_service_type[0][0][0])

                                get_bill_package = """ 
                                SELECT json_agg(t)
                                    from
                                    ( SELECT bill_package.id, bill_package.item_name, bill_package.bill_lading_detail_id, 
                                        bill_package.net_weight, bill_package.quantity_package, bill_package.length,
                                        bill_package.width, bill_package.height, bill_package.capacity, 
                                        bill_package.description, bill_package.product_type_id,p.name product_type_name, 
                                        bill_package.status, bill_package.create_uid, 
                                        TO_CHAR(bill_package.create_date, 'YYYY-MM-DD HH24:MI:SS') create_date, bill_package.write_uid, 
                                        TO_CHAR(bill_package.write_date, 'YYYY-MM-DD HH24:MI:SS') write_date
                                   FROM public.sharevan_bill_package bill_package
                                        join sharevan_product_type p on p.id = bill_package.product_type_id
                                   where bill_package.bill_lading_detail_id = %s ) t """
                                self.env.cr.execute(get_bill_package, (rec_bill_detail['id'],))
                                result_get_bill_package = self._cr.fetchall()
                                list_bill_package = []
                                if result_get_bill_package[0]:
                                    if result_get_bill_package[0][0]:
                                        for bill_package in result_get_bill_package[0][0]:
                                            for from_package in list_bill_package_import:
                                                if bill_package['product_type_id'] == \
                                                        from_package['origin_bill_package'][
                                                            'product_type_id'] and bill_package['length'] == \
                                                        from_package['origin_bill_package']['length'] and bill_package[
                                                    'width'] == from_package['origin_bill_package']['width'] and \
                                                        bill_package['height'] == from_package['origin_bill_package'][
                                                    'height']:
                                                    bill_package['length'] = from_package['length']
                                                    bill_package['net_weight'] = from_package['net_weight']
                                                    bill_package['width'] = from_package['width']
                                                    bill_package['height'] = from_package['height']
                                                    bill_package['item_name'] = from_package['item_name']
                                                    bill_package['from_change_bill_package_id'] = from_package['id']
                                                    break
                                            bill_package['from_bill_package_id'] = bill_package['id']
                                            bill_package['productType'] = {
                                                'id': bill_package['product_type_id']
                                            }
                                            list_bill_package.append(bill_package)
                                rec_bill_detail['warehouse'] = warehouse_infor
                                rec_bill_detail['billPackages'] = list_bill_package
                                rec_bill_detail['billService'] = result_service_rel_arr
                                arrBillLadingDetail.append(rec_bill_detail)
                            query = """
                                SELECT id
                                FROM public.sharevan_bill_lading_detail where bill_lading_id = %s and warehouse_type ='0'
                                    and status_order = 'running'
                                                """
                            http.request.env[BillLadingDetail._name]._cr.execute(query, (bill_lading_id,))
                            origin_records = http.request.env[BillLadingDetail._name]._cr.dictfetchall()
                            val['origin_bill_lading_detail_id'] = origin_records[0]['id']
                            jsonListUrl = []
                            getUrl_query = """
                                SELECT json_agg(t) FROM (
                                    select irc.uri_path from ir_attachment irc
                                        join public.ir_attachment_sharevan_routing_plan_day_rel pi on pi.ir_attachment_id = irc.id
                                        join sharevan_routing_plan_day srpd on pi.sharevan_routing_plan_day_id = srpd.id and srpd.bill_lading_detail_id= %s 
                                    and srpd.status = '4'
                                        ) t """
                            self.env.cr.execute(getUrl_query, (origin_records[0]['id'],))
                            get_list_images_or_attachment_url = self._cr.fetchall()
                            if get_list_images_or_attachment_url:
                                if get_list_images_or_attachment_url[0][0]:
                                    for rec in get_list_images_or_attachment_url[0][0]:
                                        jsonListUrl.append(rec['uri_path'])
                            val['image_urls'] = jsonListUrl
                            val['arrBillLadingDetail'] = arrBillLadingDetail
                            records = {
                                'length': 1,
                                'records': [val]
                            }
                            simplejson.dumps(records, indent=4, sort_keys=True, default=str)
                            return records
                else:
                    raise ValidationError('Bill of lading detail not found')
            else:
                raise ValidationError('Bill of lading detail not found')

    def send_notification_success(self):
        content = {
            'title': "You successfully created a new bill of lading " + self.name,
            'content': "Your bill of lading have been created successful! Bill code : " + self.name,  # cập nhật sau
            'res_id': self.id,
            'res_model': self._name,
            'user_id': [self.env.uid],
            'click_action': ClickActionType.customer_bill_lading_detail.value,
            'message_type': MessageType.success.value,
            'type': NotificationType.RoutingMessage.value,
            'object_status': RoutingDetailStatus.Done.value,
            'item_id': self.id,
        }
        http.request.env['sharevan.notification'].sudo().create(content)

    @api.depends('week_choose')
    def _compute_week_choose(self):
        for record in self:
            record.week_choose = str(record.day_of_week)

    @api.depends('day_of_week_view')
    def _compute_day_of_week_view(self):
        for record in self:
            record.day_of_week_view = str(record.day_of_week)

            # [('0', 'Chủ nhật'), ('1', 'Thứ hai'), ('2', 'Thứ ba'),
            #  ('3', 'Thứ tư'), ('4', 'Thứ năm'), ('5', 'Thứ sáu'), ('6', 'Thứ bảy')],


class BillLadingDetail(models.Model):
    _name = 'sharevan.bill.lading.detail'
    MODEL = 'sharevan.bill.lading.detail'
    _description = 'bill of lading detail'

    name_seq = fields.Char(string='Bill of lading detail Code', required=True, copy=False, readonly=True,
                           index=True,
                           default=lambda self: _('New'))
    qr_code = fields.Image('QR code')
    qr_char = fields.Char('QR char', related='name_seq')
    bill_lading_id = fields.Many2one('sharevan.bill.lading', 'Bill of lading', index=True, required=True)
    total_weight = fields.Float('Total weight', compute='_compute_total_weight', store=True)
    warehouse_id = fields.Many2one('sharevan.warehouse', 'Warehouse')
    warehouse_type = fields.Selection([('0', 'Nhận hàng'), ('1', 'Trả hàng')],
                                      'Job type', default='0', required=True)
    user_id = fields.Integer(string='User warehouse', help='Warehouse management account L1')
    from_bill_lading_detail_id = fields.Many2one('sharevan.bill.lading.detail', 'From bill of lading detail')
    description = fields.Text('Description', default='')
    service_id = fields.Many2many('sharevan.service.type', domain=[('status', '=', 'running')],
                                  string='Service Type')
    expected_from_time = fields.Datetime('Expected from time'
                                         # required=True, default=datetime.today()
                                         )
    expected_to_time = fields.Datetime('Expected to time'
                                       # required=True, default=datetime.today()
                                       )
    from_time = fields.Float('From time', digits=(16, 2), group_operator="avg", store=False)
    to_time = fields.Float('To time', digits=(16, 2), group_operator="avg", store=False)
    name = fields.Char('Bill of lading code')
    status = fields.Selection(
        [('0', 'Chưa định tuyến'),
         ('1', 'Đã định tuyến')],
        string='Status', context={'status': '1'}, default='1', required=True)
    approved_type = fields.Selection(
        [('0', 'Chưa xác nhận'),
         ('1', 'Đã xác nhận')
         ],
        string='approved type', context={'approved_type': '1'}, default='0', required=True)
    from_warehouse_id = fields.Many2one('sharevan.warehouse', 'From warehouse')
    latitude = fields.Float(string='Geo Latitude', digits=(16, 5))
    longitude = fields.Float(string='Geo Longitude', digits=(16, 5))
    price = fields.Float(string='Price')
    area_id = fields.Many2one('sharevan.area', string='Area')
    order_type = fields.Selection(
        [('0', 'Trong zone'),
         ('1', 'Ngoài zone')
         ],
        string='Order type', context={'status': '1'}, default='0', required=True, readonly=True)
    zone_area_id = fields.Many2one('sharevan.zone', string='Zone')
    zoneAreaId = fields.Integer('zoneAreaId', store=False)
    wjson_address = fields.Char('address json', store=False)
    warehouse_name = fields.Char('Warehouse Name', required=True)
    address = fields.Text('Address', required=True)
    status_order = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted'),
         ('draft', 'Draft')
         ],
        string='Status Order', context={'status_order': 'running'}, default='running', required=True)
    bill_package_line = fields.One2many('sharevan.bill.package', 'bill_lading_detail_id', string='Bill package',
                                        copy=True, domain=[('status', '=', 'running')],
                                        auto_join=True)
    bill_package_import = fields.One2many('sharevan.bill.package', 'bill_lading_detail_id',
                                          string='Bill package import', store=False)
    depot_id = fields.Many2one('sharevan.depot', string='Depot')
    hub_id = fields.Many2one('sharevan.hub', 'Hub')
    street = fields.Char('Street', store=False, required=True)
    street2 = fields.Char('Street2', store=False)
    city_name = fields.Char('City', store=False)
    zip = fields.Char('Zip', store=False)
    phone = fields.Char('Phone', required=True)
    state_id = fields.Many2one('sharevan.area', 'Province', store=False, domain=lambda
        self: "[('country_id', '=', country_id),('location_type','=','province'),"
              "('status','=','running')]")

    country_id = fields.Many2one('res.country', 'Country', store=False)
    district = fields.Many2one('sharevan.area', 'District', store=False, domain=lambda
        self: "[('country_id', '=', country_id),"
              "('location_type','=','district'),"
              "('status','=','running')]")
    ward = fields.Many2one('sharevan.area', 'Ward', store=False,
                           domain=lambda
                               self: "[('country_id', '=', country_id),('location_type','=','township'),('status','=','running')]")
    last_scan = fields.Datetime('last scan')
    packaged_into_cargo = fields.Boolean('Package into cargo', default=False)
    min_price = fields.Float()
    max_price = fields.Float()
    total_volume = fields.Float('Total volume')
    express_distance = fields.Float('Distance', store=False)

    def compute_display_from_depot(self):
        # This will be called every time the field is viewed
        for detail in self:
            if detail.warehouse_type == WarehouseType.Export.value:
                detail.from_depot_id = detail.from_bill_lading_detail_id.depot_id
            else:
                detail.from_depot_id = False

    from_depot_id = fields.Many2one(Constants.SHAREVAN_DEPOT, 'from depot id', compute=compute_display_from_depot,
                                    store=False)

    @api.model
    def create(self, vals):
        seq = BaseMethod.get_new_sequence('sharevan.bill.lading.detail', 'SBLD', 12, 'name_seq')
        vals['name'] = seq
        vals['name_seq'] = seq
        vals['qr_code'] = FileApi.build_qr_code(vals['name_seq'])
        if 'service_id' in vals:
            ids = []
            for sv in vals['service_id']:
                if len(sv) > 2 and isinstance(sv[2], dict):
                    if 'id' in sv[2]:
                        ids.append(sv[2]['id'])
                        sv[0] = 6
                        sv[1] = False
                        sv[2] = [sv[2]['id'], ]
                    else:
                        sv[2].pop('service_id')
            if len(ids) > 0:
                temp = [6, False, ids]
                vals['service_id'] = [temp]
        result = super(BillLadingDetail, self).create(vals)
        return result

    @api.depends('bill_package_line', 'bill_package_import')
    def _compute_total_weight(self):
        for record in self:
            if record.warehouse_type == '0':
                list_package = record.bill_package_line
            else:
                list_package = record.bill_package_import
            total_weight = 0.0
            for package in list_package:
                if not package.quantity_package or package.quantity_package == 0 or package.status == 'deleted':
                    continue
                total_weight += package.net_weight * package.quantity_package
            record.total_weight = total_weight

    def get_list_date(self, from_date, to_date):
        # query = """
        #     SELECT date_trunc('day',t.expected_from_time) as expected_from_time,
        # 	        date_trunc('day',t.expected_to_time) as expected_to_time
        #     FROM sharevan_bill_lading_detail as t
        #     WHERE not(t.expected_from_time > %s and t.expected_to_time < %s)
        # """

        query = """
                    SELECT t.expected_from_time, 
        			        t.expected_to_time
                    FROM sharevan_bill_lading_detail as t
                    WHERE not(t.expected_from_time > %s and t.expected_to_time < %s) and status_order = 'running'
                """

        self._cr.execute(query, (to_date, from_date,))
        records = self._cr.fetchall()
        format = '%Y-%m-%d'
        # fromDate = datetime.strptime(from_date, format)
        # toDate = datetime.strptime(to_date, format)
        delta = timedelta(days=1)
        ret = dict()
        for rec in records:

            min_fdate = max(rec[0], from_date)
            max_tdate = min(rec[1], to_date)
            while min_fdate <= max_tdate:
                ret[min_fdate] = '1'
                min_fdate += delta

        return list(ret.keys())

    def list_by_date(self, date):
        domain = [('expected_from_time', '<=', date), ('expected_to_time', '>=', date)]
        self.isObject = True

        bill_details = self.search_read(domain=domain)
        bill_ladings = dict()
        # bill_ladings_ret = []
        for item in bill_details:
            temp = self.env[BillLading._name].sudo().browse(item['bill_lading_id'][0]).read()
            if temp:
                temp = temp[0]

                details = []
                if temp['id'] in bill_ladings:
                    bill_lading = bill_ladings[temp['id']]
                else:
                    bill_lading = temp
                    bill_ladings[temp['id']] = bill_lading

                if 'billLadingDetails' in bill_lading:
                    details = bill_lading['billLadingDetails']
                else:
                    details = []
                    bill_lading['billLadingDetails'] = details
                details.append(item)
                # item['billLading'] = bill_lading
        return list(bill_ladings.values())

    @api.onchange('street')
    def _onchange_street(self):
        for record in self:
            street = record.street
            district = record.district
            city_name = record.city_name
            state = record.state_id
            country = record.country_id
            ward = record.ward
            area_id = record.area_id
            update_params = {}
            # update: if street input value invalid, reset all address values
            if street == '' or (record.warehouse_id and record.street not in record.warehouse_id.address):
                update_params = {
                    'district': False,
                    'city_name': '',
                    'state_id': False,
                    'ward': False,
                    'country_id': False,
                    'address': '',
                    'area_id': False,
                    'zone_area_id': False,
                    'depot_id': False,
                    'hub_id': False,
                    'warehouse_id': False,
                    'phone': False
                }
                record.update(update_params)
            else:
                if ward:
                    address = street + ' - ' + ward.name
                    area_id = ward
                    if district:
                        address = address + ' - ' + district.name
                    if city_name:
                        if city_name != '':
                            address = address + ' - ' + city_name
                    if state:
                        if city_name is False:
                            address = address + ' - ' + state.name
                    if country:
                        address = address + ' - ' + country.name
                else:
                    address = street
                    if district:
                        area_id = district
                        address = address + ' - ' + district.name
                    if city_name:
                        if city_name != '':
                            address = address + ' - ' + city_name
                    if state:
                        if city_name is False:
                            address = address + ' - ' + state.name
                    if country:
                        address = address + ' - ' + country.name
                if area_id is False:
                    raise ValidationError('Area not found')
                update_params['zone_area_id'] = area_id.zone_area_id.id
                update_params['area_id'] = area_id
                update_params['hub_id'] = area_id.hub_id.id
                update_params['depot_id'] = area_id.zone_area_id.depot_id.id
                update_params['address'] = address
            record.update(update_params)

    @api.onchange('state_id', 'district', 'ward')
    def _onchange_state_id(self):
        for record in self:
            street = record.street
            if street:
                district = record.district
                city_name = record.city_name
                state = record.state_id
                country = record.country_id
                ward = record.ward
                area_id = record.area_id
                if ward:
                    address = street + ' - ' + ward.name
                    area_id = ward
                    if district:
                        address = address + ' - ' + district.name
                    if city_name:
                        if city_name != '':
                            address = address + ' - ' + city_name
                    if state:
                        if city_name is False:
                            address = address + ' - ' + state.name
                    if country:
                        address = address + ' - ' + country.name
                else:
                    address = street
                    if district:
                        area_id = district
                        address = address + ' - ' + district.name
                    if city_name:
                        if city_name != '':
                            address = address + ' - ' + city_name
                    if state:
                        if city_name is False:
                            address = address + ' - ' + state.name
                    if country:
                        address = address + ' - ' + country.name
                if area_id is False:
                    raise ValidationError('Area not found')
                record.update({'area_id': area_id})
                record.update({'zone_area_id': area_id.zone_area_id.id})
                record.update({'hub_id': area_id.hub_id.id})
                record.update({'depot_id': area_id.zone_area_id.depot_id.id})
                record.update({'address': address})

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        # get zone import
        import_depot_id = 0
        for record in self.bill_lading_id.bill_lading_detail_ids:
            if record.warehouse_type == '0':
                import_depot_id = record.depot_id.id
                break
        selected_warehouse = []
        for record in self:
            if record.warehouse_id:
                # check if this warehouse is already chosen
                if record.warehouse_id.id not in selected_warehouse:
                    selected_warehouse.append(record.warehouse_id.id)
                else:
                    raise ValidationError("%s is already chosen!".format(record.warehouse_name))
                if import_depot_id != 0 and record.warehouse_id.area_id.zone_area_id.depot_id.id != import_depot_id:
                    record.order_type = "1"
                else:
                    record.order_type = "0"
                if record.warehouse_id.ward:
                    address = record.warehouse_id.address
                    area_id = record.warehouse_id.area_id.id
                    country_id = record.warehouse_id.country_id.id
                    state_id = record.warehouse_id.state_id.id
                    ward = record.warehouse_id.ward.id
                    record.update({'ward': ward})
                else:
                    address = record.warehouse_id.address
                    area_id = record.warehouse_id.area_id.id
                    country_id = record.warehouse_id.country_id.id
                    state_id = record.warehouse_id.state_id.id
                address_temp = address.split('-')
                update_params = {
                    'phone': record.warehouse_id.phone,
                    'zone_area_id': record.warehouse_id.area_id.zone_area_id.id,
                    'area_id': area_id,
                    'hub_id': record.warehouse_id.area_id.hub_id.id,
                    'depot_id': record.warehouse_id.area_id.zone_area_id.depot_id.id,
                    'state_id': state_id,
                    'latitude': record.warehouse_id.latitude,
                    'longitude': record.warehouse_id.longitude,
                    'district': record.warehouse_id.district.id,
                    'country_id': country_id,
                    'warehouse_name': record.warehouse_id.name,
                    'address': address,
                    'street': address_temp[0]
                }
                record.update(update_params)

            else:
                update_params = {
                    'district': False,
                    'city_name': '',
                    'state_id': False,
                    'ward': False,
                    'country_id': False,
                    'address': '',
                    'area_id': False,
                    'zone_area_id': False,
                    'depot_id': False,
                    'hub_id': False,
                    'phone': False,
                    'warehouse_name': False,
                    'latitude': False,
                    'longitude': False,
                }
                record.update(update_params)

    @api.onchange('warehouse_type')
    def _onchange_warehouse_type(self):
        import_depot_id = 0
        for record in self.bill_lading_id.bill_lading_detail_ids:
            if record.warehouse_type == '0':
                import_depot_id = record.depot_id.id
                break
        for record in self:
            if import_depot_id != 0 and record.warehouse_id.area_id.zone_area_id.depot_id.id != import_depot_id:
                record.order_type = "1"
            else:
                record.order_type = "0"
        list_pk = []
        quantity_map = {}
        for record in self.bill_lading_id.bill_lading_detail_ids:
            if record.warehouse_type == '0' and record.bill_package_line:
                for pk in record.bill_package_line:
                    quantity_map[str(pk.id)] = pk.quantity_package
        for detail in self.bill_lading_id.bill_lading_detail_ids:
            if detail.warehouse_type == '1':
                for pk in detail.bill_package_line:
                    if str(pk.from_bill_package_id) in quantity_map:
                        quantity_map[str(pk.id)] -= pk.quantity_package
        ind = 1
        for record in self.bill_lading_id.bill_lading_detail_ids:
            if record.warehouse_type == '0' and record.bill_package_line:
                for pk in record.bill_package_line:
                    pk_copy = pk.copy_data()[0]
                    pk_copy['quantity_package'] = 0
                    pk_copy['total_quantity'] = quantity_map[str(pk.id)]
                    pk_copy['from_bill_package_id'] = pk.id
                    pk_copy['key_map'] = ind
                    pk.key_map = ind
                    pk.quantity_package = 9999
                    ind += 1
                    list_pk.append(pk_copy)
                break
        for record in self.bill_lading_id.bill_lading_detail_ids:
            if record.warehouse_type == '1' and str(record.id) == str(self.id):
                list_obj = self.env['sharevan.bill.package'].create(list_pk)
                record.bill_package_import = list_obj

    @api.model
    def search_bill_detail(self, domain=None, fields=[], offset=0, limit=10, order=[], count=False):
        select_query = """
            select bill.id as id, bill.name_seq as name_seq, bill.status as status, 
                from_detail.address as address1, to_detail.address as address2
        """
        from_query = """
            from sharevan_bill_lading bill
            left join sharevan_bill_lading_detail from_detail 
                on from_detail.bill_lading_id = bill.id and from_detail.warehouse_type = '0'
            left join sharevan_bill_lading_detail to_detail 
                on to_detail.bill_lading_id = bill.id and to_detail.warehouse_type = '1'
        """
        groupby_query = " group by bill.id, from_detail.address, to_detail.address "
        params = []
        where_clause = " where 1=1 "
        for f in domain:
            where_clause += " and "
            if f[0] == 'name_seq':
                where_clause += " bill.name_seq "
            elif f[0] == "address1":
                where_clause += " from_detail.address "
            elif f[0] == "address2":
                where_clause += " to_detail.address "
            elif f[0] == "date_plan":
                where_clause += ""

            if f[1] == "ilike":
                where_clause += " ilike "
            else:
                where_clause += " = "

            where_clause += " %s "
            params.append("%" + f[2] + "%")

        extra = groupby_query + (" order by {order_by}" if order else " ")
        parsed_orderby = ""
        for od in order:
            column = ""
            if od['name'] == "id":
                column = "bill.id"
            parsed_orderby += column + " " + ("ASC" if od['asc'] else "DESC")
        # params.append(parsed_orderby.strip())
        search_query = select_query + from_query + where_clause + extra
        if count:
            search_query = "select count(t.*) from (" + search_query + " ) as t"
        else:
            search_query += " limit %s "
            params.append(limit)
            if offset > 0:
                search_query += " offset + {offset} "
        self.env.cr.execute(search_query.strip().format(order_by=parsed_orderby, offset=offset), params)
        if count:
            count_res = self.env.cr.dictfetchall()
            if count_res:
                return count_res[0]['count']
            else:
                return 0

        else:
            return self.env.cr.dictfetchall()


class BillPackage(models.Model):
    _name = 'sharevan.bill.package'
    MODEL = 'sharevan.bill.package'
    _description = 'bill package'

    name = fields.Char("Bill package name", default="New")
    item_name = fields.Text('Item name')
    bill_lading_detail_id = fields.Many2one('sharevan.bill.lading.detail', 'Bill of lading detail', index=True)
    net_weight = fields.Float('Net weight')
    quantity_package = fields.Integer('Quantity Package')
    total_quantity = fields.Integer('Total quantity')
    length = fields.Float('Length')
    width = fields.Float('Width')
    height = fields.Float('Height')
    capacity = fields.Integer('Capacity')
    description = fields.Text('Description')
    key_map = fields.Char("Key Map")
    commodities_type = fields.Char("Commodities type", store=False)
    product_type_id = fields.Many2one('sharevan.product.type', 'Product type')
    product_type_name = fields.Char('Product type name', store=False)
    status = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted'),
         ('draft', 'Draft')
         ],
        string='Status', context={'status': 'running'}, default='running', required=True)
    qr_code = fields.Image("Image", max_width=512, max_height=512)
    zone_area_id = fields.Many2one(related='bill_lading_detail_id.zone_area_id', store=False)
    from_bill_package_id = fields.Many2one('sharevan.bill.package', 'Bill Package')

    def unlink(self):
        for record in self:
            record.write({
                'status': 'deleted'
            })
        return self

    @api.model
    def create(self, vals):
        if vals.get('name_seq', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'self.sharevan.bill.package.name') or 'New'
        if 'product_type_id' in vals and isinstance(vals['product_type_id'], dict):
            if 'id' in vals['product_type_id']:
                vals['product_type_id'] = vals['product_type_id']['id']
            else:
                vals.pop('product_type_id')
        if 'origin_bill_package' in vals:
            vals.pop('origin_bill_package')
        if 'from_change_bill_package_id' in vals:
            vals.pop('from_change_bill_package_id')
        if 'qrChecked' in vals:
            vals.pop('qrChecked')
        if 'quantityQrChecked' in vals:
            vals.pop('quantityQrChecked')
        result = super(BillPackage, self).create(vals)
        result.generate_qr()
        return result

    def generate_qr(self):
        if qrcode and base64:
            if not self.name:
                prefix = str(
                    self.env['ir.config_parameter'].sudo().get_param('customer_product_qr.config.customer_prefix'))
                if not prefix:
                    raise UserError(_('Set A Customer Prefix In General Settings'))
                self.name = self.env['ir.sequence'].next_by_code('self.sharevan.bill.package.name') or '/'
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr_data = {
                "zone_area_id": self.bill_lading_detail_id.id,
                "bill_package_name": self.name
            }
            qr.add_data(qr_data)
            qr.make(fit=True)

            img = qr.make_image()
            temp = BytesIO()
            img.save(temp, format="PNG")
            qr_image = base64.b64encode(temp.getvalue())
            self.write({'qr_code': qr_image})
        else:
            raise UserError(_('Necessary Requirements To Run This Operation Is Not Satisfied'))

    @api.onchange('quantity_package')
    def _onchange_quantity(self):
        for record in self:
            if record.quantity_package < 0:
                record.quantity_package = 0
            if record.bill_lading_detail_id.warehouse_type == '1' and record.quantity_package > record.total_quantity:
                record.quantity_package = record.total_quantity
                raise ValidationError("Quantity must be lower or equal to total quantity")

    @api.constrains('quantity_package')
    def _onchange_quantity(self):
        for record in self:
            if record.quantity_package < 0:
                record.quantity_package = 0

    @api.onchange('height')
    def _onchange_height(self):
        for record in self:
            if record.height < 0:
                record.height = 0.0

    @api.onchange('length')
    def _onchange_length(self):
        for record in self:
            if record.length < 0:
                record.length = 0.0

    @api.onchange('width')
    def _onchange_width(self):
        for record in self:
            if record.width < 0:
                record.width = 0.0

    @api.onchange('width')
    def _onchange_net_weight(self):
        for record in self:
            if record.net_weight < 0:
                record.net_weight = 0.0


class BillPackageType(models.Model):
    _name = 'sharevan.product.package.type'
    MODEL = 'sharevan.product.package.type'
    _description = 'product package type'

    name_seq = fields.Char(string='Product package type Code', required=True, copy=False, readonly=True,
                           index=True,
                           default=lambda self: _('New'))
    net_weight = fields.Float('Net weight')
    name = fields.Char('Product package type')
    length = fields.Float('Length')
    width = fields.Float('Width')
    height = fields.Float('Height')
    capacity = fields.Integer('Capacity')
    description = fields.Text('Description')
    status = fields.Selection(
        [('running', 'Running'), ('deleted', 'Deleted'),
         ('draft', 'Draft')], string='Status',
        default='running', required=True)

    def unlink(self):
        record_ids = self.env['sharevan.product.package.type'].search([('name_seq', '=', self.name_seq)])
        for record in record_ids:
            record.write({
                'status': 'deleted'
            })
        return self


class BillService(models.Model):
    _name = 'sharevan.bill.service'
    MODEL = 'sharevan.bill.service'
    _description = 'bill service'
    _rec_name = 'service_name'

    service_code = fields.Char('Service code')
    service_name = fields.Char('Service name')
    service_type = fields.Many2one('sharevan.service.type',
                                   'Service type')
    price = fields.Float('Price')
    package_quantity = fields.Integer('Package Quantity')
    description = fields.Html('Description', sanitize_style=True)
    phone = fields.Char('Phone')
    status = fields.Selection(
        [('running', 'Running'),
         ('stopped', 'Stopped')],
        string='Status')
    vendor_id = fields.Many2one(
        'res.partner', 'Vendor')


class SharevanServiceType(models.Model):
    _name = 'sharevan.service.type'
    MODEL = 'sharevan.service.type'
    _description = 'Sharevan Service Type'

    name = fields.Char(required=True, translate=True)
    # category = fields.Selection([
    #     ('service', 'Service'),
    #     ('warehouse', 'Service warehouse')
    # ], 'Category', required=True, help='Choose whether the service refer to contracts, vehicle services or both')
    price = fields.Float(string='Cost', digits=(12, 3), required=True)
    vendor_id = fields.Many2one('sharevan.vendor', 'Vendor', required=True,
                                domain=[('type', '=', 'vendor_service'), ('status', '=', 'running')])
    service_code = fields.Char(string='Service_code', required=True, copy=False, readonly=True, index=True,
                               default=lambda self: _('New'))

    status = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted')
         ],
        string='Status', required=True, default='running')

    description = fields.Html('Description', sanitize_style=True)

    @api.constrains('price')
    def _check_price(self):
        if self.price <= 0.0:
            raise ValidationError(_('Price must be greater than 0'))

    @api.model
    def create(self, vals):
        if vals.get('service_code', 'New') == 'New':
            vals['service_code'] = self.env['ir.sequence'].next_by_code(
                'sharevan.service.type') or 'New'
            result = super(SharevanServiceType, self).create(vals)
            return result

    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.service.type'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })
        return self


class ShareVanInsurance(models.Model):
    MODEL = 'sharevan.insurance'

    _name = 'sharevan.insurance'

    _description = 'DLP Insurance'

    name = fields.Char('Insurance Name', required=True, translate=True)
    amount = fields.Float('Insurance Price', required=True)
    package_percent = fields.Float('Package Percent')
    package_amount = fields.Float('Package Amount')
    description = fields.Html('Description', sanitize_style=True)
    vehicle_id = fields.Many2one('fleet.vehicle')
    insurance_type = fields.Selection(
        [('0', 'Package'),
         ('1', 'Vehicle'),
         ],
        string='Insurance type', required=True)
    duration = fields.Selection(
        [('0', '6 months'),
         ('1', '1 year'),
         ('2', '2 year'),
         ('3', '3 year'),
         ('4', '4 year'),
         ('5', '5 year')
         ],
        string='Duration')

    start_date = fields.Date('Start date')
    start_end = fields.Date('End date')
    package_type = fields.Selection(
        [('0', 'Bronze'),
         ('1', 'Silver'),
         ('2', 'Gold'),
         ('3', 'Premium'),
         ('4', 'Diamond')],
        string='Package Type', required=True)

    @api.onchange('amount')
    def onchange_amount(self):
        if self.amount < 0:
            raise ValidationError(_('Insurance Price must have a value greater than 0!'))

    @api.onchange('duration')
    def onchange_duration(self):
        for record in self:
            record.update({
                'start_date': False,
                'start_end': False
            })

            if record['duration'] == '0' and record['start_date'] != False:
                record['start_end'] = record['start_date'] + timedelta(days=183)
            if record['duration'] == '1' and record['start_date'] != False:
                record['start_end'] = record['start_date'] + timedelta(days=365)
            if record['duration'] == '2' and record['start_date'] != False:
                record['start_end'] = record['start_date'] + timedelta(days=730)
            if record['duration'] == '3' and record['start_date'] != False:
                record['start_end'] = record['start_date'] + timedelta(days=1095)
            if record['duration'] == '4' and record['start_date'] != False:
                record['start_end'] = record['start_date'] + timedelta(days=1460)
            if record['duration'] == '5' and record['start_date'] != False:
                record['start_end'] = record['start_date'] + timedelta(days=1825)

    @api.onchange('start_end')
    def onchange_start_end(self):
        for record in self:

            if record['start_end'] is False or record['start_date'] is False:
                record.update({
                    'start_date': False
                })
            elif record['start_end'] <= record['start_date'] and record['start_date'] != False and record[
                'start_end'] != False:
                raise ValidationError('The end date must be greater than the start date !')

    # @api.constrains('start_date')
    # def _constrains(self):
    #     for record in self:
    #         message = ""
    #         if record.start_date and record.start_date < datetime.today().date():
    #             notice = "Sorry, The start date must be greater than or equal to the current date..."
    #             message += notice + "\n"
    #         message = message.strip()
    #         if message:
    #             raise ValidationError(message)

    @api.onchange('start_date')
    def onchange_start_date(self):
        for record in self:

            if record['start_date'] is False:
                record.update({
                    'start_date': False,
                    'start_end': False
                })
            elif record['duration'] != False:
                if record['duration'] == '0':
                    record['start_end'] = record['start_date'] + timedelta(days=183)
                if record['duration'] == '1':
                    record['start_end'] = record['start_date'] + timedelta(days=365)
                if record['duration'] == '2':
                    record['start_end'] = record['start_date'] + timedelta(days=730)
                if record['duration'] == '3':
                    record['start_end'] = record['start_date'] + timedelta(days=1095)
                if record['duration'] == '4':
                    record['start_end'] = record['start_date'] + timedelta(days=1460)
                if record['duration'] == '5':
                    record['start_end'] = record['start_date'] + timedelta(days=1825)
                if record['start_date'] >= record['start_end'] and record['start_date'] != False and record[
                    'start_end'] != False:
                    raise ValidationError('Start date must be less than end date !')

            elif record['start_date'] != False and record['start_end'] != False:
                if record['start_date'] >= record['start_end']:
                    raise ValidationError('Start date must be less than end date !')

    @api.onchange('package_percent')
    def onchange_package_percent(self):
        if self.package_percent < 0:
            raise ValidationError(_(' package_percent  > 0'))

    @api.onchange('package_amount')
    def onchange_package_amount(self):
        if self.package_amount < 0:
            raise ValidationError(_(' package_amount  > 0'))

    status = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted')
         ],
        default='running',
        string='Status', required=True)

    vendor_id = fields.Many2one('sharevan.vendor', 'Vendor', required=True,
                                domain=[('type', '=', 'vendor_insurance'), ('status', '=', 'running')])
    deductible = fields.Char('Deductible', required=True)
    insurance_code = fields.Char(string='Insurance Code', required=True, copy=False, readonly=True, index=True,
                                 default=lambda self: _('New'))

    @api.onchange('vendor_id')
    def onchange_vendor(self):
        if self.vendor_id['type']:
            if self.vendor_id['type'] != 'vendor_insurance':
                raise ValidationError(_('Required to be an insurance provider!'))

    @api.model
    def create(self, vals):
        seq = BaseMethod.get_new_sequence('sharevan.insurance', 'ISR', 6, 'insurance_code')
        vals['insurance_code'] = seq
        result = super(ShareVanInsurance, self).create(vals)
        return result

    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.insurance'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })

        return self


class Subscribe(models.Model):
    _name = "sharevan.subscribe"
    MODEL = "sharevan.subscribe"

    _description = 'Subscribe the bill of lading regularly'
    _order = 'subscribe_code'

    name = fields.Char(string='Subscribe Name', required=True)
    subscribe_code = fields.Char(string='Subscribe code', required=True, copy=False, readonly=True, index=True,
                                 default=lambda self: _('New'))
    isRepeat = fields.Boolean(string='Repeat')
    description = fields.Html('Description', sanitize_style=True)
    value = fields.Integer(string='Value', required=True)
    status = fields.Selection(
        [('running', 'Running'),
         ('deleted', 'Deleted')
         ],
        default='running',
        string='Status', required=True)

    @api.constrains('value')
    def onchange_value(self):
        for record in self:
            if record['value'] <= 0:
                raise ValidationError('Value must bigger than 0 !')

    @api.model
    def create(self, vals):
        if vals.get('subscribe_code', 'New') == 'New':
            vals['subscribe_code'] = self.env['ir.sequence'].next_by_code(
                'sharevan.subscribe') or 'New'
            result = super(Subscribe, self).create(vals)
            return result

    @api.model
    def create(self, vals):
        seq = BaseMethod.get_new_sequence('sharevan.subscribe', 'SUB', 6, 'subscribe_code')
        vals['subscribe_code'] = seq
        result = super(Subscribe, self).create(vals)
        return result

    def unlink(self):
        for id in self.ids:
            record = self.env['sharevan.subscribe'].search([('id', '=', id)])
            record.write({
                'status': 'deleted'
            })
        return self
