# urls.py
from django.urls import path, include
from . import views

urlpatterns = [
    # API endpoints
    path('api/location/', views.LocationUpdateView.as_view(), name='location_update'),
    path('api/locations/', views.CurrentLocationListView.as_view(), name='current_locations'),
    path('api/alerts/', views.AlertListView.as_view(), name='alerts'),
    path('api/map-data/', views.get_map_data, name='map_data'),
    
    # Web views
    path('', views.dashboard_view, name='dashboard'),
    path('map/', views.real_time_map_view, name='real_time_map'),
]
