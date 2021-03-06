$(document).ready(function() {
  $('.select2-widget').select2({
    placeholder: '',
    ajax: {
      dataType: 'json'
    }
  });

  $('.select2-container').on('keydown', function (e) {
      if (e.keyCode === 13) {
        $(this).closest('form').submit();
      }
  });

});