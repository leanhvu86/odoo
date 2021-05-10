from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import AccessError, ValidationError
import re


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


def validate_mail(self):
    for rec in self:
        if rec.email != False:
            match = re.search(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9]+\.[a-zA-Z0-9.]*\.*[com|org|edu]{3}$)", rec.email)
            if match:
                return True
            raise ValidationError(_('Format email address "Name <email@domain>'))
    return True


def validate_zip_code(zip_code):
    if zip_code:
        match = re.search(r'.*(\D+?)$', zip_code)
        if match:
            raise ValidationError(_('Format zip code e.g. 1111111111'))
    return True


def validate_phone_number_v2(phone_number):
    if phone_number:
        match = re.search(r"(^[+0-9]{1,3})*([0-9]{10,14}$)", phone_number)
        if match:
            pass
        else:
            raise ValidationError(_('The phone number is wrong format.(eg. 0123456789)'))
        if len(phone_number) != 10:
            raise ValidationError(_('The phone number must be equals 11 numbers'))
        return True


def check_string_contain_special_character(string, field_name):
    if string:
        string_check = re.compile('[@_+!#$%^&*()<>-?/\|}{~:]')
        # if (string_check.search(string) == None):
        return True
        # raise ValidationError(_(field_name + ' must does not contain special character'))
