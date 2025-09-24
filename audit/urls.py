from django.urls import path
from . import views

urlpatterns = [
    path('ajax/sublocations/', views.get_sublocations, name='ajax_sublocations'),
    path('ajax/archetypes/', views.get_archetypes, name='ajax_archetypes'),
]
