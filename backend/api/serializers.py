from rest_framework import serializers
from django.contrib.auth.models import User
from .models import DHCPServer, DHCPLease


class UserSerializer(serializers.ModelSerializer):
    """用戶序列化器"""
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 
                  'is_active', 'is_staff', 'is_superuser', 'date_joined', 'password')
        read_only_fields = ('date_joined',)
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


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
