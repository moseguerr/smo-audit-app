from django.core.management.base import BaseCommand
import csv
from audit.models import PairApplication, CallbackLog
from pathlib import Path
import pandas as pd

class Command(BaseCommand):
    help = 'Export merged data combining resume_pairs_log with job applications and callback data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--resume_csv', 
            type=str, 
            required=True,
            help='Path to original resume_pairs_log.csv'
        )
        parser.add_argument(
            '--output_path', 
            type=str, 
            default='merged_applications_export.csv',
            help='Output CSV file path'
        )

    def handle(self, *args, **options):
        resume_csv_path = Path(options['resume_csv'])
        output_path = Path(options['output_path'])
        
        if not resume_csv_path.exists():
            self.stdout.write(self.style.ERROR(f'Resume CSV not found: {resume_csv_path}'))
            return
        
        # Read original resume data
        resume_df = pd.read_csv(resume_csv_path)
        
        # Get all applications with related data
        applications = PairApplication.objects.select_related(
            'pair', 'employer'
        ).prefetch_related('pair__profiles', 'callbacks__profile')
        
        # Create list to store merged records
        merged_records = []
        
        for app in applications:
            # Get profiles for this pair
            profiles = list(app.pair.profiles.all())
            
            for profile in profiles:
                # Find matching resume record
                resume_match = resume_df[
                    (resume_df['pair_id'] == app.pair.pair_id) & 
                    (resume_df['full_name'] == profile.full_name)
                ]
                
                if not resume_match.empty:
                    # Start with original resume data
                    merged_record = resume_match.iloc[0].to_dict()
                    
                    # Add job application data (RA-logged information)
                    merged_record.update({
                        'job_title': app.job_title,
                        'job_text': app.job_text,
                        'job_location': app.job_location,
                        'work_mode': app.work_mode,
                        'job_link': app.job_link,
                        'job_board': app.job_board,
                        'job_board_other': app.job_board_other,
                        'days_open': app.days_open,
                        'application_occupation': app.occupation,
                        'application_created': app.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'application_updated': app.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                        
                        # Add employer data (RA-logged employer information)
                        'applied_employer_name': app.employer.display_name,
                        'applied_employer_location': app.employer.employer_location,
                        'applied_employer_industry': app.employer.industry,
                        'applied_employer_employees': app.employer.number_employees,
                        'applied_employer_glassdoor_score': app.employer.glassdoor_score,
                        'applied_employer_diversity_score': app.employer.diversity_score,
                        'applied_employer_openings': app.employer.openings_number,
                        'applied_employer_mission': app.employer.mission_statement,
                    })
                    
                    # Add callback data for this specific profile
                    try:
                        callback_log = app.callbacks.get(profile=profile)
                        callback_data = {
                            'callback_status': callback_log.callback_status,
                            'callback_received': callback_log.callback_status == 'callback',  # Boolean for easier analysis
                            'callback_rejected': callback_log.callback_status == 'rejection',  # Boolean for easier analysis
                            'callback_date': callback_log.callback_date.strftime('%Y-%m-%d') if callback_log.callback_date else '',
                            'callback_medium': callback_log.callback_medium,
                            'callback_notes': callback_log.callback_notes,
                            'callback_created': callback_log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                            'callback_updated': callback_log.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                        }
                    except CallbackLog.DoesNotExist:
                        # No callback log exists for this profile-application combination
                        callback_data = {
                            'callback_status': '',
                            'callback_received': False,
                            'callback_rejected': False,
                            'callback_date': '',
                            'callback_medium': '',
                            'callback_notes': '',
                            'callback_created': '',
                            'callback_updated': '',
                        }
                    
                    # Add callback data to the merged record
                    merged_record.update(callback_data)
                    
                    merged_records.append(merged_record)
        
        if not merged_records:
            self.stdout.write(self.style.WARNING('No matching records found to merge'))
            return
        
        # Convert to DataFrame and export
        merged_df = pd.DataFrame(merged_records)
        merged_df.to_csv(output_path, index=False)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Exported {len(merged_records)} merged records to {output_path}'
            )
        )