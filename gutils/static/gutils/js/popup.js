$(document).ready(function() {
    $('.tip').adminTip();

    $.admin.table.init('.table,.formset');
    $.admin.changer.init('.item-change');
    $(document).on('click', 'a', function() {
        var a = $(this);
        if (a.attr('target') == '_parent' || a.attr('target') == '_blank')
            return true;
        var href = a.attr('href');
        if (href[0] == '#')
            return true;
        if(href.indexOf('?') == -1) {
            href += '?popup=1';
        }
        else {
            href += '&popup=1';
        }
        a.attr('href', href);
        return true;
    });
});
