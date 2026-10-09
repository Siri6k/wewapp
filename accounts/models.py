from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone, password=None, **extra):
        if not phone:
            raise ValueError("Le numéro de téléphone est obligatoire")
        user = self.model(phone=phone, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(phone, password, **extra)


class User(AbstractUser):
    class Role(models.TextChoices):
        PASSENGER = "passenger", "Passager"
        DRIVER = "driver", "Motard"

    username = None
    phone = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.PASSENGER)
    cancellation_count = models.PositiveIntegerField(default=0)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    def __str__(self):
        return f"{self.name} ({self.phone})"
