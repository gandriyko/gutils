$(document).ready(function(){
    $('#folder').change(function() {
        location.href = $(this).val();
    });

    $('#folder-create').click(function() {
        var folder = prompt($(this).attr('title'));
        if (!folder)
            return false;
        $(this).val(folder);
    });

    $('#folder-delete').click(function() {
        return confirm($(this).attr('title') + ' "'+$(this).val()+ '"');
    });

    $('#image-upload').click(function() {
        $('#id_image').click();
        return false;
    });

    $('#id_image').change(function() {
        $(this).closest('form').submit();
    });

    $('#id_naming').change(function() {
        $.cookie('image-naming', $(this).val());
    });

    var selected = 0;
    var img = new Image();
    var imgWidth = 0;
    var imgHeight = 0;
    var imgRatio = 1;

    img.onload = function () {
        if (img.width) {
            imgRatio = img.height / img.width;
        }
        else {
            imgRatio = 1;
        }
        $('#image-size').change();
    };

    function setSize(width, height) {
        if (width || height) {
            if ($('#image-ratio').is(':checked')) {
                if (width) {
                    imgWidth = width;
                    imgHeight = Math.round(imgWidth * imgRatio);
                } else {
                    imgHeight = height;
                    imgWidth = Math.round(imgHeight / imgRatio);
                }
            }
            else {
                imgWidth = width;
                imgHeight = height;
            }
        } else {
            imgWidth = img.width;
            imgHeight = img.height;
        }
        $('#image-width').val(imgWidth);
        $('#image-height').val(imgHeight);
    }

    $('#image-size').change(function() {
        if (selected) {
            if ($(this).val()) {
                var size = $(this).val().split('x');
                setSize(Number(size[0]), Number(size[1]));
            } else {
                setSize(0, 0);
            }
        }
    });

    $('#image-ratio').change(function() {
        if ($(this).is(':checked') && selected) {
            setSize(imgWidth, imgHeight);
        }
    });

    $('#image-width').keyup(function() {
        if ($('#image-ratio').is(':checked'))
            setSize(Number($(this).val()), 0);
    });

    $('#image-height').keyup(function() {
        if ($('#image-ratio').is(':checked'))
            setSize(0, Number($(this).val()));
    });

    $('.image-list .image').click(function() {
        if (selected){
            $(selected).removeClass('selected');
        }
        selected = $(this);
        selected.addClass('selected');
        img.src = selected.data('src');
        $('#image-url').attr('href', img.src).text(img.src);
        $('#image-delete').show();
        return false;
    });

    $('#image-delete').click(function() {
        var image = selected.attr('title');
        if (selected && confirm($(this).attr('title')+' "'+image+'"')) {
            $(this).val(image);
        }
        else {
            return false;
        }
    });

    $('#image-insert').click(function() {
        if (!selected)
            return false;
        var src = selected.data('src');
        var caption = $('#image-caption').val();
        var align = $('#image-align').val();
        if (align)
            align = ' align="'+align+'"';
        var size = (img.width != imgWidth || img.height != imgHeight) ? ' width="'+imgWidth+'" height="'+imgHeight+'"' : '';
        var html = '<img src="'+src+'" alt="'+caption+'"'+align+size+'/>';
        if ($('#image-zooming').is(':checked'))
            html = '<a href="'+src+'" title="'+caption+'" class="image-box"">'+html+'</a>';

        $.cookie('image-align', $('#image-align').val());
        $.cookie('image-zooming', $('#image-zooming').is(':checked'));
        $.cookie('image-ratio', $('#image-ratio').is(':checked'));
        $.cookie('image-size', $('#image-size').val());

        //parent.tinymce.activeEditor.insertContent(html);
        //parent.tinymce.activeEditor.windowManager.close();
        return false;
    });

    if ($.cookie('image-naming'))
        $('#id_naming').val($.cookie('image-naming'));
    if ($.cookie('image-size'))
        $('#image-size').val($.cookie('image-size'));
    if ($.cookie('image-align'))
        $('#image-align').val($.cookie('image-align'));
    if ($.cookie('image-ratio') == 'false')
        $('#image-ratio').prop('checked', false);
    if ($.cookie('image-zooming') == 'false')
        $('#image-zooming').prop('checked', false);
});