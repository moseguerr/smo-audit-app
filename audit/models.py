from django.db import models


class Pair(models.Model):
    pair_id = models.CharField(max_length=50, unique=True, db_index=True)
    occupation = models.CharField(max_length=120)
    good_fit_occupations = models.TextField()   # long descriptive text from CSV

    def __str__(self):
        return f"{self.pair_id} ({self.occupation})"


class Profile(models.Model):
    pair = models.ForeignKey(Pair, on_delete=models.CASCADE, related_name="profiles")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    expertise = models.TextField(blank=True)   # from "professional skills and expertise"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Employer(models.Model):
    display_name = models.CharField(max_length=255, unique=True)
    normalized_name = models.CharField(max_length=255, editable=False, unique=True)

    # RA logging fields
    employer_location = models.CharField(max_length=255, blank=True)
    number_employees = models.PositiveIntegerField(blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True)

    def save(self, *args, **kwargs):
        self.normalized_name = (
            self.display_name.lower().replace(".", "").replace(",", "").strip()
        )
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

    WORK_MODE_CHOICES = [
        ("remote", "Remote"),
        ("hybrid", "Hybrid"),
        ("in_person", "In-person"),
    ]
    work_mode = models.CharField(max_length=20, choices=WORK_MODE_CHOICES, default="in_person")

    job_link = models.URLField(blank=True)
    JOB_BOARD_CHOICES = [
        ("indeed", "Indeed"),
        ("glassdoor", "Glassdoor"),
        ("ziprecruiter", "ZipRecruiter"),
        ("other", "Other"),
    ]
    job_board = models.CharField(max_length=50, choices=JOB_BOARD_CHOICES, default="other")
    job_board_other = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["occupation", "employer"], name="unique_occupation_employer_application")
        ]

    def save(self, *args, **kwargs):
        if self.pair:
            occ = self.pair.occupation.strip()
            # normalize → first letter uppercase, rest lowercase
            self.occupation = occ.capitalize()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.pair.pair_id} → {self.occupation} | {self.job_title} @ {self.employer}"

