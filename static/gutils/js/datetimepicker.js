jQuery(function($){
    if ($.datepicker) {
        $.datepicker.regional[''] = {
            closeText: gettext('Done'),
            prevText: '&#x3c;',
            nextText: '&#x3e;',
            currentText: gettext('Today'),
            monthNames: [
                gettext('January'),
                gettext('February'),
                gettext('March'),
                gettext('April'),
                gettext('May'),
                gettext('June'),
                gettext('July'),
                gettext('August'),
                gettext('September'),
                gettext('October'),
                gettext('November'),
                gettext('December')
            ],
            monthNamesShort: [
                gettext('Jan'),
                gettext('Feb'),
                gettext('Mar'),
                gettext('Apr'),
                gettext('May'),
                gettext('Jun'),
                gettext('Jul'),
                gettext('Aug'),
                gettext('Sep'),
                gettext('Oct'),
                gettext('Nov'),
                gettext('Dec')
            ],
            dayNames: [
                gettext('Sunday'),
                gettext('Monday'),
                gettext('Tuesday'),
                gettext('Wednesday'),
                gettext('Thursday'),
                gettext('Friday'),
                gettext('Saturday')
            ],
            dayNamesShort: [
                gettext('Sun'),
                gettext('Mon'),
                gettext('Tue'),
                gettext('Wed'),
                gettext('Thu'),
                gettext('Fri'),
                gettext('Sat')
            ],
            dayNamesMin: [
                gettext('Su'),
                gettext('Mo'),
                gettext('Tu'),
                gettext('We'),
                gettext('Th'),
                gettext('Fr'),
                gettext('Sa')
            ],
            weekHeader: gettext('Wk'),
            dateFormat: get_format('JS_DATE_FORMAT'),
            firstDay: 1,
            isRTL: false,
            showMonthAfterYear: false,
            yearSuffix: ''
        };
        $.datepicker.setDefaults($.datepicker.regional['']);
    }

    if ($.timepicker) {
        $.timepicker.regional[''] = {
            currentText: gettext('Now'),
            closeText: gettext('Done'),
            amNames: ['AM', 'A'],
            pmNames: ['PM', 'P'],
            timeFormat: 'HH:mm',
            timeSuffix: '',
            timeOnlyTitle: gettext('Choose Time'),
            timeText: gettext('Time'),
            hourText: gettext('Hour'),
            minuteText: gettext('Minute'),
            secondText: gettext('Second'),
            millisecText: gettext('Millisecond'),
            microsecText: gettext('Microsecond'),
            timezoneText: gettext('Time Zone'),
            isRTL: false
        };
        $.timepicker.setDefaults($.timepicker.regional['']);
    }

    $.fn.widgetDate = function() {
        if ($(this).data('has-date-widget'))
            return this;
        /*
        // check native widget
        var input = document.createElement('input');
        input.setAttribute('type','date');
        input.setAttribute('value', '-');
        if(input.value !== '-') {
            var val = $(this).val();
            var re = /^\d\d\d\d\-\d\d\-\d\d$/;
            if(!re.exec(val)) {
                $(this).val(moment(val, get_format('JS_DATE_FORMAT')).format('YYYY-MM-DD'));
            }
            $(this).data('has-date-widget');
            $(this).attr('type', 'date');
            return this;
        }
        */
        $(this).datepicker({
            changeMonth: true,
            changeYear: true,
            showAnim: ''
        });
        return this;
    };

    $.fn.widgetDateTime = function() {
         if ($(this).data('has-date-widget'))
             return this;
         $(this).datetimepicker({
             controlType: 'select',
             oneLine: true,
             dateFormat: get_format('JS_DATE_FORMAT'),
             timeFormat: get_format('JS_TIME_FORMAT')
         });
        return this;
    }

    $.fn.widgetDateRange = function() {
        var field = $(this);
        if (field.data('has-date-widget'))
             return this;
        field.attr('type', 'hidden');
        var dates = ['', ''];
        var classes = ['date-from-input', 'date-to-input'];
        var placeholders = [gettext('Date from'), gettext('Date to')];
        if (field.val()) {
            dates = field.val().split(get_format('DATE_SEPARATOR'));
        }
        for (var i=1; i >= 0; i--) {
            var input = $('<input id="'+field.attr('id')+'_'+i+'" type="text"/>');
            field.after(input);
            if (dates[i]) {
                input.val(dates[i]);
            }
            input.addClass(classes[i]);
            input.attr('placeholder', placeholders[i]);
            input.datepicker({
                changeMonth: true,
                changeYear: true,
                showAnim: ''
            });
            input.change(function() {
                field.val(field.next().val()+get_format('DATE_SEPARATOR')+field.next().next().val());
            });
        }
        return this;
    }


});

