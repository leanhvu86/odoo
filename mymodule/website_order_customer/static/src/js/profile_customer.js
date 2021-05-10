odoo.define('website_order_customer.frofile_customer', function (require) {
    "use strict";
    var Widget = require('web.Widget');
    var core = require('web.core');
    var QWeb = core.qweb;
    var session = require('web.session');
    var ajax = require('web.ajax');
    var publicWidget = require('web.public.widget');


    //Tab menu profile customer
    var index_menu_content = 0;
    var warehouse_id = null;
    var list_package = []

/*
    publicWidget.registry.ProfileCustomer = publicWidget.Widget.extend({
        selector: '.warehouse-receiving-bts',
        events: {
            'click #warehouse-receiving-bt-1': '_onClick',
        },

        init: function (parent, data, options, recordOptions) {
            this._super(parent);
            console.log("lock");
            ajax.loadXML('/website_order_customer/static/src/xml/woc_template.xml', QWeb);

        },

        start: function () {
            console.log("lock");
        },

        _onClick: function (ev) {
            console.log("click");
            $(QWeb.render('website_order_customer.order_button2', {
                currency: 'abc'
            }));
        },
    });
*/


    $('.tablinks').bind('click', function (e) {
        var index = $('.tablinks').index(this);
        $('.tablinks').removeClass(["active"]);
        e.currentTarget.className += " active";

        var tabcontent = document.getElementsByClassName("tabcontent");
        tabcontent[index_menu_content].style.display = "none";
        tabcontent[index].style.display = "block";

        // trigger search action when switch to a tab with search button
        var searchButton = tabcontent[index].querySelector('.search-button');
        if (searchButton) {
            searchButton.click();
        }
        index_menu_content = index;
    });


    //Input select
    $("#warehouse-input input").keyup(function (event) {
        console.log("anhquang");
        let container, input, filter, li, input_val;
        container = $(this).closest(".searchable");
        input_val = container.find("input").val().toUpperCase();

        if (["ArrowDown", "ArrowUp", "Enter"].indexOf(event.key) != -1) {
            keyControl(event, container)
        } else {
            li = container.find("ul li");
            li.each(function (i, obj) {
                if ($(this).text().toUpperCase().indexOf(input_val) > -1) {
                    $(this).show();
                } else {
                    $(this).hide();
                }
            });

            container.find("ul li").removeClass("selected");
            setTimeout(function () {
                container.find("ul li:visible").first().addClass("selected");
            }, 100)
        }
    });


    function keyControl(e, container) {
        console.log("b");
        if (e.key == "ArrowDown") {

            if (container.find("ul li").hasClass("selected")) {
                if (container.find("ul li:visible").index(container.find("ul li.selected")) + 1 < container.find("ul li:visible").length) {
                    container.find("ul li.selected").removeClass("selected").nextAll().not('[style*="display: none"]').first().addClass("selected");
                }

            } else {
                container.find("ul li:first-child").addClass("selected");
            }

        } else if (e.key == "ArrowUp") {

            if (container.find("ul li:visible").index(container.find("ul li.selected")) > 0) {
                container.find("ul li.selected").removeClass("selected").prevAll().not('[style*="display: none"]').first().addClass("selected");
            }
        } else if (e.key == "Enter") {
            container.find("input").val(container.find("ul li.selected").text()).blur();
            $('.info-warehouses').show();
        }

        container.find("ul li.selected")[0].scrollIntoView({
            behavior: "auto",
            block: 'nearest'
        });
    }


    $(".searchable input").focus(function (event) {
        console.log("focus");
        $(event.target).closest(".searchable").find("ul li").remove();

        var model_name = $(event.target).attr("model");

        ajax.jsonRpc('/share_van_order/get_model_name', 'call', {
            'model': model_name
        }).then(function (result) {
            console.log(result.records[0][0][0]);
            result.records[0][0][0].forEach(function (field) {
                let li = "<li ids =" + field.id + " class = 'cvb'><p>" + field.name + "</p></li>"
                $(event.target).closest(".searchable").find("ul").append(li);
            });
        })

        $(event.target).closest(".searchable").find("ul").show();
        $(event.target).closest(".searchable").find("ul li").show();

    });
    $(".searchable input").blur(function () {
        let that = this;
        setTimeout(function () {
            $(that).closest(".searchable").find("ul").hide();
        }, 100);
    });


    // action khi click vào 1 list danh sách
    $(document).on("click", ".searchable ul li", function (event) {
        console.log("click li");

        let container, ids, model_name;
        container = $(event.target).closest(".searchable");
        container.find("input").val($(event.target).text()).blur();
        model_name = container.find("input").attr("model");
        ids = Number($(event.target).closest("li").attr("ids"));

        container.find("input").attr("ids", ids);

        if (model_name == 'sharevan_warehouse') {
            ajax.jsonRpc('/share_van_order/get_model_name_warehouse', 'call', {
                'model': model_name, 'id': ids
            }).then(function (result) {
                result.records[0][0][0].forEach(function (field) {
                    $('#info-warehouses-name').text(field.name);
                    $('#info-warehouses-employee').text("Trần Anh Quang");
                    $('#info-warehouses-phone').text(field.phone);
                    $('#info-warehouses-province').text(field.state_name);
                    $('#info-warehouses-district').text(field.district_name);
                    $('#info-warehouses-award').text(field.ward_name);
                    $('#info-warehouses-alley').text("186 Khương Trung");
                    $('#info-warehouses-address-detail').text(field.address);


                    $('.info-warehouses').show();

                    if (list_package.length > 0) {
                        $(".point-delivery-button").css({"cursor": "pointer", "background-color": "#5ABF64"});
                    }
                });

            })
        }


    });


    //Chọn kho có sẵn , thêm kho mới , ẩn hiện
    $('#warehouse-receiving-bt-1').bind('click', function (e) {
        $('.searchable ul li').remove();
        $('.warehouse-receiving-bt').hide();
        $('.searchable').show();
        $('.warehouse-receiving-close').show();


    });


    //Close warehouse có sẵn đã chọn
    $('.warehouse-receiving-close').bind('click', function (e) {
        $('.warehouse-receiving-bt').show();
        $('.searchable').hide();
        $('.warehouse-receiving-close').hide();
        $('.info-warehouses').hide();
        $('#warehouse-input').val(null);

    });


    //Chọn dịch vụ
    var service_id = [];
    $(".service-select-bt-close").click(function () {
        $('.services-selected').show();
        $('.services-select').hide();
        let len_select_service = $('.service-ul-select li').length;
        for (let i = 0; i < len_select_service; i++) {
            $('.service-ul-select li input')[i].checked = false;
        }
        for (let i = 0; i < service_id; i++) {
            $('.service-ul-select li input')[i].checked = true;
        }
        // service_id.forEach(function (field) {
        //     $('.service-ul-select li input')[field].checked = true;
        // });
    });

    $(".services-button-add").click(function () {
        $('.services').hide();
        ajax.jsonRpc('/share_van_order/get_service_type', 'call', {}).then(function (result) {
            console.log(result.records[0]);
            result.records[0].forEach(function (field) {
                let li = "<li>\n" +
                    "<p style='float:left;width: 44%;font-size:1rem;'>" + field.name + "</p>\n" +
                    "<img style='width: 20;height: auto;float: left;margin-top: 7px;margin-right: 4%;'\n" +
                    "      src=\"/theme_order_customer/static/src/img/dolar.png\"/>\n" +
                    "<p style='width: 41%;font-size: 1rem;float:left'>" + field.price + "\n" +
                    "      <span>" + localStorage.getItem('currency') +
                    "</span>\n" +
                    "</p>\n" +
                    "<input type='checkbox' value=" + field.id + "\n" +
                    "      style=\"height: 16px;width: 16px;\"/>\n" +
                    "<hr style=\"margin-top: 2%;\"/>\n" +
                    "</li>"
                $('.service-ul-select').append(li);

            });
        })

        $('.services-select').show();

    });

    $(".service-select-bt-save").click(function () {
        console.log("abc");

        $('.services-select').hide();
        $('.services-selected').show();
        $('.service-ul-selected li').remove();
        let len = $('.service-ul-select li input:checked').length;
        for (let i = 0; i < len; i++) {
            let service_name = $('.service-ul-select li input:checked')[i].closest("li").children[0].innerText;
            let service_price = $('.service-ul-select li input:checked')[i].closest("li").children[2].innerText;
            let id = $('.service-ul-select li input:checked')[i].attributes[1].value;
            let li = "<li" + " ids = " + id + ">\n" +
                "                                            <p class='li-p\'>" + service_name + "</p>\n" +
                "                                            <img style=\"width: 6%;height: auto;float: left;margin-top: 2.1%;margin-right: 4%;\"\n" +
                "                                                 src=\"/theme_order_customer/static/src/img/dolar.png\"/>\n" +
                "                                            <p style='width: 41%;font-size: 1rem;float:left;text-align: right;'>" + service_price + "\n" +
                "                                            </p>\n" +
                "                                            <hr style=\"margin-top: 2%;clear:both;\"/>\n" +
                "                                        </li>"

            $('.service-ul-selected').append(li);
            service_id = []
            service_id.push(id);
        }

    });

    $(".service-select-bt-addd").click(function () {
        $('.services-selected').hide();
        $('.services-select').show();
    });


    // button thêm gói hàng mới
    $(".packages-selected-add").click(function () {
        $("#exampleModalLongTitle1").text("Thông tin gói hàng")
        $("#btn-save-new-package").text("Lưu")
        $("#btn-save-new-package").attr("types", "add");

        // clear data input form
        $("#exampleModalCenter1").modal('toggle');
        $(".inputName").val(null);
        $(".inputProductType").val(null);
        $(".inputAmount").val(null);
        $(".inputLong").val(null);
        $(".inputWidth").val(null);
        $(".inputHeight").val(null);
        $(".inputWeight").val(null);
    })

    //Save gói hàng mới
    $(document).on("click", "#btn-save-new-package", function () {
        console.log("save");
        let button_type = $("#btn-save-new-package").attr("types")
        let name = $(".inputName").val();
        let productType = $(".inputProductType").val();
        let amount = $(".inputAmount").val();
        let long = $(".inputLong").val();
        let width = $(".inputWidth").val();
        let height = $(".inputHeight").val();
        let weight = $(".inputWeight").val();

        if (button_type == "add") {
            if (name && productType && amount && long && width && height && weight) {
                console.log("add");
                $("#exampleModalCenter1").modal('toggle');
                $(".inputName").val(null);
                $(".inputProductType").val(null);
                $(".inputAmount").val(null);
                $(".inputLong").val(null);
                $(".inputWidth").val(null);
                $(".inputHeight").val(null);
                $(".inputWeight").val(null);


                list_package.push({
                    'name': name,
                    'productType': productType,
                    'amount': amount,
                    'long': long,
                    'width': width,
                    'height': height,
                    'weight': weight,
                });

                let item_package = "                                        <div class=\"item-packagess\">\n" +
                    "                                            <div class=\"item-package-name\">\n" +
                    "                                                <span class=\"item-package-name-left\">Tên</span>\n" +
                    "                                                <span class='item-package-name-right'>" + name + "</span>\n" +
                    "                                            </div>\n" +
                    "                                            <div class=\"item-package-name\">\n" +
                    "                                                <span class=\"item-package-name-left\">Loại hàng</span>\n" +
                    "                                                <span class='item-package-name-right'>" + productType + "</span>\n" +
                    "                                            </div>\n" +
                    "                                            <div class=\"item-package-name\">\n" +
                    "                                                <span class=\"item-package-name-left\">Số lượng</span>\n" +
                    "                                                <span class='item-package-name-right'>" + amount + "</span>\n" +
                    "                                            </div>\n" +
                    "                                            <div class=\"item-package-name\">\n" +
                    "                                                <span class=\"item-package-name-left\">Kích thước</span>\n" +
                    "                                                <span class='item-package-name-right'>" + long + "x" + width + "x" + height + "cm" + "(DxRxC)" + "</span>\n" +
                    "                                            </div>\n" +
                    "                                            <div class=\"item-package-name\">\n" +
                    "                                                <span class=\"item-package-name-left\">Trọng lượng</span>\n" +
                    "                                                <span class='item-package-name-right'>" + weight + "</span>\n" +
                    "                                            </div>\n" +
                    "                                            <button title = \"Delete\" class =\"bt-close\">\n" +
                    "                                                <i class=\"fa fa-trash abc\"></i>\n" +
                    "                                            </button>\n" +
                    "                                            <button title = \"Update\" class =\"bt-update\" data-toggle=\"modal\"\n" +
                    "                                                data-target=\"#exampleModalCenter1\">\n" +
                    "                                                <i class=\"fa fa-pencil abc\"></i>\n" +
                    "                                            </button>\n" +
                    "                                        </div>"
                $('.list-package').append(item_package);
            }
        } else {
            $("#exampleModalCenter1").modal('toggle');
            let index = Number($("#btn-save-new-package").attr("index"));
            console.log("update");
            $(".list-package").children().eq(index)[0].children[0].children[1].innerHTML = name;
            $(".list-package").children().eq(index)[0].children[1].children[1].innerHTML = productType;
            $(".list-package").children().eq(index)[0].children[2].children[1].innerHTML = amount;
            $(".list-package").children().eq(index)[0].children[3].children[1].innerHTML = long + "x" + width + "x" + height + "cm" + "(DxRxC)";
            $(".list-package").children().eq(index)[0].children[4].children[1].innerHTML = weight;

        }

    });

    //Không cho form tạo gói hàng reload trang web
    $('#myform').on('submit', function (e) {
        return false;
    });

    //Delete gói hàng.
    $(document).on("click", ".bt-close", function () {
        var index = $(".bt-close").index(this);
        var close = $(".list-package .item-packagess");
        $(".list-package").children().eq(index).remove();
        list_package.splice(index, 1);

        if (list_package.length == 0 || warehouse_id == null) {
            $(".point-delivery-button").css({"cursor": "not-allowed", "background-color": "#3fa9497f"});
        }

    });

    //Update gói hàng.
    $(document).on("click", ".bt-update", function () {
        var index = $(".bt-update").index(this);
        console.log(list_package[index]);
        $('.inputName').val(list_package[index].name)
        $('.inputProductType').val(list_package[index].productType)
        $('.inputAmount').val(list_package[index].amount)
        $('.inputLong').val(list_package[index].long)
        $('.inputWidth').val(list_package[index].width)
        $('.inputHeight').val(list_package[index].height)
        $('.inputWeight').val(list_package[index].weight)

        // Thay đổi text cập nhật và thêm attr types == update
        $("#exampleModalLongTitle1").text("Cập nhật thông tin gói hàng")
        $("#btn-save-new-package").text("Cập nhật")
        $("#btn-save-new-package").attr("types", "update");


        // Thêm attr index cho button , để khi update biết được index bao nhiêu
        $("#btn-save-new-package").attr("index", index);

    });


    // $('#exampleModalCenter1').modal({keyboard: false})


})