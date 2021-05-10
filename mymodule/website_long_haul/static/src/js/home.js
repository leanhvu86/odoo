//odoo.define('theme_long_haul.footer', (require) => {
//    "use strict";
//    var core = require('web.core');
//    var publicWidget = require('web.public.widget');
//    var slideIndex = 1;
//
//    publicWidget.registry.home = publicWidget.Widget.extend({
//        selector : '.slideshow-container',
//        events: {
//            'click .next': '_onClickNext',
//            'click .pre': '_onClickPre',
//        },
//        _onClickNext: function (ev) {
//            this.plusSlides(1);
//        },
//        _onClickPre: function (ev){
//            this.plusSlides(-1);
//        },
//        init: function () {
//            this._super.apply(this, arguments);
//            var self = this;
//            var param = this.param;
//            this.slideIndex = 1;
//            console.log("Home");
//        },
//        start: function () {
//            this.showSlides();
//        },
//        on_ready: function () {
//        },
//        plusSlides: function (n) {
//          this.switchSlides(slideIndex += n);
//        },
//
//        // Thumbnail image controls
//        currentSlide: function (n) {
//          this.switchSlides(slideIndex = n);
//        },
//
//        switchSlides: function (n) {
//          var i;
//          var slides = this.$(".mySlides");
//          var dots = this.$(".dot");
//          if (n > slides.length) {
//            slideIndex = n % slides.length + 1;
//          } else if (n < 1) {
//            slideIndex = slides.length
//          } else {
//            slideIndex = n;
//          }
//          for (i = 0; i < slides.length; i++) {
//              slides[i].style.display = "none";
//          }
//        //  for (i = 0; i < dots.length; i++) {
//        //      dots[i].className = dots[i].className.replace(" active", "");
//        //  }
//          slides[slideIndex-1].style.display = "block";
////          dots[slideIndex-1].className += " active";
//        },
//
//        showSlides: function () {
////          var i;
//          var slides = this.$(".mySlides");
////          for (i = 0; i < slides.length; i++) {
////            slides[i].style.display = "none";
////          }
////          slideIndex++;
////          if (slideIndex > slides.length) {slideIndex = 1}
////          slides[slideIndex-1].style.display = "block";
//            this.switchSlides(this.slideIndex++);
//            setInterval((function () {
//                this.switchSlides(this.slideIndex++);
//                if (this.slideIndex > slides.length) {
//                    this.slideIndex = this.slideIndex % slides.length;
//                }
//            }).bind(this), 5000); // Change image every 5 seconds
//        },
//    });
//
//    return publicWidget;
//});