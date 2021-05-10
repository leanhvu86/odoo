import re
from odoo import _
from odoo.exceptions import ValidationError
from datetime import datetime


def validate_phone_number(self):
    for rec in self:
        if rec.phone_number:
            match = re.search(r"(^[+0-9]{1,3})*([0-9]{10,11}$)", rec.phone_number)
            if match:
                pass
            else:
                raise ValidationError(_('The phone number is wrong format.(eg. 0123456789)'))
            if len(rec.phone_number) != 10:
                raise ValidationError(_('The phone number must be equals 11 numbers'))
            return True
    return True
def check_number_smaller_than_0(key,number):
    if number < 0:
        raise ValidationError(_(key + ' must greater than 0!'))


def validate_phone_number_v2(phone_number):
    if phone_number:
        match = re.search(r"(^[+0-9]{1,3})*([0-9]{10,11}$)", phone_number)
        if match:
            pass
        else:
            raise ValidationError(_('The phone number is wrong format.(eg. 0123456789)'))
        if len(phone_number) != 10:
            raise ValidationError(_('The phone number must be equals 11 numbers'))
        return True


def check_string_contain_special_character(string, field_name):
    if string:
        string_check = re.compile('[@_+!#$%^&*()<>?/\|}{~:]')
        if string_check.search(string) is None:
            return True
        raise ValidationError(_(field_name + ' must does not contain special character'))


def validate_mail(self):
    for rec in self:
        if rec.email != False:
            match = re.search(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9]+\.[a-zA-Z0-9.]*\.*[com|org|edu]{3}$)", rec.email)
            if match:
                return True
            raise ValidationError(_('Format email address "Name <email@domain>'))
    return True


def check_number_bigger_than_zero(number, field_name):
    if number:
        if number < 0:
            raise ValidationError(_("" + field_name + " : value must greater than or equal to  0!"))
        return True

    def validate_mail_v2(email):
        if email != False:
            match = re.search(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9]+\.[a-zA-Z0-9.]*\.*[com|org|edu]{3}$)", email)
            if match:
                return True
            raise ValidationError(_('Format email address "Name <email@domain>'))
        return True


def validate_website_link(email_link):
    if email_link:
        regex = re.compile(
            r'^(?:http|ftp)s?://'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
            r'localhost|'
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?::\d+)?'
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        match = re.match(regex, email_link)
        if match:
            return True
        raise ValidationError(_('Format website address e.g. https://www.odoo.com'))
    return True


def validate_zip_code(zip_code):
    if zip_code:
        match = re.search(r'.*(\D+?)$', zip_code)
        if match:
            raise ValidationError(_('Format zip code e.g. 1111111111'))
    return True

def check_from_date_greater_than_to_date(from_date, to_date):
    if from_date and to_date:
        # fDate_time_obj = datetime.datetime.strptime(from_date, '%Y-%m-%d %H:%M:%S.%f')
        # tDate_time_obj = datetime.datetime.strptime(to_date,'%Y-%m-%d %H:%M:%S.%f')
        fDate_time_obj = datetime.strptime(str(from_date), '%Y-%m-%d')
        tDate_time_obj = datetime.strptime(str(to_date), '%Y-%m-%d')
        if fDate_time_obj > tDate_time_obj:
            raise ValidationError(_('"'+str(from_date)+'" ' + ' From date is must smaller than to date '+ '"'+str(to_date)+'" ' ))
    else:
        raise ValidationError('From date and to date can not null!')
