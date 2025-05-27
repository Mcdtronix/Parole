from Tracking.models import Alert, GeofenceZone
from geopy.distance import geodesic
from django.utils import timezone
from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)

class GeofenceChecker:
    @staticmethod
    def check_violations(device, latitude, longitude):
        """Check if current location violates any geofence rules"""
        inmate = device.inmate
        current_point = (float(latitude), float(longitude))
        current_time = timezone.now().time()
        current_day = timezone.now().weekday() + 1  # 1=Monday, 7=Sunday
        
        geofence_zones = GeofenceZone.objects.filter(
            inmate=inmate,
            is_active=True
        )
        
        for zone in geofence_zones:
            zone_center = (float(zone.center_latitude), float(zone.center_longitude))
            distance = geodesic(current_point, zone_center).meters
            
            # Check if within radius
            is_inside_zone = distance <= zone.radius_meters
            
            # Check time restrictions
            time_allowed = GeofenceChecker.is_time_allowed(zone, current_time, current_day)
            
            if zone.zone_type == 'allowed' and not is_inside_zone and time_allowed:
                # Outside allowed zone during allowed time
                AlertManager.create_geofence_violation_alert(
                    device, zone, latitude, longitude, 
                    f"Outside allowed zone '{zone.name}'"
                )
            elif zone.zone_type == 'restricted' and is_inside_zone:
                # Inside restricted zone
                AlertManager.create_geofence_violation_alert(
                    device, zone, latitude, longitude, 
                    f"Inside restricted zone '{zone.name}'"
                )
            elif zone.zone_type == 'home' and not is_inside_zone:
                # Check if it's curfew time
                if GeofenceChecker.is_curfew_time(current_time):
                    AlertManager.create_curfew_violation_alert(
                        device, latitude, longitude, 
                        f"Outside home zone during curfew hours"
                    )
    
    @staticmethod
    def is_time_allowed(zone, current_time, current_day):
        """Check if current time is within allowed time for the zone"""
        if not zone.start_time or not zone.end_time:
            return True
        
        # Check day of week
        if str(current_day) not in zone.days_of_week:
            return False
        
        # Check time range
        if zone.start_time <= zone.end_time:
            # Same day range
            return zone.start_time <= current_time <= zone.end_time
        else:
            # Overnight range
            return current_time >= zone.start_time or current_time <= zone.end_time
    
    @staticmethod
    def is_curfew_time(current_time):
        """Check if current time is during curfew hours (example: 10 PM - 6 AM)"""
        curfew_start = time(22, 0)  # 10 PM
        curfew_end = time(6, 0)     # 6 AM
        
        return current_time >= curfew_start or current_time <= curfew_end

class AlertManager:
    @staticmethod
    def create_geofence_violation_alert(device, zone, latitude, longitude, description):
        """Create a geofence violation alert"""
        alert = Alert.objects.create(
            inmate=device.inmate,
            device=device,
            alert_type='geofence_violation',
            severity='high',
            title=f"Geofence Violation - {zone.name}",
            description=description,
            location_latitude=latitude,
            location_longitude=longitude
        )
        
        NotificationManager.send_alert_notifications(alert)
        return alert
    
    @staticmethod
    def create_low_battery_alert(device):
        """Create a low battery alert"""
        # Check if there's already a recent low battery alert
        recent_alert = Alert.objects.filter(
            device=device,
            alert_type='low_battery',
            status__in=['new', 'acknowledged'],
            created_at__gte=timezone.now() - timezone.timedelta(hours=2)
        ).first()
        
        if not recent_alert:
            alert = Alert.objects.create(
                inmate=device.inmate,
                device=device,
                alert_type='low_battery',
                severity='medium',
                title="Device Low Battery",
                description=f"Device battery level is {device.battery_level}%"
            )
            
            NotificationManager.send_alert_notifications(alert)
            return alert
    
    @staticmethod
    def create_speed_violation_alert(device, speed):
        """Create a speed violation alert"""
        alert = Alert.objects.create(
            inmate=device.inmate,
            device=device,
            alert_type='speed_violation',
            severity='medium',
            title="Speed Violation",
            description=f"Speed exceeded limit: {speed} km/h"
        )
        
        NotificationManager.send_alert_notifications(alert)
        return alert
    
    @staticmethod
    def create_curfew_violation_alert(device, latitude, longitude, description):
        """Create a curfew violation alert"""
        alert = Alert.objects.create(
            inmate=device.inmate,
            device=device,
            alert_type='curfew_violation',
            severity='high',
            title="Curfew Violation",
            description=description,
            location_latitude=latitude,
            location_longitude=longitude
        )
        
        NotificationManager.send_alert_notifications(alert)
        return alert

class NotificationManager:
    @staticmethod
    def send_alert_notifications(alert):
        """Send notifications for an alert"""
        try:
            officer = alert.inmate.assigned_officer
            if not officer:
                return
            
            settings = NotificationSettings.objects.filter(officer=officer).first()
            if not settings:
                return
            
            # Get notification preferences for this alert type
            notification_types = []
            if alert.alert_type == 'geofence_violation':
                notification_types = settings.geofence_violations
            elif alert.alert_type == 'device_tamper':
                notification_types = settings.device_tampering
            elif alert.alert_type == 'low_battery':
                notification_types = settings.low_battery
            elif alert.alert_type == 'device_offline':
                notification_types = settings.device_offline
            elif alert.alert_type == 'emergency':
                notification_types = settings.emergency_alerts
            
            # Send notifications based on preferences
            for notification_type in notification_types:
                if notification_type == 'email':
                    NotificationManager.send_email_notification(officer, alert)
                elif notification_type == 'sms':
                    NotificationManager.send_sms_notification(officer, alert)
                # Add other notification types as needed
                    
        except Exception as e:
            logger.error(f"Error sending notifications: {str(e)}")
    
    @staticmethod
    def send_email_notification(officer, alert):
        """Send email notification"""
        # Implement email sending logic here
        pass
    
    @staticmethod
    def send_sms_notification(officer, alert):
        """Send SMS notification"""
        # Implement SMS sending logic here
        pass
