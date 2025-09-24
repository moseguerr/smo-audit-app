(function() {
    function initPairApplication() {
        var $ = django.jQuery;
        
        console.log("PairApplication.js loaded!");

        // Dynamic sublocation loading
        function loadSublocations() {
            var locationValue = $("#id_location").val();
            var sublocationField = $("#id_sublocation");

            if (!locationValue) {
                // Clear sublocation options if no location selected
                sublocationField.empty().append('<option value="">Select sublocation (optional)</option>');
                return;
            }

            // Make AJAX request to get sublocations
            $.get('/audit/ajax/sublocations/', {location: locationValue})
                .done(function(data) {
                    sublocationField.empty().append('<option value="">Select sublocation (optional)</option>');

                    if (data.sublocations && data.sublocations.length > 0) {
                        $.each(data.sublocations, function(index, sublocation) {
                            sublocationField.append(
                                '<option value="' + sublocation.value + '">' + sublocation.label + '</option>'
                            );
                        });
                    }
                })
                .fail(function(xhr, status, error) {
                    console.error('Error loading sublocations:', error);
                });
        }

        // Bind location change event
        $("#id_location").change(loadSublocations);

        // Show job_board_other only if "Other" selected
        function toggleOtherField() {
    		var jobBoardValue = $("#id_job_board").val();
    		var otherField = $("#id_job_board_other").closest(".form-row");
    
    		if (jobBoardValue === "other") {
        		otherField.show();
    		} else {
        		otherField.hide();
        		$("#id_job_board_other").val("");  // Clear the field when hidden
    		}
	}

	// Make sure to run this when the page loads to set initial state
	toggleOtherField();
	$("#id_job_board").change(toggleOtherField);
        
        // Debug: Check if occupation field exists and has value
        var occField = $("#id_occupation_display");
        console.log("Occupation field found:", occField.length > 0);
        console.log("Occupation value:", occField.val());
        
        // Debug: Check if add-related links exist
        var addLinks = $("a.add-related");
        console.log("Add-related links found:", addLinks.length);
        
        // Customize Add Employer button and prevent dropdown usage
        var employerField = $("#id_employer");
        var employerAddButton = $(".field-employer .add-related");

        // Make dropdown non-functional but keep it visible for Django
        if (employerField.length > 0) {
            employerField.css({
                'pointer-events': 'none',
                'background-color': '#f8f8f8',
                'color': '#999'
            });
        }

        if (employerAddButton.length > 0) {
            // Change button text to "Add Employer"
            employerAddButton.text("Add Employer");
            employerAddButton.css({
                'background': '#417690',
                'color': 'white',
                'padding': '8px 12px',
                'text-decoration': 'none',
                'border-radius': '4px',
                'font-weight': 'bold'
            });
        }

        // Append occupation to Employer popup link
        $("a.add-related").on("click", function(e) {
            console.log("Add-related link clicked!");

            var occ = $("#id_occupation_display").val();
            console.log("Occupation from field:", occ);

            if (occ) {
                var url = $(this).attr("href");
                console.log("Original URL:", url);

                if (url.indexOf("occupation=") === -1) {
                    url += (url.indexOf("?") === -1 ? "?" : "&") + "occupation=" + encodeURIComponent(occ);
                    console.log("Modified URL:", url);
                    $(this).attr("href", url);
                }
            } else {
                console.log("No occupation value found!");
            }
        });
    }
    
    // Initialize when DOM is ready
    if (typeof django !== 'undefined' && django.jQuery) {
        django.jQuery(document).ready(initPairApplication);
    } else {
        document.addEventListener('DOMContentLoaded', function() {
            if (typeof django !== 'undefined' && django.jQuery) {
                initPairApplication();
            }
        });
    }
})();