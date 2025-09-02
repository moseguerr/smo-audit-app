import pandas as pd
from django.core.management.base import BaseCommand
from audit.models import Pair, Profile


class Command(BaseCommand):
    help = "Import pairs and profiles from an Excel (.xlsx) file"

    def add_arguments(self, parser):
        parser.add_argument("xlsx_path", type=str, help="Path to pairs.xlsx")

    def handle(self, *args, **options):
        xlsx_path = options["xlsx_path"]
        self.stdout.write(self.style.NOTICE(f"Reading {xlsx_path}..."))

        # Load Excel
        df = pd.read_excel(xlsx_path)

        required_cols = [
            "pair_id",
            "first_name",
            "last_name",
            "occupation",
            "good fit occupations",
            "professional skills and expertise",
        ]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        for _, row in df.iterrows():
            pair_id = str(row["pair_id"]).strip()
            occupation = str(row["occupation"]).strip()
            good_fit = str(row["good fit occupations"]).strip()
            first_name = str(row["first_name"]).strip()
            last_name = str(row["last_name"]).strip()
            expertise = str(row["professional skills and expertise"]).strip()

            # --- Pair ---
            pair, created = Pair.objects.get_or_create(
                pair_id=pair_id,
                defaults={
                    "occupation": occupation,
                    "good_fit_occupations": good_fit,
                },
            )
            if not created:
                # update if changed
                if pair.occupation != occupation or pair.good_fit_occupations != good_fit:
                    pair.occupation = occupation
                    pair.good_fit_occupations = good_fit
                    pair.save()

            # --- Profile ---
            profile, created = Profile.objects.get_or_create(
                pair=pair,
                first_name=first_name,
                last_name=last_name,
                defaults={"expertise": expertise},
            )
            if not created and profile.expertise != expertise:
                profile.expertise = expertise
                profile.save()

            self.stdout.write(f"Imported {pair_id}: {first_name} {last_name}")

        self.stdout.write(self.style.SUCCESS("Excel import finished"))
