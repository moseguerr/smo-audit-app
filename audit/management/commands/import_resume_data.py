from django.core.management.base import BaseCommand
import csv
from audit.models import Pair, Profile
from pathlib import Path

class Command(BaseCommand):
    help = 'Import resume data from CSV into Profile models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv_path', 
            type=str, 
            default='resume_pairs_log.csv',
            help='Path to resume_pairs_log.csv (default: resume_pairs_log.csv)'
        )

    def handle(self, *args, **options):
        csv_path = Path(options['csv_path'])
        
        if not csv_path.exists():
            self.stdout.write(
                self.style.ERROR(f'CSV file not found: {csv_path}')
            )
            return
        
        # Group by pair_id first
        pairs_data = {}
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                pair_id = row['pair_id']
                if pair_id not in pairs_data:
                    pairs_data[pair_id] = []
                pairs_data[pair_id].append(row)
        
        # Process each pair
        for pair_id, rows in pairs_data.items():
            pair, created = Pair.objects.get_or_create(
                pair_id=pair_id,
                defaults={
                    'occupation': rows[0].get('occupation', 'Unknown'),
                    'good_fit_occupations': rows[0].get('good_fit_occupations', '')
                }
            )
            
            for row in rows:
                Profile.objects.update_or_create(
                    pair=pair,
                    full_name=row['full_name'],  # Use full_name directly from CSV
                    defaults={
                        'phone': row['phone'],
                        'address': row['address'],
                        'email': row.get('email', ''),
                        'expertise': row['skills'],
                    }
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'Updated {row["full_name"]} for pair {pair_id}')
                )