# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class ParoleOfficer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    badge_number = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=15)
    email = models.EmailField()
    department = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.badge_number}"

class Inmate(models.Model):
    PAROLE_STATUS_CHOICES = [
        ('active', 'Active Parole'),
        ('violated', 'Parole Violated'),
        ('completed', 'Parole Completed'),
        ('suspended', 'Parole Suspended')
    ]
    
    inmate_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField()
    parole_start_date = models.DateField()
    parole_end_date = models.DateField()
    parole_status = models.CharField(max_length=20, choices=PAROLE_STATUS_CHOICES, default='active')
    assigned_officer = models.ForeignKey(ParoleOfficer, on_delete=models.SET_NULL, null=True)
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=15)
    home_address = models.TextField()
    photo = models.ImageField(upload_to='inmate_photos/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.inmate_id})"

class TrackingDevice(models.Model):
    DEVICE_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Under Maintenance'),
        ('tampered', 'Tampered'),
        ('low_battery', 'Low Battery')
    ]
    
    device_id = models.CharField(max_length=50, unique=True)
    inmate = models.OneToOneField(Inmate, on_delete=models.CASCADE, related_name='tracking_device')
    status = models.CharField(max_length=20, choices=DEVICE_STATUS_CHOICES, default='active')
    battery_level = models.FloatField(default=100.0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    last_ping = models.DateTimeField(null=True, blank=True)
    firmware_version = models.CharField(max_length=20, default='1.0.0')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Device {self.device_id} - {self.inmate}"

class CurrentLocation(models.Model):
    """Stores only the latest location for each device - updates in place"""
    device = models.OneToOneField(TrackingDevice, on_delete=models.CASCADE, related_name='current_location')
    latitude = models.DecimalField(max_digits=10, decimal_places=6)
    longitude = models.DecimalField(max_digits=10, decimal_places=6)
    altitude = models.FloatField(default=0.0)
    speed = models.FloatField(default=0.0)  # km/h
    satellites = models.IntegerField(default=0)
    accuracy = models.FloatField(default=0.0)  # meters
    timestamp = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.device.device_id} - Latest Location"

class LocationHistory(models.Model):
    """Stores historical location data for reporting and analysis"""
    device = models.ForeignKey(TrackingDevice, on_delete=models.CASCADE, related_name='location_history')
    latitude = models.DecimalField(max_digits=10, decimal_places=6)
    longitude = models.DecimalField(max_digits=10, decimal_places=6)
    altitude = models.FloatField(default=0.0)
    speed = models.FloatField(default=0.0)
    satellites = models.IntegerField(default=0)
    accuracy = models.FloatField(default=0.0)
    timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

class GeofenceZone(models.Model):
    ZONE_TYPE_CHOICES = [
        ('allowed', 'Allowed Zone'),
        ('restricted', 'Restricted Zone'),
        ('home', 'Home Zone'),
        ('work', 'Work Zone'),
        ('exclusion', 'Exclusion Zone')
    ]
    
    name = models.CharField(max_length=100)
    zone_type = models.CharField(max_length=20, choices=ZONE_TYPE_CHOICES)
    inmate = models.ForeignKey(Inmate, on_delete=models.CASCADE, related_name='geofence_zones')
    center_latitude = models.DecimalField(max_digits=10, decimal_places=6)
    center_longitude = models.DecimalField(max_digits=10, decimal_places=6)
    radius_meters = models.IntegerField()  # Radius in meters
    is_active = models.BooleanField(default=True)
    start_time = models.TimeField(null=True, blank=True)  # Daily time restrictions
    end_time = models.TimeField(null=True, blank=True)
    days_of_week = models.CharField(max_length=20, default='1234567')  # 1=Mon, 7=Sun
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.zone_type}) - {self.inmate}"

class Alert(models.Model):
    ALERT_TYPE_CHOICES = [
        ('geofence_violation', 'Geofence Violation'),
        ('device_tamper', 'Device Tampering'),
        ('low_battery', 'Low Battery'),
        ('device_offline', 'Device Offline'),
        ('emergency', 'Emergency Alert'),
        ('speed_violation', 'Speed Violation'),
        ('curfew_violation', 'Curfew Violation')
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('acknowledged', 'Acknowledged'),
        ('investigating', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('false_alarm', 'False Alarm')
    ]
    
    alert_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    inmate = models.ForeignKey(Inmate, on_delete=models.CASCADE, related_name='alerts')
    device = models.ForeignKey(TrackingDevice, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    title = models.CharField(max_length=200)
    description = models.TextField()
    location_latitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    location_longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    acknowledged_by = models.ForeignKey(ParoleOfficer, on_delete=models.SET_NULL, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.alert_type} - {self.inmate} ({self.created_at})"

class NotificationSettings(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('dashboard', 'Dashboard Only')
    ]
    
    officer = models.OneToOneField(ParoleOfficer, on_delete=models.CASCADE)
    geofence_violations = models.JSONField(default=list)  # List of notification types
    device_tampering = models.JSONField(default=list)
    low_battery = models.JSONField(default=list)
    device_offline = models.JSONField(default=list)
    emergency_alerts = models.JSONField(default=list)
    quiet_hours_start = models.TimeField(default='22:00:00')
    quiet_hours_end = models.TimeField(default='06:00:00')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

