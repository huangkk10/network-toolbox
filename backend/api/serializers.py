from rest_framework import serializers
from .models import DHCPServer, DHCPLease


class DHCPServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = DHCPServer
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class DHCPLeaseSerializer(serializers.ModelSerializer):
    server_name = serializers.CharField(source='server.name', read_only=True)
    
    class Meta:
        model = DHCPLease
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
