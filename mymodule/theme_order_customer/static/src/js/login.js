odoo.define('theme_order_customer.website_ajax_login', function (require) {
    var ajax = require('web.ajax');
    var session = require('web.session');
    $('#login_button').on('click', function () {
        $('#login_error').empty();
        var login = $(this).parent().parent().parent().find('#ajax_login');
        var password = $(this).parent().parent().parent().find('#ajax_password');
        var database = $(this).parent().parent().parent().find('.ajax_db :selected').val();
        var redirect = $('#nav-profile').find('input[name="redirect"]').val();
        var input = {
            login: login.val(),
            password: password.val(),
            db: 'DB_LONG',
            redirect: redirect,
        };
        console.log(input, '12321312')
        $("<div id='ajax_loader'/>").appendTo('body');
        ajax.jsonRpc('/web/session/authenticate', 'call', input).then((response) => {
            var element = document.getElementById("ajax_loader");
            console.log(response, '12321312')
            if (response['login_success'] != false) {
                localStorage.setItem('currency', response.currency);
                redirect_url = window.location.origin + '/'// response["redirect"]
                window.location.href = redirect_url;
                $(window).on('load', function () {
                });
            } else {
                element.parentNode.removeChild(element);
                custom_msg($('#login_error'), true, "Wrong user/password");
                $('#login_error').on('click', function () {
                    custom_msg($('#login_error'), false, "");
                    custom_mark($('.demo_loginclass'), false);
                });
            }
        })
    });

    var data = {};

    function custom_msg(element_id, status, msg) {
        if (status == true) {
            element_id.empty().append("<div class='alert alert-danger text-center' id='Wk_err'>" + msg + "<button type='button' class='close' data-dismiss='alert' aria-label='Close'><span class='res fa fa-times ' aria-hidden='true'></span></button></div>");
        }
        if (status == false) {
            element_id.empty();
        }
        return true;
    }

    function custom_mark(element_id, status) {
        if (status == true) {
            element_id.parent().addClass('has-error has-feedback').append("<span class='fa fa-times form-control-feedback'></span>");
        } else if (status == false) {
            element_id.parent().removeClass('has-error  has-feedback').children("span").remove();
        }
    }

});