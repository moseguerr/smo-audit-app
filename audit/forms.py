# forms.py
from django import forms
from .models import PairApplication, Pair

class SimplePairGenerationForm(forms.Form):
    """Standalone form for generating resume pairs - no models or admin dependencies."""
    location = forms.ChoiceField(
        choices=[
            ("", "Select location"),
            ("GA", "Georgia"),
            ("NY", "New York"),
            ("MA", "Massachusetts"),
            ("IL", "Illinois"),
            ("CO", "Colorado"),
            ("FLO", "Florida"),
            ("LA", "Louisiana"),
            ("MI", "Michigan"),
            ("PA", "Pennsylvania"),
            ("SFO", "San Francisco"),
            ("TX", "Texas"),
            ("WA", "Washington"),
            ("DMV", "DC Metro Area")
        ]
    )

    occupation = forms.ChoiceField(
        choices=[
            ("", "Select occupation"),
            ("communications", "Communications"),
            ("payroll", "Payroll"),
            ("project_manager", "Project Manager")
        ]
    )

    archetype = forms.CharField(
        max_length=100,
        label="Archetype",
        widget=forms.Select(choices=[("", "Select archetype")])
    )

    def clean_archetype(self):
        """Custom validation for dynamic archetype values."""
        archetype = self.cleaned_data.get('archetype')
        occupation = self.cleaned_data.get('occupation')

        if not archetype:
            raise forms.ValidationError("Please select an archetype.")

        if not occupation:
            raise forms.ValidationError("Please select an occupation first.")

        # Validate against available archetypes for the selected occupation
        from .services import get_available_archetypes
        available_archetypes = get_available_archetypes(occupation)
        valid_archetypes = [arch_tuple[0] for arch_tuple in available_archetypes]

        if archetype not in valid_archetypes:
            raise forms.ValidationError(f"Invalid archetype '{archetype}' for occupation '{occupation}'.")

        return archetype

    def generate_pair_with_pdfs(self):
        """Generate pair with PDFs using thread pool to isolate pyppeteer."""
        if not self.is_valid():
            raise ValueError("Form is not valid")

        location = self.cleaned_data['location']
        occupation = self.cleaned_data['occupation']
        archetype_string = self.cleaned_data['archetype']

        # Convert archetype string to numeric index for the backend
        from .services import get_archetype_index
        archetype = get_archetype_index(occupation, archetype_string)

        # Import required modules
        import sys
        import asyncio
        from pathlib import Path
        from concurrent.futures import ThreadPoolExecutor

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "experiment-design" / "cv-generator" / "code"))

        def run_pyppeteer_in_thread():
            """Run pyppeteer in isolated thread with signal handling patch."""
            import signal

            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Store original signal function
            original_signal = signal.signal

            # Create dummy signal function to bypass pyppeteer's signal setup
            def dummy_signal(*args, **kwargs):
                pass

            try:
                # Temporarily replace signal handler during pyppeteer operations
                signal.signal = dummy_signal

                # Import inside thread to avoid module conflicts
                from resume_randomization import generate_pair, generate_render_and_log_pair_async

                # First get the pair data for display
                pair_data = generate_pair(occupation, location, archetype)

                # Then generate the PDFs using the same pair_id (this returns folder path)
                folder_path = loop.run_until_complete(
                    generate_render_and_log_pair_async(occupation, location, archetype, pair_id=pair_data['pair_id'])
                )

                # Add form parameters to result for display
                pair_data['occupation'] = occupation
                pair_data['location'] = location

                # Convert archetype number to descriptive name
                from .services import ARCHETYPE_NAMES
                archetype_name = next((name for num, name in ARCHETYPE_NAMES.get(occupation, []) if num == archetype), f"Archetype {archetype}")
                pair_data['archetype'] = archetype_name

                pair_data['good_fit_occupations'] = pair_data.get('good_fit_occupations', '')
                pair_data['pair_id'] = pair_data.get('pair_id', '')

                # Convert skills lists to joined strings for display
                if 'resume1' in pair_data and 'skills' in pair_data['resume1']:
                    if isinstance(pair_data['resume1']['skills'], list):
                        pair_data['resume1']['skills'] = '; '.join(pair_data['resume1']['skills'])
                if 'resume2' in pair_data and 'skills' in pair_data['resume2']:
                    if isinstance(pair_data['resume2']['skills'], list):
                        pair_data['resume2']['skills'] = '; '.join(pair_data['resume2']['skills'])

                # Convert good_fit_occupations list to joined string for display
                if 'good_fit_occupations' in pair_data and isinstance(pair_data['good_fit_occupations'], list):
                    pair_data['good_fit_occupations'] = '; '.join(pair_data['good_fit_occupations'])

                # Return both the pair data and folder info
                pair_data['folder_path'] = str(folder_path)
                return pair_data
            finally:
                # Always restore original signal handling
                signal.signal = original_signal
                loop.close()

        # Execute in thread pool to avoid Django's threading issues
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_pyppeteer_in_thread)
            result = future.result()

        # Create minimal pair record for job application workflow
        from .models import Pair, Profile
        pair_obj = Pair.objects.create(
            pair_id=result['pair_id'],
            occupation=occupation,
            good_fit_occupations=result['good_fit_occupations'],
            location=location,
            archetype=archetype,  # Already converted to int
            sublocation=None  # SimplePairGenerationForm doesn't have sublocation
        )

        # Create Profile records for both resumes
        for resume_key, resume_idx in [('resume1', 1), ('resume2', 2)]:
            resume_data = result[resume_key]

            # Convert skills list to string if needed
            skills = resume_data.get('skills', '')
            if isinstance(skills, list):
                skills = '; '.join(skills)

            Profile.objects.create(
                pair=pair_obj,
                full_name=resume_data.get('full_name', ''),
                phone=resume_data.get('phone', ''),
                address=resume_data.get('address', ''),
                email=resume_data.get('email', ''),
                expertise=skills,
                resume_idx=resume_idx
            )

        # Add the database ID to result for template
        result['pair_db_id'] = pair_obj.pk

        return result

    def generate_pair(self):
        """Synchronous fallback - calls basic generate_pair without PDFs."""
        if not self.is_valid():
            raise ValueError("Form is not valid")

        location = self.cleaned_data['location']
        occupation = self.cleaned_data['occupation']
        archetype_string = self.cleaned_data['archetype']

        # Convert archetype string to numeric index for the backend
        from .services import get_archetype_index
        archetype = get_archetype_index(occupation, archetype_string)

        # Import resume_randomization directly
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "experiment-design" / "cv-generator" / "code"))

        from resume_randomization import generate_pair

        # Generate the pair without PDFs
        result = generate_pair(occupation, location, archetype)

        # Add form parameters to result for display
        result['occupation'] = occupation
        result['location'] = location

        # Convert archetype string to descriptive name
        from .services import get_archetype_display_name
        result['archetype'] = get_archetype_display_name(occupation, archetype_string)

        result['good_fit_occupations'] = result.get('good_fit_occupations', '')
        result['pair_id'] = result.get('pair_id', '')

        # Convert skills lists to joined strings for display
        if 'resume1' in result and 'skills' in result['resume1']:
            if isinstance(result['resume1']['skills'], list):
                result['resume1']['skills'] = '; '.join(result['resume1']['skills'])
        if 'resume2' in result and 'skills' in result['resume2']:
            if isinstance(result['resume2']['skills'], list):
                result['resume2']['skills'] = '; '.join(result['resume2']['skills'])

        # Convert good_fit_occupations list to joined string for display
        if 'good_fit_occupations' in result and isinstance(result['good_fit_occupations'], list):
            result['good_fit_occupations'] = '; '.join(result['good_fit_occupations'])

        return result

