from django.contrib import admin
from .models import Inmate, TrackingDevice, GeofenceZone, Alert, NotificationSettings, ParoleOfficer, CurrentLocation, LocationHistory

class InmateAdmin(admin.ModelAdmin):
    list_display = ('inmate_id', 'first_name', 'last_name', 'parole_status', 'assigned_officer')
    list_filter = ('parole_status', 'assigned_officer')
    search_fields = ('inmate_id', 'first_name', 'last_name')

class TrackingDeviceAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'inmate', 'status', 'battery_level')
    list_filter = ('status', 'battery_level')
    search_fields = ('device_id', 'inmate__first_name', 'inmate__last_name')

class GeofenceZoneAdmin(admin.ModelAdmin):
    list_display = ('name', 'zone_type', 'inmate', 'is_active')
    list_filter = ('zone_type', 'is_active')
    search_fields = ('name', 'inmate__first_name', 'inmate__last_name')

class AlertAdmin(admin.ModelAdmin):
    list_display = ('alert_id', 'inmate', 'alert_type', 'severity', 'status')
    list_filter = ('alert_type', 'severity', 'status')
    search_fields = ('alert_id', 'inmate__first_name', 'inmate__last_name')

class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ('officer', 'quiet_hours_start', 'quiet_hours_end')
    search_fields = ('officer__user__username', 'officer__badge_number')

class ParoleOfficerAdmin(admin.ModelAdmin):
    list_display = ('user', 'badge_number', 'department')
    list_filter = ('department',)
    search_fields = ('user__username', 'badge_number', 'email')

class CurrentLocationAdmin(admin.ModelAdmin):
    list_display = ('device', 'latitude', 'longitude', 'speed', 'timestamp', 'updated_at')
    list_filter = ('device__status',)
    search_fields = ('device__device_id', 'device__inmate__first_name', 'device__inmate__last_name')
    readonly_fields = ('updated_at',)

class LocationHistoryAdmin(admin.ModelAdmin):
    list_display = ('device', 'latitude', 'longitude', 'speed', 'timestamp', 'created_at')
    list_filter = ('device__status',)
    search_fields = ('device__device_id', 'device__inmate__first_name', 'device__inmate__last_name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'timestamp'

admin.site.register(Inmate, InmateAdmin)
admin.site.register(TrackingDevice, TrackingDeviceAdmin)
admin.site.register(GeofenceZone, GeofenceZoneAdmin)
admin.site.register(Alert, AlertAdmin)
admin.site.register(NotificationSettings, NotificationSettingsAdmin)
admin.site.register(ParoleOfficer, ParoleOfficerAdmin)
admin.site.register(CurrentLocation, CurrentLocationAdmin)
admin.site.register(LocationHistory, LocationHistoryAdmin)
