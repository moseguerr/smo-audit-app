from django.contrib import admin
from django import forms
from .forms import PairApplicationForm
from .models import Pair, Profile, Employer, PairApplication, normalize_employer_name, CallbackLog
from django.utils.timezone import localtime
from django.http import HttpResponse, JsonResponse
from django.utils.html import format_html
from django.urls import reverse, path
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render


class ProfileInline(admin.TabularInline):
    model = Profile
    extra = 0
    can_delete = False
    readonly_fields = ("full_name", "phone", "address", "email", "expertise", "resume_pdf_download")
    fields = ("full_name", "phone", "address", "email", "expertise", "resume_pdf_download")
    show_change_link = False
    max_num = 0

    def resume_pdf_download(self, obj):
        """Display PDF download link."""
        if obj.resume_pdf and obj.resume_pdf.name:
            return format_html(
                '<a href="{}" target="_blank" class="button">Download PDF</a>',
                obj.resume_pdf.url
            )
        return "No PDF available"
    resume_pdf_download.short_description = "Resume PDF"


@admin.register(Pair)
class PairAdmin(admin.ModelAdmin):
    list_display = ("pair_id", "occupation", "location", "archetype")
    list_filter = ("occupation", "location", "archetype")
    search_fields = ("pair_id", "occupation")
    readonly_fields = ("pair_id", "occupation", "good_fit_occupations", "location", "archetype", "sublocation")
    fieldsets = ()

    # use our custom template for the bottom area
    change_form_template = "admin/pair_change_form.html"

    def changelist_view(self, request, extra_context=None):
        """Show generation form as default view instead of pair list."""
        return self.generate_pair_view(request)

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        # Hide save buttons — Pair is read-only
        context.update({
            "show_save": False,
            "show_save_and_continue": False,
            "show_save_and_add_another": False,
            "show_delete": False,
            "title": "View pair",
        })

        # Build the popup button HTML in Python (safe)
        if obj:
            url = reverse("admin:audit_pairapplication_add") + f"?pair={obj.pk}"
            context["add_application_html"] = format_html(
                '<div style="margin-top:20px;margin-bottom:6px;">'
                '<button onclick="window.open(\'{}\', \'jobAppWindow\', \'width=900,height=700,scrollbars=yes,resizable=yes\')" class="button default" style="background:#417690;color:white;padding:10px 15px;font-weight:bold;border:none;cursor:pointer;">'
                '➕ Add Job Application for this Pair</button>'
                '</div>',
                url,
            )

            # Add archetype and sublocation display names for template
            from .services import get_archetype_display_name, HARDCODED_SUBLOCATIONS

            archetype_display = obj.archetype
            if obj.archetype and obj.occupation:
                # Convert numeric archetype back to string first, then get display name
                archetype_mappings = {
                    1: {'communications': 'digital_communications_specialist', 'payroll': 'payroll_systems_specialist', 'project_manager': 'environmental_project_manager'},
                    2: {'communications': 'strategic_internal_communications', 'payroll': 'payroll_compliance_manager', 'project_manager': 'energy_program_manager'},
                    3: {'communications': 'public_relations_specialist', 'payroll': 'hr_payroll_generalist', 'project_manager': ''},
                    4: {'communications': 'brand_content_marketing', 'payroll': '', 'project_manager': ''}
                }
                if obj.archetype in archetype_mappings and obj.occupation in archetype_mappings[obj.archetype]:
                    archetype_string = archetype_mappings[obj.archetype][obj.occupation]
                    if archetype_string:
                        archetype_display = get_archetype_display_name(obj.occupation, archetype_string)

            sublocation_display = obj.sublocation
            if obj.sublocation and obj.location and obj.location in HARDCODED_SUBLOCATIONS:
                sublocations = HARDCODED_SUBLOCATIONS[obj.location]
                if sublocations:
                    for idx, name in sublocations:
                        if idx == obj.sublocation:
                            sublocation_display = name
                            break

            context["archetype_display"] = archetype_display
            context["sublocation_display"] = sublocation_display

            # Add folder path for PDFs
            context["folder_path"] = f"/Users/mgor/Repositories/nonprofit/experiment-design/cv-generator/resumes/{obj.pair_id}/"
        else:
            context["add_application_html"] = ""

        return super().render_change_form(request, context, add, change, form_url, obj)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("list/", self.admin_site.admin_view(self.pairs_list_view), name="audit_pair_list"),
        ]
        return custom_urls + urls

    def generate_pair_view(self, request):
        """Primary admin view for generating new pairs."""
        from .forms import PairGenerationForm
        from django.contrib import messages

        result = None

        if request.method == 'POST':
            form = PairGenerationForm(request.POST)
            if form.is_valid():
                try:
                    result = form.generate_pair()
                    messages.success(request, f'Successfully generated pair {result["pair_id"]} with PDFs!')
                except Exception as e:
                    messages.error(request, f'Error generating pair: {str(e)}')
        else:
            form = PairGenerationForm()

        context = dict(
            self.admin_site.each_context(request),
            title='Generate New Resume Pair',
            form=form,
            result=result,
            opts=self.model._meta,
            app_label=self.model._meta.app_label,
            show_pairs_list_button=True,
        )

        return render(request, 'admin/audit/generate_pair.html', context)

    def pairs_list_view(self, request):
        """Secondary view to show existing pairs list."""
        # Call the original changelist_view to show existing pairs
        extra_context = {'show_generate_button': True}
        return super().changelist_view(request, extra_context)


