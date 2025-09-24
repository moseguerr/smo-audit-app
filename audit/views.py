from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.urls import reverse
from .services import get_available_sublocations, get_available_archetypes


def get_sublocations(request):
    """AJAX endpoint to get available sublocations for a given location."""
    location = request.GET.get('location')
    print(f"get_sublocations called with location: {location}")

    if not location:
        print("No location provided, returning empty list")
        return JsonResponse({'sublocations': []})

    try:
        sublocations = get_available_sublocations(location)
        print(f"get_available_sublocations returned: {sublocations}")

        # Convert to format expected by frontend
        sublocation_choices = [{'value': str(idx), 'label': name}
                              for idx, name in sublocations]

        print(f"Returning sublocation_choices: {sublocation_choices}")
        return JsonResponse({'sublocations': sublocation_choices})
    except Exception as e:
        print(f"Exception in get_sublocations: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


def get_archetypes(request):
    """AJAX endpoint to get available archetypes for a given occupation."""
    occupation = request.GET.get('occupation')
    print(f"get_archetypes called with occupation: {occupation}")

    if not occupation:
        print("No occupation provided, returning empty list")
        return JsonResponse({'archetypes': []})

    try:
        archetypes = get_available_archetypes(occupation)
        print(f"get_available_archetypes returned: {archetypes}")

        # Convert to format expected by frontend
        archetype_choices = [{'value': archetype_string, 'label': display_name}
                           for archetype_string, display_name in archetypes]

        print(f"Returning archetype_choices: {archetype_choices}")
        return JsonResponse({'archetypes': archetype_choices})
    except Exception as e:
        print(f"Exception in get_archetypes: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

