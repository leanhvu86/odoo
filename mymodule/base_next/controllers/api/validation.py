import re
from odoo import _
from odoo.exceptions import ValidationError


class ValidationApi:
    def validate_phone_number_v2(phone_number):
        if phone_number:
            match = re.search(r"(^[+0-9]{1,3})*([0-9]{10,11}$)", phone_number)
            if match:
                pass
            else:
                return False
            return True

    def validate_phone_number(self):
        for rec in self:
            if rec.phone:
                match = re.search(r"(^[+0-9]{1,3})*([0-9]{10,11}$)", rec.phone)
                if match:
                    pass
                else:
                    raise ValidationError(_('The phone number is wrong format.(eg. 0123456789)'))
                if len(rec.phone) != 10:
                    raise ValidationError(_('The phone number must be equals 11 numbers'))
                return True
        return True
