/* Project specific Javascript goes here. */
$(document).ready(function () {
    $("#input_form").submit(function () {
        $("#form_container").attr("style", "display: none");
        $("#hidden_section").attr("style", "display: block");
        return true;
    });
});
