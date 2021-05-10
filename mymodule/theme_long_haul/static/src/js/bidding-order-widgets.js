odoo.define('theme_long_haul.bidding-order-widgets', function (require) {
    "use strict";
    var session = require('web.session');
    var ajax = require('web.ajax');
    var index = 4;

    // title = title.replace(/'/g, '"');
    // title = JSON.parse(title);
    // console.log(new Date().toTimeString().slice(9));
    // console.log(Intl.DateTimeFormat().resolvedOptions().timeZone);
    // console.log(new Date().getTimezoneOffset() / -60);


    var biddingCountDown = setInterval(function () {
        var dateBidding = $(".span-bidding-time").eq(0).attr("bidding-time");
        var countDownDate = new Date(dateBidding);
        var hour_time_zone = countDownDate.getTimezoneOffset() / -60;
        countDownDate.setHours(countDownDate.getHours() + 1 + (hour_time_zone));
        countDownDate.getTime();
        var now = new Date().getTime();
        //   Find the distance between now and the count down date
        var distance = countDownDate - now;

        // Time calculations for days, hours, minutes and seconds
        var days = Math.floor(distance / (1000 * 60 * 60 * 24));
        var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        var seconds = Math.floor((distance % (1000 * 60)) / 1000);
        var viewTime = days.toString() + ":" + hours.toString() + ":" + minutes.toString() + ":" + seconds.toString() + "s ";
        if (distance < 0) {
            viewTime = "EXPIRED"
        }
        $(".count-down-time").text(viewTime);
    }, 1000);
    // console.log(biddingCountDown);

    $(".bidding-package").click(async function (event) {
        var package_id = $(this).attr('bidding-package');
        $(".loader").show();
        $("#myModal").show();
        await sleep(3000);
        session.rpc("bidding/create_bidding_order", {
            "bidding_package_id": package_id,
            "confirm_time": "2020-09-17 02:00:00"
        }).then(function () {
            $(".loader").hide();
            $(".bidding-package").hide();
            $(".dt-success").show();
            $("#myModal").hide();
            $("#myModal1").show();
            $(".item_bidding").eq(0).hide();

        });


    });


    // $(".item_bidding").click(function (event) {
    //     console.log($(this).index());
    // });

    $(".dt-success").click(function (event) {
        $("#myModal1").hide();
    });

    $(".dt-bidding").click(async function (event) {
        console.log($(this).index());
        $(".bidding-package").show();
        $(".dt-success").hide();
    });


    function sleep(ms) {
        return new Promise((accept) => {
            setTimeout(() => {
                accept();
            }, ms);
        });
    }

    $(".li-bidding-package").click(function (event) {
        $(".li-bidding-package").removeClass("click-li-bidding-package");
        $(this).addClass("click-li-bidding-package");
        clearInterval(biddingCountDown);

    });

    var myInterval = -1

    $(".li-bidding-package").click(function (event) {
        console.log("abc");
        $(".li-bidding-package").removeClass("click-li-bidding-package");
        $(this).addClass("click-li-bidding-package");
        // console.log();
        // setInterval(function () {
        //     var dateBidding = $(this).attr("bidding-time");
        //     var countDownDate = new Date(dateBidding);
        //     var hour_time_zone = countDownDate.getTimezoneOffset() / -60;
        //     countDownDate.setHours(countDownDate.getHours() + 1 + (hour_time_zone));
        //     countDownDate.getTime();
        //     var now = new Date().getTime();
        //     //   Find the distance between now and the count down date
        //     var distance = countDownDate - now;
        //
        //     // Time calculations for days, hours, minutes and seconds
        //     var days = Math.floor(distance / (1000 * 60 * 60 * 24));
        //     var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        //     var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        //     var seconds = Math.floor((distance % (1000 * 60)) / 1000);
        //     var viewTime = days.toString() + ":" + hours.toString() + ":" + minutes.toString() + ":" + seconds.toString() + "s ";
        //     if (distance < 0) {
        //         viewTime = "EXPIRED"
        //     }
        //     $(".count-down-time").text(viewTime);
        // })
    });

    $(".test").click(async function () {
        // console.log("ab");
        // ajax.jsonRpc('/bidding_order', 'call', {
        //     'test': "123",
        // }).then(function (res) {
        //     console.log("load xong!");
        // });token
        const token = $(".token1").attr('value')
        var data = {
            "test": "123"
        }

        var url = "/bidding_order";
        sendRequest(url, data, token)
            .then(data => {
                console.log(data);
                var hide_button = false;
                if (data == null) {
                    if (!alert('Something went wrong!')) {
                        window.location.reload();
                    }
                } else if (data.error != null) {
                    var res_data = data.error.data;
                    var type = res_data.exception_type;
                    if (type === "validation_error") {
                        alert(res_data.arguments[0]);
                        hide_button = true;
                    } else {
                        if (!alert('Something went wrong!')) {
                            window.location.reload();
                        }
                    }
                } else {
                    alert('Search successful!');
                }
            });

    })

    async function sendRequest(url, data, token) {
        // Default options are marked with *
        data = {
            'kwargs': data,
        };
        const response = await fetch(url, {
            method: 'POST', // *GET, POST, PUT, DELETE, etc.
            mode: 'cors', // no-cors, *cors, same-origin
//    cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
            credentials: 'same-origin', // include, *same-origin, omit
            headers: {
                'Content-Type': 'application/http'
                // 'Content-Type': 'application/x-www-form-urlencoded',
            },
            redirect: 'follow', // manual, *follow, error
            referrerPolicy: 'no-referrer', // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
            body: JSON.stringify(data) // body data type must match "Content-Type" header
        });
        return response.json(); // parses JSON response into native JavaScript objects
    }


    setInterval(function () {
        var countDownDate = new Date();
        countDownDate.setHours(countDownDate.getHours() + 1);
        countDownDate.setMinutes(0);
        countDownDate.setSeconds(0);
        countDownDate.getTime();
        var now = new Date().getTime();
        //   Find the distance between now and the count down date
        var distance = countDownDate - now;

        // Time calculations for days, hours, minutes and seconds
        var days = Math.floor(distance / (1000 * 60 * 60 * 24));
        var hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        var minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        var seconds = Math.floor((distance % (1000 * 60)) / 1000);
        var viewTime =  minutes.toString() + ":" + seconds.toString() + "s ";
        if (distance < 0) {
            viewTime = "EXPIRED"
        }
        $(".bidding-time-order").text(viewTime);
    }, 1000);

    $(".span-bidding-time").each(function (index) {
        var mydate = new Date($(this).text());
        // var đ = today;
        var hour_time_zone = mydate.getTimezoneOffset() / -60;
        mydate.setHours(mydate.getHours() + (hour_time_zone));
        var dd = mydate.getDate();
        var mm = mydate.getHours();
        // $(".span-bidding-time").eq(0).innerHTML = 8
        $(this).text(mm + ":00");
    });


    $(".next").click(function (event) {
        if (index < $('.li-bidding-package').length - 1) {
            index += 1;
            console.log(index);
            $(".li-bidding-package").each(function (index) {
                var mydate = new Date($(this).text());
            });
            $(".li-bidding-package").eq(index - 5).removeAttr("style");
            $(".li-bidding-package").eq(index - 5).css({display: "none"});

            $(".li-bidding-package").eq(index).removeAttr("style");
            $(".li-bidding-package").eq(index).css({display: "block"});
        }

    });


    $(".prev").click(function (event) {
        if (index > 4) {
            $(".li-bidding-package").each(function (index) {
                var mydate = new Date($(this).text());
            });
            $(".li-bidding-package").eq(index - 5).removeAttr("style");
            $(".li-bidding-package").eq(index - 5).css({display: "block"});

            $(".li-bidding-package").eq(index).removeAttr("style");
            $(".li-bidding-package").eq(index).css({display: "none"});
            index -= 1;
        }


    });


})
;
