# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from Parole import settings
from .models import *
from .serializers import *
from .utils import GeofenceChecker, AlertManager
import json
import logging
from geopy.distance import geodesic

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class LocationUpdateView(APIView):
    """API endpoint to receive location updates from tracking devices"""
    authentication_classes = []  # Disable authentication
    permission_classes = []      # Disable permission checks
    
    def post(self, request):
        try:
            logger.info(f"Received location update request from IP: {request.META.get('REMOTE_ADDR')}")
            logger.info(f"Raw request data: {request.body}")
            logger.info(f"Parsed request data: {request.data}")
            
            serializer = LocationUpdateSerializer(data=request.data)
            if serializer.is_valid():
                data = serializer.validated_data
                logger.info(f"Validated data: {data}")
                
                # Check for zero coordinates
                if float(data['latitude']) == 0 and float(data['longitude']) == 0:
                    logger.warning(f"Received zero coordinates for device {data['device_id']}")
                    return Response({
                        'status': 'warning',
                        'message': 'Received zero coordinates. GPS might not be ready.',
                        'device_id': data['device_id']
                    }, status=status.HTTP_200_OK)
                
                # Get or create tracking device
                try:
                    device = TrackingDevice.objects.get(device_id=data['device_id'])
                    logger.info(f"Found device: {device.device_id} for inmate: {device.inmate}")
                except TrackingDevice.DoesNotExist:
                    logger.error(f"Device {data['device_id']} not found in database")
                    return Response({
                        'error': f"Device {data['device_id']} not found. Please register device first."
                    }, status=status.HTTP_404_NOT_FOUND)
                
                # Update device status
                device.battery_level = data['battery_level']
                device.last_ping = timezone.now()
                
                # Check battery level and update device status
                if data['battery_level'] < 20:
                    device.status = 'low_battery'
                    AlertManager.create_low_battery_alert(device)
                elif device.status == 'low_battery' and data['battery_level'] > 25:
                    device.status = 'active'
                
                device.save()
                logger.info(f"Updated device status: {device.status}, battery: {device.battery_level}%")
                
                # Update or create current location
                try:
                    current_location, created = CurrentLocation.objects.update_or_create(
                        device=device,
                        defaults={
                            'latitude': data['latitude'],
                            'longitude': data['longitude'],
                            'altitude': data['altitude'],
                            'speed': data['speed'],
                            'satellites': data['satellites'],
                            'accuracy': data['accuracy'],
                            'timestamp': data['timestamp']
                        }
                    )
                    logger.info(f"{'Created' if created else 'Updated'} location for device {device.device_id}: lat={data['latitude']}, lng={data['longitude']}")
                except Exception as e:
                    logger.error(f"Error updating location: {str(e)}")
                    raise
                
                # Save to history
                should_save_history = self.should_save_to_history(device, data)
                if should_save_history:
                    try:
                        LocationHistory.objects.create(
                            device=device,
                            latitude=data['latitude'],
                            longitude=data['longitude'],
                            altitude=data['altitude'],
                            speed=data['speed'],
                            satellites=data['satellites'],
                            accuracy=data['accuracy'],
                            timestamp=data['timestamp']
                        )
                        logger.info(f"Saved location to history for device {device.device_id}")
                    except Exception as e:
                        logger.error(f"Error saving to history: {str(e)}")
                
                # Check geofence violations
                GeofenceChecker.check_violations(device, data['latitude'], data['longitude'])
                
                # Check speed violations
                if data['speed'] > 120:  # Speed limit in km/h
                    AlertManager.create_speed_violation_alert(device, data['speed'])
                
                return Response({
                    'status': 'success',
                    'message': 'Location updated successfully',
                    'device_id': data['device_id'],
                    'timestamp': timezone.now()
                }, status=status.HTTP_200_OK)
            
            logger.error(f"Invalid data received: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f"Error updating location: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def should_save_to_history(self, device, new_data):
        """Determine if location should be saved to history"""
        # Always save first location
        last_history = LocationHistory.objects.filter(device=device).first()
        if not last_history:
            return True
        
        # Save every 5 minutes
        time_diff = timezone.now() - last_history.created_at
        if time_diff.total_seconds() > 300:  # 5 minutes
            return True
        
        # Save if significant movement (>50 meters)
        old_point = (float(last_history.latitude), float(last_history.longitude))
        new_point = (float(new_data['latitude']), float(new_data['longitude']))
        distance = geodesic(old_point, new_point).meters
        
        return distance > 50

class CurrentLocationListView(generics.ListAPIView):
    """Get current locations of all active devices"""
    queryset = CurrentLocation.objects.select_related('device__inmate')
    serializer_class = CurrentLocationSerializer

class AlertListView(generics.ListAPIView):
    """Get list of alerts with filtering"""
    serializer_class = AlertSerializer
    
    def get_queryset(self):
        queryset = Alert.objects.select_related('inmate', 'device')
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by alert type
        alert_type = self.request.query_params.get('type', None)
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        
        # Filter by inmate
        inmate_id = self.request.query_params.get('inmate', None)
        if inmate_id:
            queryset = queryset.filter(inmate_id=inmate_id)
        
        return queryset

@login_required
def dashboard_view(request):
    """Main dashboard view"""
    active_inmates = Inmate.objects.filter(parole_status='active').count()
    active_alerts = Alert.objects.filter(status__in=['new', 'acknowledged']).count()
    low_battery_devices = TrackingDevice.objects.filter(battery_level__lt=20).count()
    
    context = {
        'active_inmates': active_inmates,
        'active_alerts': active_alerts,
        'low_battery_devices': low_battery_devices,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
    }
    return render(request, 'tracking/dashboard.html', context)

@login_required
def real_time_map_view(request):
    """Real-time map view"""
    context = {
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
    }
    return render(request, 'tracking/real_time_map.html', context)

def get_map_data(request):
    """API endpoint for map data"""
    locations = CurrentLocation.objects.select_related('device__inmate').all()
    alerts = Alert.objects.filter(status__in=['new', 'acknowledged']).select_related('inmate')
    
    location_data = []
    for loc in locations:
        location_data.append({
            'device_id': loc.device.device_id,
            'inmate_name': f"{loc.device.inmate.first_name} {loc.device.inmate.last_name}",
            'latitude': float(loc.latitude),
            'longitude': float(loc.longitude),
            'battery_level': loc.device.battery_level,
            'last_update': loc.updated_at.isoformat(),
            'status': loc.device.status
        })
    
    alert_data = []
    for alert in alerts:
        if alert.location_latitude and alert.location_longitude:
            alert_data.append({
                'id': str(alert.alert_id),
                'type': alert.alert_type,
                'severity': alert.severity,
                'latitude': float(alert.location_latitude),
                'longitude': float(alert.location_longitude),
                'inmate_name': f"{alert.inmate.first_name} {alert.inmate.last_name}",
                'description': alert.description,
                'created_at': alert.created_at.isoformat()
            })
    
    return JsonResponse({
        'locations': location_data,
        'alerts': alert_data
    })
