odoo.define('theme_order_customer.theme_widget', function (require) {
    "use strict";
    var session = require('web.session');
    var ajax = require('web.ajax');
    //init,handler slider bar
    var layout = {
        slideIndex: 1,
        animationSpeed: 1000,
        pause: 3000,
        currentSlide: 1,

        //slider show
        moveSlides: function (n) {
            this.displaySlider(this.slideIndex = n);
        },
        activeSlide: function (n) {
            this.displaySlider(this.slideIndex = n);
        },
        displaySlider: function (n) {
            var i;
            var totalslides = $(".slide-home");
            var totaldots = $(".footerdot");
            //dom element
            var $slider = $('#slider-bar');
            var $sliderAnimation = $slider.find($('.image-container'));
            var $slides = $sliderAnimation.find($('.slide-home'));
            if (n > totalslides.length) {
                this.slideIndex = 1;
            }

            if (n < 1) {
                this.slideIndex = totalslides.length;
            }
            for (i = 0; i < totalslides.length; i++) {
                totalslides[i].style.display = "none";
            }
            for (i = 0; i < totaldots.length; i++) {
                totaldots[i].className =
                    totaldots[i].className.replace(" active", "");
            }
            totalslides[this.slideIndex - 1].style.display = "block";
            totaldots[this.slideIndex - 1].className += " active";
        }, changeImage: function () {
            var index = 1
            setInterval(() => {
                    this.moveSlides(index)
                    index++
                    if (index > $(".slide-home").length) {
                        index = 1
                    }
                    // this.slideIndex == $(".slide").length ? this.slideIndex = 1 : this.slideIndex
                }
                , this.pause);
        }

    }
    var publicWidget = require('web.public.widget');
    publicWidget.registry.homePage_silderBar = publicWidget.Widget.extend({
        selector: '#slider-bar',
        events: {
            'click .footerdot': '_onNextImageClick',
        },

        /**
         * @override
         */
        start: function () {
            // $('.js_tweet, .js_comment').share({});
            layout.displaySlider(1)
            layout.changeImage()
            return this._super.apply(this, arguments);
        },
        _onNextImageClick: function (ev) {
            // console.log(ev.preventDefault());
            var self = this;
            // var $el = $(ev.currentTarget);
            var $input = $(ev.currentTarget);
            console.log($input[0].getAttribute('value'))
            $input[0].getAttribute('value') && layout.activeSlide($input[0].getAttribute('value'))
        },
    });

    // $('.footerdot').bind('click', function (e) {
    //     var $input = $(e.currentTarget);
    //     console.log($input[0].getAttribute('value'))
    //     $input[0].getAttribute('value') && layout.activeSlide($input[0].getAttribute('value'))
    // });

    // a quang ngao
    var currentIndex = 0;
    $('.icon-progress').bind('click', function (e) {

        document.getElementById("timeline-item-" + currentIndex.toString()).style.display = "none";
        var visited = Number(e.currentTarget.attributes[2].value)
        currentIndex = visited;

        document.getElementById("timeline-item-" + currentIndex.toString()).style.display = "block";

        var styleNode = document.createElement('style');

        var style = ".achievement .lazyloaded {left:" + (165 * visited).toString() + "px;}";
        styleNode.type = "text/css";

        var styleText = document.createTextNode(style);
        styleNode.appendChild(styleText);
        document.getElementsByTagName('head')[0].appendChild(styleNode);

    });

    $('.slick-prev').bind('click', function (e) {
        if (currentIndex > 0) {
            document.getElementById("timeline-item-" + currentIndex.toString()).style.display = "none";
            document.getElementById("timeline-item-" + (currentIndex - 1).toString()).style.display = "block";
            currentIndex -= 1;
            var styleNode = document.createElement('style');

            var style = ".achievement .lazyloaded {left:" + (165 * currentIndex).toString() + "px;}";
            styleNode.type = "text/css";

            var styleText = document.createTextNode(style);
            styleNode.appendChild(styleText);
            document.getElementsByTagName('head')[0].appendChild(styleNode);
            console.log("prev");
        }


    });

    $('.slick-next').bind('click', function (e) {

        if (currentIndex < 7 && currentIndex != 6) {
            document.getElementById("timeline-item-" + currentIndex.toString()).style.display = "none";
            document.getElementById("timeline-item-" + (currentIndex + 1).toString()).style.display = "block";
            currentIndex += 1;

            var styleNode = document.createElement('style');

            var style = ".achievement .lazyloaded {left:" + (165 * currentIndex).toString() + "px;}";
            styleNode.type = "text/css";

            var styleText = document.createTextNode(style);
            styleNode.appendChild(styleText);
            document.getElementsByTagName('head')[0].appendChild(styleNode);
            console.log("next");
        }


    });







})