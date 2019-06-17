(function( $ ) {

$.admin = {

    popup: {
        init: function(selector) {
            $(document).on('click', selector, function() {
                if(!$(this).data('popup')) {
                    if ($(this).hasClass('popup-reload')) {
                        $.admin.popup.open($(this).attr('href'), {
                            close: function() {
                                location.reload();
                            }
                        });
                    }
                    else {
                        $.admin.popup.open($(this).attr('href'));
                    }
                }
                return false;
            });
        },

        open: function(url, options) {
            $('.tip').qtip('hide');
            if(url.indexOf('?popup=1') == -1 && url.indexOf('&popup=1') == -1) {
                if(url.indexOf('?') == -1) {
                    url += '?popup=1';
                }
                else  {
                    url += '&popup=1';
                }
            }
            var params = {
                items: {
                    src: url,
                    type: 'iframe'
                },
                callbacks: {
                    open: function() {
                        $('.mfp-iframe').load(function() {
                            var iframe = $(this).contents();
                            var w = $('#container', iframe).width();
                            if (w < 200) w = 600;
                            $('.mfp-content').css({width: w + 60 + 'px'});
                            var h = $('body', iframe).height();
                            $('.mfp-content').css({height: h +'px'});
                            $('.btn-close-popup', iframe).click(function() {
                                parent.$.magnificPopup.close();
                            });
                        });
                    }
                }
            };
            if (options && options.close) {
                params.callbacks.close = options.close;
            }
            $.magnificPopup.open(params);
        },

        openAjax: function(url) {
            $.magnificPopup.open({
                items: {
                    src: url,
                    type: 'ajax'
                }
            });
        },

        close: function() {
            $.magnificPopup.close();
        },

        closeParent: function() {
            parent.$.magnificPopup.close();
        },

        resizeParent: function() {
            var w = $('#container').width();
            if (w < 200) w = 600;
            parent.$('.mfp-content').css({width: w + 60 + 'px'});
            var h = $('body').height();
            parent.$('.mfp-content').css({height: h +'px'});
        }
    },

    modal: {
        init: function(selector) {
            $(document).on('click', selector, function() {
                $.admin.modal.open($(this).attr('href'));
                return false;
            });
        },

        open: function(src) {
            $.magnificPopup.open({
                items: {
                    src: src,
                    type: 'inline'
                }
            });
        },

        close: function() {
            $.magnificPopup.close();
        }
    },

    image: {
        init: function(selector) {
            $(document).on('click', selector, function() {
                $.admin.image.open($(this).attr('href'));
                return false;
            });
        },

        open: function(src) {
            $.magnificPopup.open({
                items: {
                    src: src,
                    type: 'image'
                },
            });
        }
    },

    tip: {
        init: function(selector) {
            $(document).on('mouseenter', '.tip', function() {
                if (!$(this).data('tip')) {
                    $.admin.tip.add($(this));
                    $(this).mouseenter();
                }
            });
        },

        add: function(e) {
            if (e.data('tip'))
                return;
            e.data('tip', true);
            var my = 'center left';
            var at = 'center right';
            if (e.data('position') == 'left') {
                my = 'center right';
                at = 'center left';
            }
            if (e.data('position') == 'top') {
                my = 'bottom center';
                at = 'top center';
            }
            if (e.data('position') == 'bottom') {
                my = 'top center';
                at = 'bottom center';
            }
            var params = {
                style: {
                    classes: 'qtip-light qtip-shadow'
                },
                show: {
                    delay: 100,
                    solo: true,
                    effect: false
                },
                position: {
                    effect: false,
                    my: my,
                    at: at,
                    viewport: $(window)
                },
                hide: {
                    effect: false,
                    fixed: true,
                    delay: 200
                }
            };
            if (e.data('url')) {
                params['content'] = {
                    text: function (event, api) {
                        $.ajax({
                                url: e.data('url'), // Use data-url attribute for the URL
                                cache: false
                            })
                            .then(function (content) {
                                // Set the tooltip content upon successful retrieval
                                api.set('content.text', content);
                            }, function (xhr, status, error) {
                                // Upon failure... set the  tooltip content to the status and error value
                                api.set('content.text', status + ': ' + error);
                            });
                        return gettext('Loading...'); // Set some initial text
                    }
                }
            }
            else {
                params['content'] = {text: e.children('.hidden')};
            }
            e.qtip(params);
        },

        destroy: function(e) {
            e.qtip('destroy', true);
        }
    },

    changer: {
        init: function(selector) {
            $(document).on('click', selector, $.admin.changer.click);
        },

        click: function() {
            var a = $(this);
            if (a.hasClass('loading'))
                return false;
            if (a.attr('rev') == 'confirm' && !confirm(a.attr('title')))
                return false;
            a.addClass('loading');
            $.post(a.attr('href'), function(data) {
                a.removeClass('loading');
                if (data) {
                    if (data.error) {
                        alert(data.error)
                    }
                    else {
                        var icons = a.data('icons') || 'negative fa-minus-circle,positive fa-check-circle';
                        icons = icons.split(',');
                        for(var i=0;i<icons.length;i++) {
                            a.removeClass(icons[i]);
                        }
                        a.addClass(icons[data.value]);
                    }
                }
            });
            return false;
        }
    },

    dropdown: {
        init: function(selector) {
            $(document).on('click', selector, $.admin.dropdown.click);
        },

        click: function() {
            var toggle = $(this);
            if (toggle.hasClass('dropdown-open')) {
                return true;
            }
            $.admin.dropdown.close();
            if (toggle.data('disabled'))
                return false;
            var position = toggle.position();
            var menu = toggle.parents('.dropdown').find('.dropdown-menu');
            if (menu.data('align') == 'right') {
                menu.css({right: position.left});
            } else {
                menu.css({left: position.left});
            }
            menu.css({top: Math.round(toggle.position().top + toggle.height() + 8) + 'px'});
            menu.addClass('dropdown-open');
            $(document).on('click.admin_dropdown', function(e) {
                var target = $(e.target);
                if (!target.closest('.dropdown-menu').length) {
                    $.admin.dropdown.close();
                }
                if (target.closest('.dropdown-toggle.dropdown-open').length) {
                    return false;
                }
            });
            return false;
        },

        close: function() {
            $('.dropdown-open').removeClass('dropdown-open');
            $(document).unbind('click.admin_dropdown');
        }
    },

    table: {
        init: function (selector) {
            if (typeof selector === 'string' || selector instanceof String) {
                var elements = $(selector);
            }
            else {
                var elements = selector;
            }
            if (elements.length) {
                elements.on('change', 'th.check input', function () {
                    var checked = $(this).is(':checked');
                    $(this).closest('table').children('tbody').children('tr').each(function() {
                        var input = $(this).children('td.check').find('input:enabled');
                        if (input.length) {
                            if (checked) {
                                $(this).addClass('selected');
                                input.prop('checked', true);
                            }
                            else {
                                $(this).removeClass('selected');
                                input.prop('checked', false);
                            }
                        }
                    });
                });
                elements.on('change', 'td.check input', function() {
                    if ($(this).is(':checked')) {
                        $(this).closest('tr').addClass('selected');
                    }
                    else {
                        $(this).closest('tr').removeClass('selected');
                    }
                });
                elements.on('click', 'td.col-editable', function (event) {
                    event.preventDefault();
                    $('.table-edit-box').remove();
                    var td = $(this);
                    var tr = td.closest('tr');
                    var box = $('<div class="table-edit-box"><div class="table-edit-spinner"><i class="fa fa-spinner fa-spin"></i></div></div>');
                    var offset = td.offset();
                    box.appendTo('body');
                    box.css('top', offset.top + 'px');
                    setTimeout(function() { box.addClass('opened') }, 50);
                    var d = $(document).width() - offset.left - box.width() - 50;
                    if (d < 0) {
                        box.css('left', offset.left + d + 'px');
                    }
                    else {
                        box.css('left', offset.left + 'px');
                    }
                    $.ajax({
                        method: 'POST',
                        data: {
                            '_action': 'edit',
                            '_column': td.data('column'),
                            'id': tr.data('id'),
                            'csrfmiddlewaretoken': $.cookie('csrftoken')
                        },
                        dataType: 'json'
                    }).done(function(data) {
                        if (data.success) {
                            box.html(data.content);
                            $.admin.table.initEditBox(box, tr);
                        }
                    }).fail(function(jqXHR, textStatus, errorThrown) {
                        alert(textStatus + ':' + errorThrown);
                    });
                });
            }
        },

        get: function() {
            var result = [];
            this.children('tbody').children('tr').children('td.check').find('input:checked').each(function() {
                result.push($(this).val());
            });
            return result;
        },

        setChecked: function(input) {
            var result = [];
            this.children('tbody').children('tr').children('td.check').find('input:checked').each(function() {
                result.push($(this).val());
            });
            input.val(result.join(','));
            return this;
        },

        initEditBox: function(box, tr) {
            var form = box.find('form').first();
            form.find('input,select,textarea').first().focus().select();
            form.find('.btn-close').click(function() {
                box.remove();
            });
            if (form.find('.ui-autocomplete-input')) {
                $(window).trigger('init-autocomplete');
            }
            form.find('.btn-submit').click(function(event) {
                event.preventDefault();
                var button = $(this);
                button.prop('disabled', true);
                $.ajax({
                    method: 'POST',
                    data: form.serializeArray(),
                    dataType: 'json'
                }).done(function(data) {
                    if (data.success) {
                        tr.after(data.content);
                        tr.remove();
                        box.remove();
                    } else {
                        box.html(data.content);
                        button.prop('disabled', true);
                        $.admin.table.initEditBox(box, tr);
                    }
                }).fail(function(jqXHR, textStatus, errorThrown) {
                    alert(textStatus + ':' + errorThrown);
                    button.prop('disabled', true);
                });
            });
        }
    }
};

    $.fn.adminPopup = function() {
        this.each(function() {
            var a = $(this);
            if(!a.data('popup')) {
                a.data('popup', true);
                a.click(function(){
                    $.admin.popup.open($(this).attr('href'));
                    return false;
                });
            }
        });
        return this;
    };

    $.fn.adminModal = function() {
        this.magnificPopup({
            type:'inline',
            midClick: true
        });
        return this;
    };

    $.fn.adminImage = function() {
        this.magnificPopup({
            type: 'image'
        });
        return this;
    };

    $.fn.adminTip = function() {
        return this.each(function() {
            $.admin.tip.add($(this));
        });
    };

    $.fn.adminChanger = function() {
        this.click($.admin.changer.click);
        return this;
    };

    $.fn.adminTable = function(method) {
        if ($.admin.table[method]) {
            return $.admin.table[method].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof method === 'object' || ! method) {
            return $.admin.table.init.apply(this, arguments);
        }
    };

    $.fn.adminDropdown = function() {
        this.click($.admin.dropdown.click);
        return this;
    };

})(jQuery);