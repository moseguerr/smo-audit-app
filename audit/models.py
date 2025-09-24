from django.db import models
import re

class Pair(models.Model):
    pair_id = models.CharField(max_length=50, unique=True, db_index=True)
    occupation = models.CharField(max_length=120)
    good_fit_occupations = models.TextField()   # long descriptive text from CSV

    # Generation tracking (optional, for audit trail)
    location = models.CharField(max_length=10, blank=True)
    archetype = models.IntegerField(blank=True, null=True)
    sublocation = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.pair_id} ({self.occupation})"


class Profile(models.Model):
    pair = models.ForeignKey(Pair, on_delete=models.CASCADE, related_name="profiles")
    full_name = models.CharField(max_length=200, blank=True)  # New field
    phone = models.CharField(max_length=20, blank=True)       # New field
    address = models.CharField(max_length=255, blank=True)    # New field
    email = models.CharField(max_length=100, blank=True)      # New field
    expertise = models.TextField(blank=True)  # Rename from professional skills

    # PDF storage and generation tracking
    resume_pdf = models.FileField(upload_to='resumes/pdfs/', blank=True, null=True)
    template_name = models.CharField(max_length=50, blank=True)
    resume_idx = models.IntegerField(default=1)  # 1 or 2 to track which resume in pair
    
    

def normalize_employer_name(name):
    """
    Normalize employer names for duplicate detection.
    Removes common business suffixes, punctuation, and standardizes formatting.
    """
    if not name:
        return ""
    
    # Convert to lowercase
    normalized = name.lower().strip()
    
    # Remove common punctuation
    normalized = normalized.replace(".", "").replace(",", "")
    
    # Remove common business suffixes (case insensitive)
    suffixes_to_remove = [
        r'\binc\b',           # Inc
        r'\bincorporated\b',  # Incorporated
        r'\bltd\b',           # Ltd
        r'\blimited\b',       # Limited
        r'\bllc\b',           # LLC
        r'\bllp\b',           # LLP
        r'\bcorp\b',          # Corp
        r'\bcorporation\b',   # Corporation
        r'\bco\b',            # Co (only if at end)
        r'\bcompany\b',       # Company
        r'\bthe\b',           # The (if at beginning)
        r'\b&\b',             # & symbol
        r'\band\b',           # and
        r'\bgroup\b',         # Group
        r'\bholdings\b',      # Holdings
        r'\benterprise\b',    # Enterprise
        r'\benterprises\b',   # Enterprises
        r'\bsolutions\b',     # Solutions
        r'\bservices\b',      # Services
        r'\bconsulting\b',    # Consulting
        r'\btechnologies\b',  # Technologies
        r'\btech\b',          # Tech
        r'\bsystems\b',       # Systems
        r'\binternational\b', # International
        r'\bintl\b',          # Intl
        r'\bworldwide\b',     # Worldwide
        r'\bglobal\b',        # Global
    ]
    
    # Remove suffixes
    for suffix in suffixes_to_remove:
        normalized = re.sub(suffix, '', normalized)
    
    # Clean up extra whitespace and special characters
    normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove non-alphanumeric except spaces
    normalized = re.sub(r'\s+', ' ', normalized)     # Replace multiple spaces with single space
    normalized = normalized.strip()
    
    return normalized

class Employer(models.Model):
    display_name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, editable=False, unique=False)

    # RA logging fields
    employer_location = models.CharField(max_length=255, blank=True)
    number_employees = models.PositiveIntegerField(blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True)
    glassdoor_score = models.DecimalField(max_digits=2, decimal_places=1, blank=True, null=True, help_text="Rating out of 5.0")
    diversity_score = models.DecimalField(max_digits=2, decimal_places=1, blank=True, null=True, help_text="Rating out of 5.0")
    openings_number = models.PositiveIntegerField(blank=True, null=True, help_text="Number of current job openings")
    mission_statement= models.TextField()


    def save(self, *args, **kwargs):
        self.normalized_name = normalize_employer_name(self.display_name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.display_name



class PairApplication(models.Model):
    pair = models.ForeignKey(Pair, on_delete=models.PROTECT, related_name="applications")
    employer = models.ForeignKey(Employer, on_delete=models.PROTECT, related_name="applications")

    # occupation visible but controlled in admin
    occupation = models.CharField(max_length=120, editable=False)

    job_title = models.CharField(max_length=255)
    job_text = models.TextField()
    job_location = models.CharField(max_length=255, blank=True)
    days_open=models.PositiveIntegerField(blank=True, help_text="Number of days open", default=0)

    WORK_MODE_CHOICES = [
        ("remote", "Remote"),
        ("hybrid", "Hybrid"),
        ("in_person", "In-person"),
    ]
    work_mode = models.CharField(max_length=20, choices=WORK_MODE_CHOICES, default="in_person")

    job_link = models.URLField(blank=True)
    JOB_BOARD_CHOICES = [
        ("", "Select a job board"),  # Add empty default option
        ("indeed", "Indeed"),
        ("glassdoor", "Glassdoor"),
        ("ziprecruiter", "ZipRecruiter"),
        ("other", "Other"),
    ]
    job_board = models.CharField(max_length=50, choices=JOB_BOARD_CHOICES, blank="True")
    job_board_other = models.CharField(max_length=255, blank=True)

    # Application workflow status
    STATUS_CHOICES = [
        ("draft", "Work in Progress"),
        ("submitted", "Submitted"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    submitted_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["occupation", "employer"], name="unique_occupation_employer_application")
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pair.pair_id} → {self.occupation} | {self.job_title} @ {self.employer} ({self.get_status_display()})"

# In audit/models.py
class CallbackLog(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="callbacks")
    application = models.ForeignKey(PairApplication, on_delete=models.CASCADE, related_name="callbacks")
    
    CALLBACK_STATUS_CHOICES = [
        ('no_info', 'No Info'),
        ('callback', 'Callback Received'),
        ('rejection', 'Rejection'),
    ]
    callback_status = models.CharField(max_length=20, choices=CALLBACK_STATUS_CHOICES, default='no_info')
    callback_date = models.DateField(blank=True, null=True)
    
    CALLBACK_MEDIUM_CHOICES = [
        ('phone', 'Phone call'),
        ('personalized_email', 'Personalized email'),
        ('standardized_email', 'Standardized/automated email'),
        ('text', 'Text message'),
        ('other', 'Other'),
    ]
    callback_medium = models.CharField(max_length=20, choices=CALLBACK_MEDIUM_CHOICES, blank=True)
    callback_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['profile', 'application']
    
    def __str__(self):
        return f"{self.profile.full_name} - {self.application.employer.display_name} ({self.get_callback_status_display()})"