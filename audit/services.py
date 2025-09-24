"""
Resume generation service for Django audit app.

Integrates with resume_randomization.py to generate pairs on-demand
and store them in Django models with PDF files.
"""

import sys
import os
import asyncio
from pathlib import Path
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from .models import Pair, Profile

# Add the resume_randomization module to the path
RESUME_RANDOMIZATION_PATH = Path(__file__).parent.parent.parent / "experiment-design" / "cv-generator" / "code"
sys.path.insert(0, str(RESUME_RANDOMIZATION_PATH))

try:
    from resume_randomization import generate_pair, generate_render_and_log_pair_async, build_template_context, _env, _load_data_once, _locations
    RESUME_GENERATION_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import resume_randomization: {e}")
    RESUME_GENERATION_AVAILABLE = False


def get_available_locations():
    """Get list of available locations - hardcoded valid identifiers."""
    # Hardcoded list of valid location identifiers that work with generate_render_and_log_pair
    return ["GA", "NY", "MA", "IL", "CO", "FLO", "LA", "MI", "PA", "SFO", "TX", "WA", "DMV"]


# Hardcoded sublocation data for reliable dropdown functionality
HARDCODED_SUBLOCATIONS = {
    # Locations with NO sublocations
    'GA': [],

    # Locations with SINGLE sublocation (no dropdown needed)
    'NY': [(1, 'New York-Newark-Jersey City, NY-NJ-PA')],
    'MA': [(1, 'Boston-Cambridge-Newton, MA-NH Metro Area')],
    'IL': [(1, 'Chicago-Naperville-Elgin, IL-IN Metro Area')],
    'FLO': [(1, 'Miami-Fort Lauderdale-Pompano Beach, FL')],
    'LA': [(1, 'Los Angeles-Long Beach-Anaheim, CA')],
    'MI': [(1, 'Detroit-Warren-Dearborn, MI Metro Area')],
    'SFO': [(1, 'San Francisco-Oakland-Fremont, CA Metro Area')],
    'WA': [(1, 'Seattle-Tacoma-Bellevue, WA Metro Area')],
    'DMV': [(1, 'Washington-Arlington-Alexandria, DC-VA-MD-WV Metro Area')],

    # Locations with MULTIPLE sublocations (dropdown needed)
    'CO': [(1, 'Boulder, CO Metro Area'), (2, 'Glenwood Springs CCD, Garfield County, Colorado')],
    'PA': [(1, 'Harrisburg-Carlisle, PA Metro Area'), (2, 'Philadelphia-Camden-Wilmington, PA-NJ-DE-MD Metro Area'), (3, 'Pittsburgh, PA Metro Area')],
    'TX': [(1, 'Austin-Round Rock-Georgetown, TX'), (2, 'Dallas-Fort Worth-Arlington, TX Metro Area'), (3, 'Houston-The Woodlands-Sugar Land, TX')]
}

# Accurate archetype mappings that match the resume generation system
ARCHETYPE_MAPPINGS = {
    'communications': [
        ('digital_communications_specialist', 'Digital Communications Specialist'),
        ('strategic_internal_communications', 'Strategic Internal Communication'),
        ('public_relations_specialist', 'Public Relations Specialist'),
        ('brand_content_marketing', 'Brand Content Marketing')
    ],
    'payroll': [
        ('payroll_systems_specialist', 'Payroll Systems Specialist'),
        ('payroll_compliance_manager', 'Payroll Compliance Manager'),
        ('hr_payroll_generalist', 'HR Payroll Generalist')
    ],
    'project_manager': [
        ('environmental_project_manager', 'Environmental Project Manager'),
        ('energy_program_manager', 'Energy Program Manager')
    ]
}

# Legacy mapping for backward compatibility - maps archetype strings to numeric indices
ARCHETYPE_STRING_TO_INDEX = {
    'communications': {
        'digital_communications_specialist': 1,
        'strategic_internal_communications': 2,
        'public_relations_specialist': 3,
        'brand_content_marketing': 4
    },
    'payroll': {
        'payroll_systems_specialist': 1,
        'payroll_compliance_manager': 2,
        'hr_payroll_generalist': 3
    },
    'project_manager': {
        'environmental_project_manager': 1,
        'energy_program_manager': 2
    }
}

