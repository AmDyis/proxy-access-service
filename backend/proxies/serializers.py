from rest_framework import serializers

from proxies.models import VirtualMachine


class VirtualMachineSerializer(serializers.ModelSerializer):
    class Meta:
        model = VirtualMachine
        fields = (
            "id",
            "name",
            "host",
            "port",
            "protocol",
            "is_active",
            "current_user",
            "last_used_at",
        )
        read_only_fields = fields


class ProxyConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VirtualMachine
        fields = (
            "id",
            "name",
            "host",
            "port",
            "protocol",
        )
        read_only_fields = fields
