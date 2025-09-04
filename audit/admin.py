from django.contrib import admin
from django import forms
from .forms import PairApplicationForm
from .models import Pair, Profile, Employer, PairApplication
from django.utils.timezone import localtime
from django.http import HttpResponse, JsonResponse
from django.utils.html import format_html
from django.urls import reverse, path
from django.contrib.admin.views.decorators import staff_member_required

class ProfileInline(admin.TabularInline):
    model = Profile
    extra = 0
    can_delete = False
    readonly_fields = ("first_name", "last_name", "expertise")
    show_change_link = False
    max_num = 0

@admin.register(Pair)
class PairAdmin(admin.ModelAdmin):
    list_display = ("pair_id", "occupation")
    search_fields = ("pair_id", "occupation")
    readonly_fields = ("pair_id", "occupation", "good_fit_occupations")
    fieldsets = ((None, {"fields": ("pair_id", "occupation", "good_fit_occupations")}),)
    inlines = [ProfileInline]

    # use our custom template for the bottom area
    change_form_template = "admin/pair_change_form.html"

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        # Hide save buttons — Pair is read-only
        context.update({
            "show_save": False,
            "show_save_and_continue": False,
            "show_save_and_add_another": False,
            "show_delete": False,
        })

        # Build the popup button HTML in Python (safe)
        if obj:
            url = reverse("admin:audit_pairapplication_add") + f"?pair={obj.pk}"
            context["add_application_html"] = format_html(
                '<div style="margin-top:20px;margin-bottom:6px;">'
                '<a href="{}" class="button addlink" '
                'onclick="return showAddAnotherPopup(this);">➕ Add Job Application</a>'
                '</div>',
                url,
            )
        else:
            context["add_application_html"] = ""

        return super().render_change_form(request, context, add, change, form_url, obj)


@admin.register(Employer)
class EmployerAdmin(admin.ModelAdmin):
    list_display = ("display_name", "normalized_name", "employer_location", "number_employees", "industry")

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

    normalized = employer_name.lower().replace(".", "").replace(",", "").strip()
    exists = PairApplication.objects.filter(
        employer__normalized_name=normalized,
        occupation=occupation.strip().title()
    ).exists()

    if exists:
        return JsonResponse({"ok": False, "error": "This employer already has an application for this occupation"})
    return JsonResponse({"ok": True, "message": "OK — you can proceed"})



@admin.register(PairApplication)
class PairApplicationAdmin(admin.ModelAdmin):
    form = PairApplicationForm
    list_display = ("pair", "job_title", "employer", "created_at", "updated_at")
    list_filter = ("work_mode", "job_board", "created_at")
    search_fields = ("job_title", "employer__display_name", "pair__pair_id")
    ordering = ("-created_at",)  
    
    
    fieldsets = (
        ("Pair Info", {"fields": ("pair_id_display", "occupation_display")}),
        ("Links", {"fields": ("employer",)}),
        ("Job Information", {"fields": ("job_title", "job_text")}),
        ("Location & Work Mode", {"fields": ("job_location", "work_mode")}),
        ("Posting Details", {"fields": ("job_link", "job_board", "job_board_other")}),
        # 👇 timestamps deliberately omitted so they won’t appear in the form
    )

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        pair_id = request.GET.get("pair")
        if pair_id:
            initial["pair"] = pair_id
        return initial

    class Media:
        js = ("admin/js/pairapplication.js",)
