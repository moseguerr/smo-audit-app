// Wait for jQuery to be available
(function() {
    function initEmployerCheck() {
        var $ = django.jQuery;  // Use Django's jQuery
        
        console.log("Employer.js loaded successfully!");
        
        var field = $("#id_display_name");
        var saveButtons = $("input[name='_save'], input[name='_addanother'], input[name='_continue']");
        
        // Initially disable save buttons
        saveButtons.prop("disabled", true);
        
        // Add check button and message div dynamically
        if (field.length) {
            // Create check button
            var checkButton = $('<button type="button" class="button" id="check-employer-btn" style="margin-left: 10px;">Check</button>');
            field.after(checkButton);
            
            // Create message area
            var messageDiv = $('<div id="check-result" style="margin-top: 5px; font-weight: bold; min-height: 20px;"></div>');
            checkButton.after(messageDiv);
            
            function runCheck() {
                var employer = field.val().trim();
                var occ = new URLSearchParams(window.location.search).get("occupation");
                
                if (!employer) {
                    messageDiv.html('<span style="color: red;">Please enter an employer name first</span>');
                    saveButtons.prop("disabled", true);
                    return;
                }
                
                messageDiv.html('<span style="color: blue;">Checking...</span>');
                
                $.get(window.location.pathname.replace("/add/", "/check/"),
                      {employer: employer, occupation: occ},
                      function(data) {
                    if (data.ok) {
                        messageDiv.html('<span style="color: green;">✓ ' + data.message + '</span>');
                        saveButtons.prop("disabled", false);
                        field.css("border-color", "green");
                    } else {
                        messageDiv.html('<span style="color: red;">✗ ' + data.error + '</span>');
                        saveButtons.prop("disabled", true);
                        field.css("border-color", "red");
                    }
                }).fail(function() {
                    messageDiv.html('<span style="color: red;">Error checking employer</span>');
                    saveButtons.prop("disabled", true);
                });
            }
            
            // Bind check button click
            checkButton.on("click", runCheck);
            
            // Optional: Auto-check when user leaves the field
            field.on("blur", function() {
                if (field.val().trim()) {
                    runCheck();
                }
            });
            
            // Clear message when user starts typing again
            field.on("input", function() {
                messageDiv.html('');
                field.css("border-color", "");
                saveButtons.prop("disabled", true);
            });
        }
    }
    
    // Initialize when DOM is ready
    if (typeof django !== 'undefined' && django.jQuery) {
        django.jQuery(document).ready(initEmployerCheck);
    } else {
        // Fallback if django.jQuery isn't available yet
        document.addEventListener('DOMContentLoaded', function() {
            if (typeof django !== 'undefined' && django.jQuery) {
                initEmployerCheck();
            }
        });
    }
})();