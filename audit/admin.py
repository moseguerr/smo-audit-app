from django.contrib import admin
from .models import Pair, Profile, Employer, PairApplication


class ProfileInline(admin.TabularInline):
    model = Profile
    extra = 0
    can_delete = False
    readonly_fields = ("first_name", "last_name", "expertise")
    show_change_link = False
    max_num = 0


class PairApplicationInline(admin.StackedInline):
    model = PairApplication
    extra = 0

    fieldsets = (
        ("Employer", {
            "fields": ("employer",)
        }),
        ("Job Information", {
            "fields": ("occupation", "job_title", "job_text")
        }),
        ("Location & Work Mode", {
            "fields": ("job_location", "work_mode")
        }),
        ("Posting Details", {
            "fields": ("job_link", "job_board", "job_board_other")
        }),
    )


@admin.register(Pair)
class PairAdmin(admin.ModelAdmin):
    list_display = ("pair_id", "occupation")
    search_fields = ("pair_id", "occupation")
    readonly_fields = ("pair_id", "occupation", "good_fit_occupations")
    inlines = [ProfileInline, PairApplicationInline]
    change_form_template = "admin/read_only_change_form.html"

    def has_add_permission(self, request):
        return False  # no new Pairs in admin

    def has_delete_permission(self, request, obj=None):
        return False  # no deleting Pairs

    def has_change_permission(self, request, obj=None):
        return True  # allow RAs to add applications


@admin.register(Employer)
class EmployerAdmin(admin.ModelAdmin):
    list_display = ("display_name", "normalized_name")
    search_fields = ("display_name", "normalized_name")


@admin.register(PairApplication)
class PairApplicationAdmin(admin.ModelAdmin):
    list_display = ("pair", "employer", "job_title", "work_mode", "job_board")
    search_fields = (
        "pair__pair_id",
        "employer__display_name",
        "job_title",
        "job_location",
    )
    list_filter = ("work_mode", "job_board")
