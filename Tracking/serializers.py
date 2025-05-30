# serializers.py
from rest_framework import serializers
from .models import *

class LocationUpdateSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=50)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    altitude = serializers.FloatField(default=0.0)
    speed = serializers.FloatField(default=0.0)
    satellites = serializers.IntegerField(default=0)
    accuracy = serializers.FloatField(default=0.0)
    battery_level = serializers.FloatField()
    timestamp = serializers.DateTimeField()
    status = serializers.CharField(max_length=20, default='normal')

class CurrentLocationSerializer(serializers.ModelSerializer):
    device_id = serializers.CharField(source='device.device_id', read_only=True)
    inmate_name = serializers.CharField(source='device.inmate.first_name', read_only=True)
    inmate_last_name = serializers.CharField(source='device.inmate.last_name', read_only=True)
    
    class Meta:
        model = CurrentLocation
        fields = '__all__'

class AlertSerializer(serializers.ModelSerializer):
    inmate_name = serializers.CharField(source='inmate.first_name', read_only=True)
    inmate_last_name = serializers.CharField(source='inmate.last_name', read_only=True)
    
    class Meta:
        model = Alert
        fields = '__all__'

class GeofenceZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeofenceZone
        fields = '__all__'
