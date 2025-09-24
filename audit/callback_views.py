# callback_views.py
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.http import JsonResponse
from .models import PairApplication

@staff_member_required
def callback_search(request):
    search_results = []
    search_query = request.GET.get('q', '').strip()
    debug_info = {}
    
    if search_query:
        # Debug: Show what we're searching for
        debug_info['search_query'] = search_query
        
        # Get applications that match search criteria
        applications = PairApplication.objects.select_related(
            'pair', 'employer'
        ).prefetch_related('pair__profiles').filter(
            Q(employer__display_name__icontains=search_query) |
            Q(pair__profiles__full_name__icontains=search_query) |
            Q(pair__profiles__email__icontains=search_query) |
            Q(pair__profiles__phone__icontains=search_query)
        ).distinct()
        
        debug_info['total_applications_found'] = applications.count()
        debug_info['application_ids'] = [app.id for app in applications]
        
        # Create merged records for search results
        for app in applications:
            profiles = list(app.pair.profiles.all())
            debug_info[f'app_{app.id}_profiles'] = [p.full_name for p in profiles]
            
            for profile in profiles:
                # Create merged record
                merged_record = {
                    'application_id': app.id,  # This should exist
                    'pair_id': app.pair.pair_id,
                    'full_name': profile.full_name,
                    'email': profile.email,
                    'phone': profile.phone,
                    'address': profile.address,
                    'job_title': app.job_title,
                    'employer_name': app.employer.display_name,
                    'employer_location': app.employer.employer_location,
                    'application_date': app.created_at.date() if app.created_at else None,
                    
                    # Callback data (these might be None if fields don't exist yet)
                    'callback_received': getattr(app, 'callback_received', False),
                    'callback_date': getattr(app, 'callback_date', None),
                    'callback_medium': getattr(app, 'callback_medium', ''),
                    'callback_notes': getattr(app, 'callback_notes', ''),
                }
                search_results.append(merged_record)
    
    return render(request, 'admin/callback_search.html', {
        'search_results': search_results,
        'search_query': search_query,
        'debug_info': debug_info,  # Pass debug info to template
        'title': 'Callback Search & Logging',
        'opts': {'app_label': 'audit', 'verbose_name': 'Callback Search'}
    })


@staff_member_required
def update_callback(request, application_id):
    """Handle AJAX requests to update callback status"""
    if request.method == 'POST':
        try:
            app = PairApplication.objects.get(id=application_id)
            
            # Update callback fields
            app.callback_received = request.POST.get('callback_received') == 'on'  # checkbox sends 'on' when checked
            
            callback_date = request.POST.get('callback_date')
            if callback_date:
                app.callback_date = callback_date
            else:
                app.callback_date = None
                
            app.callback_medium = request.POST.get('callback_medium', '')
            app.callback_notes = request.POST.get('callback_notes', '')
            
            app.save()
            
            return JsonResponse({'success': True, 'message': 'Callback status updated'})
            
        except PairApplication.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Application not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})