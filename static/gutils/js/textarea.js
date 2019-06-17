$(document).ready(function() {
    var tinyParams = {
        selector: "textarea.rich-editor",
        language: "uk",
        relative_urls: false,
        convert_urls: false,
        auto_cleanup_word : true,
        remove_script_host : false,
        plugins: [
                    "advlist autolink autosave link image lists charmap print preview hr anchor pagebreak",
                    "searchreplace wordcount visualblocks visualchars code fullscreen insertdatetime media nonbreaking",
                    "table contextmenu directionality template textcolor paste textcolor images"
        ],
        toolbar: "pastetext | bold italic | styleselect | bullist numlist | undo redo removeformat | table images media link | visualblocks code fullscreen",
        menubar: false,
        statusbar: false,
        toolbar_items_size: "small",
        content_css : "/static/gutils/css/tiny.css",
        height : "250",
        extended_valid_elements:"script[language|type|src]",
        auto_cleanup_word : true,
        paste_create_paragraphs : false,
        paste_create_linebreaks : false,
        paste_remove_styles: true,
        paste_remove_styles_if_webkit: true,
        paste_strip_class_attributes: true,
        paste_as_text: true,
        paste_use_dialog : true,
        paste_auto_cleanup_on_paste : true,
        paste_convert_middot_lists : false,
        paste_unindented_list_class : "unindentedList",
        paste_convert_headers_to_strong : true,
        forced_root_block: false,
        force_br_newlines : false,
        force_p_newlines : false
    };

    if (!typeof tiny_height === 'undefined') {
        tinyParams['height'] = tiny_height;
    };

    if (!typeof tiny_width === 'undefined') {
        tinyParams['width'] = tiny_width;
    };
    
    tinymce.init(tinyParams);
});