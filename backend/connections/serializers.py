from rest_framework import serializers


class ActivateKeySerializer(serializers.Serializer):
    activation_key = serializers.CharField(max_length=64)


class DisconnectBySessionSerializer(serializers.Serializer):
    connection_token = serializers.CharField(max_length=64)