class PairGenerationForm(forms.Form):
    """Form for generating new resume pairs."""
    location = forms.ChoiceField(
        choices=[
            ("", "Select location"),
            ("GA", "Georgia"),
            ("NY", "New York"),
            ("MA", "Massachusetts"),
            ("IL", "Illinois"),
            ("CO", "Colorado"),
            ("FLO", "Florida"),
            ("LA", "Louisiana"),
            ("MI", "Michigan"),
            ("PA", "Pennsylvania"),
            ("SFO", "San Francisco"),
            ("TX", "Texas"),
            ("WA", "Washington"),
            ("DMV", "DC Metro Area")
        ],
        label="Location",
        help_text="Select location for resume generation"
    )
    occupation = forms.ChoiceField(
        choices=[
            ("", "Select occupation"),
            ("communications", "Communications"),
            ("payroll", "Payroll"),
            ("project_manager", "Project Manager")
        ],
        label="Occupation",
        help_text="Select occupation type"
    )
    archetype = forms.CharField(
        max_length=100,
        label="Archetype",
        help_text="Select archetype specialization",
        widget=forms.Select(choices=[("", "Select archetype")])
    )
    sublocation = forms.CharField(
        max_length=10,
        required=False,
        label="Sublocation",
        help_text="Select specific area within location (optional)",
        widget=forms.Select(choices=[("", "Select sublocation (optional)")])
    )

    def clean_archetype(self):
        """Custom validation for dynamic archetype values."""
        archetype = self.cleaned_data.get('archetype')
        occupation = self.cleaned_data.get('occupation')

        if not archetype:
            raise forms.ValidationError("Please select an archetype.")

        if not occupation:
            raise forms.ValidationError("Please select an occupation first.")

        # Validate against available archetypes for the selected occupation
        from .services import get_available_archetypes
        available_archetypes = get_available_archetypes(occupation)
        valid_archetypes = [arch_tuple[0] for arch_tuple in available_archetypes]

        if archetype not in valid_archetypes:
            raise forms.ValidationError(f"Invalid archetype '{archetype}' for occupation '{occupation}'.")

        return archetype

    def clean_sublocation(self):
        """Custom validation for dynamic sublocation values."""
        sublocation = self.cleaned_data.get('sublocation')
        location = self.cleaned_data.get('location')

        # Sublocation is optional, so empty is allowed
        if not sublocation:
            return sublocation

        if not location:
            raise forms.ValidationError("Please select a location first.")

        # Validate against available sublocations for the selected location
        from .services import get_available_sublocations
        available_sublocations = get_available_sublocations(location)

        # Convert sublocation to integer for validation
        try:
            sublocation_int = int(sublocation)
        except (ValueError, TypeError):
            raise forms.ValidationError("Invalid sublocation format.")

        # Check if sublocation index is valid
        valid_sublocation_indices = [sub_tuple[0] for sub_tuple in available_sublocations]

        if sublocation_int not in valid_sublocation_indices:
            raise forms.ValidationError(f"Invalid sublocation '{sublocation}' for location '{location}'.")

        return sublocation

    def generate_pair(self):
        """Generate and store a new pair with PDFs using thread pool to avoid signal issues."""
        if not self.is_valid():
            raise ValueError("Form is not valid")

        location = self.cleaned_data['location']
        occupation = self.cleaned_data['occupation']
        archetype_string = self.cleaned_data['archetype']
        sublocation = int(self.cleaned_data['sublocation']) if self.cleaned_data['sublocation'] else None

        # Convert archetype string to numeric index for the backend
        from .services import get_archetype_index
        archetype = get_archetype_index(occupation, archetype_string)

        # Auto-select sublocation for single-sublocation locations
        if sublocation is None:
            from .services import get_available_sublocations
            sublocations = get_available_sublocations(location)
            if len(sublocations) == 1:
                sublocation = sublocations[0][0]  # Use the index of the single sublocation

        # Import required modules
        import sys
        import asyncio
        from pathlib import Path
        from concurrent.futures import ThreadPoolExecutor

        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "experiment-design" / "cv-generator" / "code"))

        def run_pyppeteer_in_thread():
            """Run pyppeteer in isolated thread with signal handling patch."""
            import signal

            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Store original signal function
            original_signal = signal.signal

            # Create dummy signal function to bypass pyppeteer's signal setup
            def dummy_signal(*args, **kwargs):
                pass

            try:
                # Temporarily replace signal handler during pyppeteer operations
                signal.signal = dummy_signal

                # Import inside thread to avoid module conflicts
                from resume_randomization import generate_pair, generate_render_and_log_pair_async

                # First get the pair data for display
                pair_data = generate_pair(occupation, location, archetype, sublocation)

                # Then generate the PDFs using the same pair_id (this returns folder path)
                folder_path = loop.run_until_complete(
                    generate_render_and_log_pair_async(occupation, location, archetype, sublocation, pair_id=pair_data['pair_id'])
                )

                # Add form parameters to result for display
                pair_data['occupation'] = occupation
                pair_data['location'] = location

                # Convert archetype string to descriptive name
                from .services import get_archetype_display_name
                pair_data['archetype'] = get_archetype_display_name(occupation, archetype_string)

                # Convert sublocation number to descriptive name
                if sublocation:
                    from .services import HARDCODED_SUBLOCATIONS
                    sublocation_name = next((name for num, name in HARDCODED_SUBLOCATIONS.get(location, []) if num == sublocation), f"Sublocation {sublocation}")
                    pair_data['sublocation'] = sublocation_name
                else:
                    pair_data['sublocation'] = None  # Template will show "Not specified"
                pair_data['good_fit_occupations'] = pair_data.get('good_fit_occupations', '')
                pair_data['pair_id'] = pair_data.get('pair_id', '')

                # Convert skills lists to joined strings for display
                if 'resume1' in pair_data and 'skills' in pair_data['resume1']:
                    if isinstance(pair_data['resume1']['skills'], list):
                        pair_data['resume1']['skills'] = '; '.join(pair_data['resume1']['skills'])
                if 'resume2' in pair_data and 'skills' in pair_data['resume2']:
                    if isinstance(pair_data['resume2']['skills'], list):
                        pair_data['resume2']['skills'] = '; '.join(pair_data['resume2']['skills'])

                # Convert good_fit_occupations list to joined string for display
                if 'good_fit_occupations' in pair_data and isinstance(pair_data['good_fit_occupations'], list):
                    pair_data['good_fit_occupations'] = '; '.join(pair_data['good_fit_occupations'])

                # Return both the pair data and folder info
                pair_data['folder_path'] = str(folder_path)
                return pair_data
            finally:
                # Always restore original signal handling
                signal.signal = original_signal
                loop.close()

        # Execute in thread pool to avoid Django's threading issues
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_pyppeteer_in_thread)
            result = future.result()

        # Create minimal pair record for job application workflow
        from .models import Pair, Profile
        pair_obj = Pair.objects.create(
            pair_id=result['pair_id'],
            occupation=occupation,
            good_fit_occupations=result['good_fit_occupations'],
            location=location,
            archetype=archetype,  # Already converted to int
            sublocation=sublocation  # PairGenerationForm has sublocation support
        )

        # Create Profile records for both resumes
        for resume_key, resume_idx in [('resume1', 1), ('resume2', 2)]:
            resume_data = result[resume_key]

            # Convert skills list to string if needed
            skills = resume_data.get('skills', '')
            if isinstance(skills, list):
                skills = '; '.join(skills)

            Profile.objects.create(
                pair=pair_obj,
                full_name=resume_data.get('full_name', ''),
                phone=resume_data.get('phone', ''),
                address=resume_data.get('address', ''),
                email=resume_data.get('email', ''),
                expertise=skills,
                resume_idx=resume_idx
            )

        # Add the database ID to result for template
        result['pair_db_id'] = pair_obj.pk

        return result

class PairApplicationForm(forms.ModelForm):
    """Form for creating job applications with existing pairs."""
    pair_id_display = forms.CharField(label="Pair ID", disabled=True, required=False)
    occupation_display = forms.CharField(label="Occupation", disabled=True, required=False)

    class Meta:
        model = PairApplication
        fields = [
            "pair", "employer",
            "pair_id_display", "occupation_display",
            "job_title", "job_text",
            "job_location", "work_mode",
            "job_link", "job_board", "job_board_other", "days_open"
        ]
        widgets = {
            'pair': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If pair parameter exists, populate display fields AND set the actual pair field
        if "pair" in self.initial:
            try:
                pair = Pair.objects.get(pk=self.initial["pair"])
                # Set display fields for user visibility
                self.fields["occupation_display"].initial = pair.occupation
                self.fields["pair_id_display"].initial = pair.pair_id
                # Set the actual pair field for form submission (if it exists)
                if "pair" in self.fields:
                    self.fields["pair"].initial = pair
            except Pair.DoesNotExist:
                pass

        # Employer field setup
        self.fields['employer'].help_text = "Use the 'Add Employer' button to add an employer."
            

