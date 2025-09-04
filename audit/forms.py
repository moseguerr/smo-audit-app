# forms.py
from django import forms
from .models import PairApplication, Pair

class PairApplicationForm(forms.ModelForm):
    pair_id_display = forms.CharField(label="Pair ID", disabled=True, required=False)
    occupation_display = forms.CharField(label="Occupation", disabled=True, required=False)
    created_at_display = forms.CharField(label="Created At", disabled=True, required=False)
    updated_at_display = forms.CharField(label="Last Modified", disabled=True, required=False)


    class Meta:
        model = PairApplication
        fields = [
            "pair", "employer",
            "pair_id_display", "occupation_display",  # show both, read-only
            "job_title", "job_text",
            "job_location", "work_mode",
            "job_link", "job_board", "job_board_other",
            
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        pair = None
        # If form is initialized from URL param (via GET)
        if "pair" in self.initial:
            try:
                pair = Pair.objects.get(pk=self.initial["pair"])
            except Pair.DoesNotExist:
                pass
        # If editing an existing instance
        elif self.instance and self.instance.pair_id:
            pair = self.instance.pair

        if pair:
            self.fields["pair_id_display"].initial = pair.pair_id
            self.fields["occupation_display"].initial = pair.occupation
            
            # Inject occupation into Add Employer popup URL
            rel = self.fields["employer"].widget
            rel.widget.attrs.update({"data-occupation": pair.occupation.strip().title()})



