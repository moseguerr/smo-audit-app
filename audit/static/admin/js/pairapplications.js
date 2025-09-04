(function($) {
    $(document).ready(function() {
        // Show job_board_other only if "Other" selected
        function toggleOtherField() {
            if ($("#id_job_board").val() === "other") {
                $("#id_job_board_other").closest(".form-row").show();
            } else {
                $("#id_job_board_other").closest(".form-row").hide();
                $("#id_job_board_other").val("");
            }
        }
        toggleOtherField();
        $("#id_job_board").change(toggleOtherField);

        // Append occupation to Employer popup link
       (function($) {
    $(document).ready(function() {
        $("a.add-related").on("click", function() {
            var occ = $("#id_occupation_display").val();
            if (occ) {
                var url = $(this).attr("href");
                if (url.indexOf("occupation=") === -1) {
                    url += (url.indexOf("?") === -1 ? "?" : "&") + "occupation=" + encodeURIComponent(occ);
                    $(this).attr("href", url);
                }
            }
        });
    });
})(django.jQuery);