@admin.register(Employer)
class EmployerAdmin(admin.ModelAdmin):
    list_display = ("display_name", "normalized_name", "employer_location", "number_employees", "industry", "glassdoor_score")
    list_filter = ("industry", "glassdoor_score")
    search_fields = ("display_name", "employer_location", "industry")
    
    fieldsets = (
        ("Basic Information", {
            "fields": ("display_name", "employer_location", "industry")
        }),
        ("Metrics", {
            "fields": ("number_employees", "glassdoor_score", "diversity_score", "openings_number", "mission_statement")
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("check/", self.admin_site.admin_view(check_employer), name="employer-check"),
        ]
        return custom_urls + urls

    class Media:
        js = ("admin/js/employer.js",)


@staff_member_required
def check_employer(request):
    employer_name = request.GET.get("employer")
    occupation = request.GET.get("occupation")

    if not employer_name or not occupation:
        return JsonResponse({"ok": False, "error": "Missing employer or occupation"})

    normalized = normalize_employer_name(employer_name)
    normalized_occupation = occupation.strip().capitalize()
    
    exists = PairApplication.objects.filter(
        employer__normalized_name=normalized,
        occupation=normalized_occupation
    ).exists()

    if exists:
        return JsonResponse({
            "ok": False, 
            "error": f"This employer already has an application for {normalized_occupation}"
        })
    
    return JsonResponse({
        "ok": True, 
        "message": f"OK - {employer_name} can receive an application for {normalized_occupation}"
    })


class CallbackLogInline(admin.TabularInline):
    model = CallbackLog
    extra = 0
    max_num = 2  # Maximum 2 entries (one per profile)
    fields = ('profile_display', 'callback_status', 'callback_date', 'callback_medium', 'callback_notes')
    readonly_fields = ('profile_display',)
    
    def profile_display(self, obj):
        """Display the profile's full name"""
        return obj.profile.full_name if obj.profile else "-"
    profile_display.short_description = 'Profile Name'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('profile').order_by('profile__full_name')
    
    def has_add_permission(self, request, obj=None):
        # Don't allow manual adding
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deleting
        return False


@admin.register(PairApplication)
class PairApplicationAdmin(admin.ModelAdmin):
    form = PairApplicationForm
    list_display = ("pair", "job_title", "employer", "status", "submitted_at", "callback_summary", "created_at")
    list_filter = ("status", "work_mode", "job_board", "created_at")
    search_fields = (
        "job_title",
        "employer__display_name",
        "pair__pair_id",
        "pair__profiles__full_name",  # Search by candidate name
        "pair__profiles__email",      # Search by email
        "pair__profiles__phone"       # Search by phone
    )
    ordering = ("-created_at",)

    inlines = [CallbackLogInline]

    def callback_summary(self, obj):
        """Show summary of callback statuses"""
        callbacks = obj.callbacks.all()
        if callbacks.count() == 0:
            return "Not initialized"
        
        statuses = []
        for callback in callbacks:
            if callback.callback_status == 'callback':
                statuses.append(f"✓ {callback.profile.full_name}")
            elif callback.callback_status == 'rejection':
                statuses.append(f"✗ {callback.profile.full_name}")
            else:
                statuses.append(f"⏳ {callback.profile.full_name}")
        
        return " | ".join(statuses)
    callback_summary.short_description = 'Callback Status'
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        self._ensure_callback_logs(obj)
    
    def save_formset(self, request, form, formset, change):
        super().save_formset(request, form, formset, change)
        if hasattr(form.instance, 'pair'):
            self._ensure_callback_logs(form.instance)
    
    def _ensure_callback_logs(self, application):
        """Ensure exactly 2 callback logs exist for this application"""
        if application.pair:
            for profile in application.pair.profiles.all():
                CallbackLog.objects.get_or_create(
                    profile=profile,
                    application=application,
                    defaults={'callback_status': 'no_info'}
                )
    
    fieldsets = (
        ("Pair Info", {"fields": ("pair_id_display", "occupation_display")}),
        ("Employer", {"fields": ("employer",)}),
        ("Job Information", {"fields": ("job_title", "job_text")}),
        ("Location & Work Mode", {"fields": ("job_location", "work_mode")}),
        ("Posting Details", {"fields": ("job_link", "job_board", "job_board_other", "days_open")}),
    )


    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        # Customize button labels and handle read-only state for submitted applications
        if obj and obj.status == "submitted":
            # Submitted applications are read-only
            context.update({
                "show_save": False,
                "show_save_and_continue": False,
                "show_save_and_add_another": False,
                "show_delete": False,
                "title": f"View Job Application (Submitted {obj.submitted_at.strftime('%m/%d/%Y') if obj.submitted_at else ''})",
            })
        else:
            # Draft applications or new applications can be edited
            context.update({
                "save_text": "SUBMIT",
                "save_and_add_another_text": "Submit and add another",
                "save_and_continue_text": "Save and continue editing",
            })

        return super().render_change_form(request, context, add, change, form_url, obj)

    def save_model(self, request, obj, form, change):
        # Detect which button was clicked and set status accordingly
        if "_save" in request.POST:  # SUBMIT button
            obj.status = "submitted"
            if not obj.submitted_at:
                from django.utils import timezone
                obj.submitted_at = timezone.now()
        elif "_continue" in request.POST:  # Save and continue editing
            obj.status = "draft"
        elif "_addanother" in request.POST:  # Submit and add another
            obj.status = "submitted"
            if not obj.submitted_at:
                from django.utils import timezone
                obj.submitted_at = timezone.now()

        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        # Make all fields readonly for submitted applications
        if obj and obj.status == "submitted":
            return [field.name for field in self.model._meta.fields if field.name != "id"]
        return self.readonly_fields

    def get_changeform_initial_data(self, request):
        # Handle pair parameter from URL for new applications
        initial = super().get_changeform_initial_data(request)

        # Only add pair if it's not already set and we have a pair parameter
        if 'pair' in request.GET and 'pair' not in initial:
            try:
                pair_id = request.GET['pair']
                pair = Pair.objects.get(pk=pair_id)
                initial['pair'] = pair  # Set the Pair object, not just the ID
            except (Pair.DoesNotExist, ValueError):
                # If pair doesn't exist or invalid ID, don't set it
                pass

        return initial

    def changelist_view(self, request, extra_context=None):
        # Custom grouped view by status
        if 'status' not in request.GET:
            # Group applications by status for display
            draft_apps = PairApplication.objects.filter(status='draft').order_by('-updated_at')
            submitted_apps = PairApplication.objects.filter(status='submitted').order_by('-submitted_at', '-created_at')

            context = {
                'draft_applications': draft_apps,
                'submitted_applications': submitted_apps,
                'title': 'Job Applications',
                'opts': self.model._meta,
                'app_label': self.model._meta.app_label,
                'has_add_permission': self.has_add_permission(request),
                'has_change_permission': self.has_change_permission(request),
                'has_delete_permission': self.has_delete_permission(request),
            }
            if extra_context:
                context.update(extra_context)

            return render(request, 'admin/audit/pairapplication/change_list.html', context)

        # Fall back to default view if status filter is applied
        return super().changelist_view(request, extra_context)

    class Media:
        js = ("admin/js/pairapplication.js",)