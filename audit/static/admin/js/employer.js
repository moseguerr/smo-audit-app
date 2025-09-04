

(function($) {
    $(document).ready(function() {
        var field = $("#id_display_name");

        if (field.length) {
            var saveButtons = $("input[name='_save'], input[name='_addanother'], input[name='_continue']");
            saveButtons.prop("disabled", true); // disabled by default

            function runCheck() {
                var employer = field.val();
                var occ = new URLSearchParams(window.location.search).get("occupation");

                if (!employer) {
                    saveButtons.prop("disabled", true);
                    return;
                }

                $.get(window.location.pathname.replace("/add/", "/check/"),
                      {employer: employer, occupation: occ},
                      function(data) {
                    if (data.ok) {
                        saveButtons.prop("disabled", false);
                        field.css("border-color", "green"); // visual cue
                    } else {
                        alert(data.error);
                        window.close();
                    }
                });
            }

            // Auto-check when user leaves the field
            field.on("blur", runCheck);

            // Optional manual retry button
            var btn = $('<button type="button" class="button">Check Employer</button>');
            field.after(btn);
            btn.on("click", runCheck);
        }
    });
})(django.jQuery);
