import re

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import User
from .utils import normalize_phone


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["id", "phone", "name", "role", "password"]

    def validate_phone(self, value):
        phone = normalize_phone(value)
        if not re.fullmatch(r"\+\d{10,15}", phone):
            raise serializers.ValidationError("Numéro de téléphone invalide.")
        if User.objects.filter(phone=phone).exists():
            raise serializers.ValidationError("Ce numéro est déjà utilisé.")
        return phone

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "phone", "name", "role", "cancellation_count"]
        read_only_fields = fields


class PhoneTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        attrs["phone"] = normalize_phone(attrs.get("phone", ""))
        data = super().validate(attrs)
        data["role"] = self.user.role
        return data
