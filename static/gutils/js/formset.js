$(document).ready(function() {
    var table = $('table.formset tbody');
    table.parent().after('<div style="height:0px; overflow: hidden;"><input id="formset-input" type="text" autocomplete="off" /></div>');
    var input = $('#formset-input');
    var min_x = 1;
    var min_y = 0;
    var max_x = table.children('tr').first().children('td').length -1;
    var max_y = table.children('tr').length - 1;
    var x = min_x;
    var y = min_y;
    table.children('tr').each(function(y) {
        $(this).data('y', y);
        $(this).children('td').each(function(x) {
            $(this).data('x', x);
            $(this).find('input').attr('autocomplete', 'off');
            $(this).find('input[type=number]').attr('type', 'text');
        });
    });
    table.find('input').focus(function() {
        table.find('.cursor').removeClass('cursor');
        var td = $(this).parents('td');
        td.addClass('cursor');
        x = td.data('x');
        y = td.parent().data('y');
    });
    table.find('input').keydown(function(e) {
        if(e.which == 13 || e.which == 27) {
            input.focus();
            return false;
        };
        if(e.which == 37 || e.which == 39 || (!$(this).hasClass('ui-autocomplete-input') && (e.which == 38 || e.which == 40))) {
            move(e.which);
            input.focus();
            return false;
        };
    });
    input.keydown(function(e) {
        if(e.which >= 37 && e.which <= 40 || e.which == 9) {
            move(e.which);
            return false;
        }
        var text = table.find('.cursor input[type=text]').first();
        if (text)
            text.focus().select();
        if(e.which == 13) {
            var checkbox = table.find('.cursor input[type=checkbox]').first();
            if (checkbox)
                checkbox.prop('checked', !checkbox.prop('checked'));
            return false;
        }
    });
    function move(code) {
        var x1 = x;
        var y1 = y;
        switch (code) {
            case 38:
                if (y1 > min_y)
                    y1 -= 1;
                break;
            case 40:
                if (y1 < max_y)
                    y1 += 1;
                break;
            case 37:
                if (x1 > min_x)
                    x1 -= 1;
                break;
            case 39:
                if (x1 < max_x)
                    x1 += 1;
                break;
            case 9:
                if(x1 < max_x)
                    x1 += 1;
                else {
                    x1 = min_x;
                    if (y1 < max_y)
                        y1 += 1;
                    else
                        y1 = min_y;
                }
                break;
        }
        if (x1!=x || y1!=y) {
            x = x1;
            y = y1;
            table.find('.cursor').removeClass('cursor');
            table.children('tr').eq(y).children('td').eq(x).addClass('cursor');
        }
    }
});