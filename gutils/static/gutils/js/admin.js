$(document).ready(function() {
    $.admin.table.init('.table,.formset');
    $.admin.popup.init('.popup');
    $.admin.modal.init('.modal-box');
    $.admin.dropdown.init('.dropdown-toggle');
    $.admin.image.init('.image-box');
    $.admin.changer.init('.item-change');
    $.admin.tip.init('.tip');

    $('#sidebar-open').click(function () {
        $('#sidebar').addClass('open');
        $('#sidebar-overlay').addClass('open');
        return false;
    });

    $('#sidebar-overlay').click(function () {
        $('#sidebar').removeClass('open');
        $('#sidebar-overlay').removeClass('open');
        return false;
    });

    $('#main-menu').on('click', 'a', function() {
        var li = $(this).parent();
        if (li.hasClass('open')) {
            li.removeClass('open');
            return false;
        }
        if (li.children('ul').length) {
            $('#main-menu .open').removeClass('open');
            li.addClass('open');
            return false;
        }
    });

    var toggle = $('#filter-advanced-toggle');
    if (toggle.length) {
        var fields = toggle.closest('form').children('.field:gt(6)');
        if (!$.cookie('filter_advanced')) {
            toggle.data('show', false);
            fields.hide();
        }
        else {
            toggle.data('show', true);
        }
        toggle.click(function() {
            if ($(this).data('show')) {
                $(this).data('show', false);
                $.cookie('filter_advanced', null);
                fields.hide();
            }
            else {
                $(this).data('show', true);
                $.cookie('filter_advanced', 1);
                fields.show();
            }
        });
    }
});