import itertools
import json
from datetime import datetime, timedelta

from mymodule.base_next.models.notification import Notification
from mymodule.enum.ClickActionType import ClickActionType
from mymodule.enum.MessageType import MessageType
from mymodule.enum.NotificationType import NotificationType
from mymodule.enum.VehicleStateStatus import VehicleStateStatus
from odoo import api, fields, models, http
from odoo.exceptions import AccessError, ValidationError


class RequestTimeOff(models.Model):
    _name = 'fleet.request.time.off'
    _description = 'Fleet request time off'
    _inherit = 'fleet.request.time.off'

    def _check_can_approve(self):
        today = datetime.now().today().date()
        time_limit = int(http.request.env['ir.config_parameter'].sudo().get_param('driver.request.time.limit'))
        list_exceed = []
        for record in self:
            first_day = record.group_request_id.start_day
            # if create request the day before, must be before time_limit(hour of day)
            if time_limit and 0 <= time_limit <= 24 and (first_day + timedelta(
                    days=-1)) == today and datetime.now().today().hour >= time_limit:
                record.can_approve = False
                list_exceed.append(record.id)
        if len(list_exceed) == len(self):
            return
        if self.env.user.channel_id.channel_type == 'manager':
            for record in self:
                # 1 day before request day but already past time limit
                if record.id in list_exceed:
                    continue
                # request day < today
                if record.status != '1' or record.request_day < datetime.today().date():
                    record.can_approve = False
                    continue
                # manager type can approve anyone's request
                record.can_approve = True
        else:
            sql = """
                    select
                        driver.fleet_driver_id
                    from
                        fleet_management_driver_temp driver
                    inner join fleet_management_driver_temp manager on
                        driver.fleet_management_id = manager.fleet_management_id
                        and manager.status = 'active'
                        and LOWER(manager.type) = 'manager'
                    inner join fleet_driver fd on
                        fd.id = manager.fleet_driver_id
                        and fd.user_id = %s
                    where
                        1=1
                        and driver.status = 'active'
                        and LOWER(driver.type) = 'driver'
                """
            self.env.cr.execute(sql, [self.env.user.id])
            res = self.env.cr.fetchall()
            if res:
                res = [i for i in itertools.chain(*res)]
            for record in self:
                # 1 day before request day but already past time limit
                if record.id in list_exceed:
                    continue
                # request day < today
                if record.status != '1' or record.request_day < datetime.today().date():
                    record.can_approve = False
                    continue
                # if this user is allowed to approve this request
                if record.driver_id.id in res:
                    record.can_approve = True
                    continue
                record.can_approve = False

    def deny_request(self):
        self.group_request_id.deny_request()

    def approve_request(self):
        self.group_request_id.approve_request()

    def _check_all_day(self):
        for record in self:
            if record.type == '1':
                record.all_day = True
            else:
                record.all_day = False