def get_available_sublocations(location):
    """Get list of available sublocations (census areas) for a given location."""
    return HARDCODED_SUBLOCATIONS.get(location, [])

def get_available_archetypes(occupation):
    """Get list of available archetypes with descriptive names for a given occupation."""
    return ARCHETYPE_MAPPINGS.get(occupation, [])

def get_archetype_index(occupation, archetype_string):
    """Convert archetype string to numeric index for the resume generation system."""
    return ARCHETYPE_STRING_TO_INDEX.get(occupation, {}).get(archetype_string, 1)

def get_archetype_display_name(occupation, archetype_string):
    """Get the display name for an archetype string."""
    mappings = ARCHETYPE_MAPPINGS.get(occupation, [])
    for arch_str, display_name in mappings:
        if arch_str == archetype_string:
            return display_name
    return archetype_string.replace('_', ' ').title()


def get_available_occupations():
    """Get list of available occupations - hardcoded valid options."""
    # Hardcoded list of valid occupations that work with generate_render_and_log_pair
    return [
        ("communications", "Communications"),
        ("payroll", "Payroll"),
        ("project_manager", "Project Manager")
    ]




async def generate_and_store_pair_async(location, occupation, archetype, sublocation=None):
    """
    Generate a resume pair and store it in Django models with PDF files.

    Args:
        location (str): Location code (e.g., "GA", "NY")
        occupation (str): Occupation type ("communications", "payroll", "project_manager")
        archetype (int): Archetype number (1-4)
        sublocation (int, optional): Sublocation index (1-based)

    Returns:
        Pair: Created Pair instance with associated Profile records
    """
    if not RESUME_GENERATION_AVAILABLE:
        raise Exception("Resume generation not available - could not import resume_randomization")

    # Generate the pair data
    pair_data = generate_pair(occupation, location, archetype, sublocation)

    # Create Pair record
    pair = Pair.objects.create(
        pair_id=pair_data["pair_id"],
        occupation=occupation,
        good_fit_occupations=", ".join(pair_data["good_fit_occupations"]),
        location=location,
        archetype=archetype,
        sublocation=sublocation
    )

    # Generate and store both profiles with PDFs
    for resume_key, resume_idx in [("resume1", 1), ("resume2", 2)]:
        resume_data = pair_data[resume_key]

        # Create Profile record
        profile = Profile.objects.create(
            pair=pair,
            full_name=resume_data["full_name"],
            phone=resume_data["phone"],
            address=resume_data["address"],
            email=resume_data["email"],
            expertise=resume_data["skills"],  # Map skills to expertise
            template_name=resume_data["template_name"],
            resume_idx=resume_idx
        )

        # Generate PDF using enhanced resume_randomization
        try:
            # Build template context
            from resume_randomization import build_template_context, _env, TEMPLATE_DIR
            from pyppeteer import launch

            ctx = build_template_context(resume_data)
            template = _env.get_template(resume_data["template_name"])
            html_content = template.render(**ctx)

            # Generate PDF using Pyppeteer
            browser = await launch(headless=True, args=['--no-sandbox'])
            page = await browser.newPage()

            # Create temp HTML file
            temp_html = TEMPLATE_DIR / f"temp_{profile.full_name.replace(' ', '_')}_{pair.pair_id}.html"
            with open(temp_html, 'w', encoding='utf-8') as f:
                f.write(html_content)

            await page.goto(f"file://{temp_html}", {'waitUntil': 'networkidle0'})

            # Generate PDF content
            pdf_content = await page.pdf({
                'printBackground': True,
                'format': 'Letter',
                'margin': {'top': '0.75in', 'right': '0.75in', 'bottom': '0.75in', 'left': '0.75in'}
            })

            # Save PDF to model
            pdf_filename = f"{profile.full_name.replace(' ', '_')}_{pair.pair_id}.pdf"
            profile.resume_pdf.save(
                pdf_filename,
                ContentFile(pdf_content),
                save=True
            )

            # Cleanup
            temp_html.unlink()
            await page.close()
            await browser.close()

        except Exception as e:
            print(f"Error generating PDF for {profile.full_name}: {e}")
            # Continue without PDF if generation fails

    return pair


def generate_and_store_pair(location, occupation, archetype, sublocation=None):
    """
    Synchronous wrapper for generate_and_store_pair_async.
    """
    return asyncio.run(generate_and_store_pair_async(location, occupation, archetype, sublocation))