class GroupRequestTO(models.Model):
    # 'to' = time off
    _name = 'fleet.group.request.to'
    _inherit = 'fleet.group.request.to'

    @api.model
    def create(self, vals):
        try:
            self.validate_request(vals)
            list_day = vals['request_days']
            list_request = []
            len_days = len(list_day)
            index = 0
            for request_day in list_day:
                if 'days_update' in vals \
                        and datetime.strptime(request_day['date_value'], "%Y-%m-%d") in vals['days_update']:
                    index += 1
                    continue
                if len_days > 1 and index == 0 and request_day['type'] == "2":
                    raise ValidationError("Invalid start of multiple day off")
                if len_days > 1 and index == len_days - 1 and request_day['type'] == "3":
                    raise ValidationError("Invalid end of multiple day off")
                param = {
                    'request_day': request_day['date_value'],
                    'type': request_day['type'] if 'type' in request_day else "1",
                    'company_id': self.env.company.id,
                    'driver_id': vals['driver_id'],
                }
                list_request.append((0, False, param))
                index += 1
            if len(list_request) > 0 or 'res_update' in vals:
                create_params = [{
                    'list_day_request': list_request,
                    'driver_id': vals['driver_id'],
                    'start_day': vals['start_day'],
                    'end_day': vals['end_day'],
                    'reason': vals['reason'],
                    'company_id': self.env.company.id,
                    'status': "1"
                }]
                res = super(GroupRequestTO, self).create(create_params)
                if res:
                    if 'res_update' in vals:
                        list_update = vals['res_update']
                        for obj in list_update:
                            obj.write({'group_request_id': res.id})
                    return str(res['id'])
                else:
                    self.env.cr.rollback()
                    return '0'
            else:
                self.env.cr.rollback()
                return '0'
        except Exception:
            self.env.cr.rollback()
            raise

    @api.model
    def deny_from_calendar(self, request_id):
        request = self.search(args=[('list_day_request.id', '=', request_id)])
        if request:
            return request.deny_request()

    @api.model
    def approve_from_calendar(self, request_id):
        request = self.search(args=[('list_day_request.id', '=', request_id)])
        if request:
            return request.approve_request()

    def get_time_range(self):
        time_range = ""
        if self.start_day == self['end_day']:
            time_range = self.start_day
        else:
            time_range = "from " + str(self.start_day) + " to " + str(self.end_day)
        return time_range

    def approve_request(self):
        try:
            if not self.list_day_request[0].can_approve:
                raise AccessError("You don't have the permission to perform this action")
            lst_assigned = self.env['fleet.vehicle.assignation.log']. \
                search([('driver_id', '=', self.driver_id.id), ('give_car_back', '=', None),
                        ('date_start', '<=', self.end_day), ('date_end', '>=', self.start_day)])
            if lst_assigned:
                # delete assignation and free vehicle
                available_state = self.env['fleet.vehicle.state']. \
                    search([('code', '=', VehicleStateStatus.Available.value)], limit=1)
                for lg in lst_assigned:
                    if lg.vehicle_id.state_id.id != available_state.id:
                        lg.vehicle_id.state_id = available_state
                    lg.unlink()
            if self and super(GroupRequestTO, self).write({'status': "2", 'approver_id': self.env.uid}):
                self.send_noti(body="Your request time off for %s approved" % self.get_time_range())
                return True
            return False
        except AccessError:
            raise AccessError("You don't have the permission to perform this action")

    @api.model
    def deny_request(self):
        try:
            if not self.list_day_request[0].can_approve:
                raise AccessError("You don't have the permission to perform this action")
            if self and super(GroupRequestTO, self).write({'status': "3", 'approver_id': self.env.uid}):
                self.send_noti(body="Your request time off %s was denied" % self.get_time_range())
                return True
            return False
        except AccessError:
            raise AccessError("You don't have the permission to perform this action")

    def send_noti(self, body):
        val = {
            'user_id': [self.driver_id.user_id.id],
            'title': "Request time off result",
            'content': body,
            'click_action': ClickActionType.requesttime_off_type.value,
            'message_type': MessageType.success.value,
            'type': NotificationType.RoutingMessage.value,
            'object_status': self.status,
            'item_id': str(self.start_day)
        }
        http.request.env[Notification._name].create(val)

    def validate_request(self, vals):
        if 'driver_id' not in vals or 'request_days' not in vals or 'reason' not in vals:
            raise ValidationError("Wrong input parameters!")
        list_days = {}
        for rqd in vals['request_days']:
            if rqd['date_value'] in list_days:
                raise ValidationError("Cannot request the same day more than once")
            list_days[datetime.strptime(rqd['date_value'], "%Y-%m-%d").date()] = rqd['type']
        # Validate individual value
        dates = list(list_days.keys())
        dates.sort()
        # check consecutive dates
        # dates = [datetime.strptime(d, "%Y-%m-%d") for d in list_temp]
        date_ints = set([d.toordinal() for d in dates])
        first_day = dates[0]
        today = datetime.now().today().date()
        # if create request the day before, must be before time_limit(hour of day)
        time_limit = int(http.request.env['ir.config_parameter'].sudo().get_param('driver.request.time.limit'))
        if time_limit and 0 <= time_limit <= 24 and (first_day + timedelta(
                days=-1)) == today and datetime.now().today().hour >= time_limit:
            raise ValidationError("Request date time limit exceeded, make your request before ")
        if len(date_ints) > 1 and max(date_ints) - min(date_ints) != len(date_ints) - 1:
            raise ValidationError("Dates are not consecutive")
        # end check consecutive dates
        first_day_str = str(dates[0])
        last_day_str = str(dates[len(dates) - 1])
        vals['start_day'] = first_day_str
        vals['end_day'] = last_day_str
        # first day must be after today
        if first_day <= today:
            raise ValidationError("Request date must be after today")
        if not vals['reason']:
            raise ValidationError("Reason is invalid")
        if self.check_dupe_request(vals['driver_id'], list_days, vals):
            raise ValidationError("Driver has already requested one of these days")
        self.validate_driver(vals['driver_id'])

    def cancel_request(self, request_group_id):
        try:
            request_res = http.request.env['fleet.group.request.to'].search(args=[('id', '=', request_group_id)])
            if not request_res:
                raise ValidationError("Request group id invalid")
            if request_res.status != "1":
                raise ValidationError("This request group is processed, cannot cancel")
            if request_res.driver_id.user_id.id != self.env.uid:
                raise AccessError("You don't have the permission to cancel this request")
            res = super(GroupRequestTO, request_res).write({'status': "4"})
            if res:
                # list_rq = self.env['fleet.request.time.off']. \
                #     search_read(domain=[('group_request_id', '=', request_group_id)])
                list_res = []
                for rq in request_res.list_day_request:
                    temp = {
                        'id': rq['id'],
                        'group_request_id': request_res.id,
                        'request_day': str(rq['request_day']) + " 00:00:00",
                        'type': rq['type'],
                        'status': request_res.status,
                        'driver_id': request_res.driver_id.id,
                        'reason': request_res.reason
                    }
                    list_res.append(temp)
                return {'records': list_res}
        except Exception:
            return {'records': []}

    # Check if the driver_id exist, then check if the logged in user match the driver
    def validate_driver(self, driver_id):
        driver_res = self.env['fleet.driver'].search(args=[('id', '=', driver_id)])
        if not driver_res:
            raise ValidationError("Driver is not valid")
        if driver_res.user_id.id != self.env.uid:
            raise AccessError("User account and driver don't match!")

    # Search for request for the same day and not canceled
    def check_dupe_request(self, driver_id, request_days, vals):
        request_res = self.env['fleet.request.time.off']. \
            search(args=[('driver_id', '=', driver_id), ('request_day', 'in', list(request_days.keys())),
                         ('status', 'in', ('1', '2', '4'))])
        if not request_res:
            return False
        vals['days_update'] = []
        for res in request_res:
            if res.request_day in request_days.keys():
                res_type = request_days[res.request_day]
                if res.type == '1' or res_type == '1' or res.type == res_type:
                    if res.status == '4':
                        vals['days_update'].append(res.request_day)
                        if 'res_update' not in vals:
                            vals['res_update'] = [res]
                        else:
                            vals['res_update'].append(res)
                    else:
                        return True
        return False

    def get_list_request(self, year, month):
        driver_res = http.request.env['fleet.driver'].search(args=[('user_id', '=', self.env.uid)])
        if not driver_res:
            raise ValidationError("This account is not of a driver")
        query_string = """
            select rq.group_request_id , rq.id, gr.driver_id, (request_day || ' 00:00:00') as request_day, gr.reason, rq.type, gr.status, gr.approver_id,
                rp.name approver_name, rp.phone, rp.mobile
            from fleet_request_time_off rq 
            left join fleet_group_request_to gr on gr.id = rq.group_request_id 
            left join res_users apv on apv.id = gr.approver_id
            left join res_partner rp on rp.id = apv.partner_id 
            where gr.status != '4'
                and gr.driver_id = %s
                and ((extract(year from gr.start_day) = %s	
                and extract (month from gr.start_day) = %s) 
                or (extract(year from gr.end_day) = %s	
                and extract (month from gr.end_day) = %s))
            order by rq.request_day, gr.create_date desc
        """

        self.env.cr.execute(query_string, (driver_res.id, year, month, year, month))
        res = self.env.cr.dictfetchall()
        return res
