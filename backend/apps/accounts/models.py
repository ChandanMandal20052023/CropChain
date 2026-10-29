"""User model, role definitions, and manager for the accounts app."""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Manager for the email-based custom user model."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email).strip().lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.CONSUMER)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, username):
        """Allow case-insensitive authentication by email address."""
        return self.get(email__iexact=username)


class User(AbstractUser):
    """Platform account.

    Authentication is email-based, and every account carries a role that
    determines which parts of the supply chain it may operate.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        FARMER = "farmer", "Farmer"
        SUPPLIER = "supplier", "Supplier"
        WAREHOUSE = "warehouse", "Warehouse Operator"
        TRANSPORTER = "transporter", "Transporter"
        PROCESSOR = "processor", "Processor"
        INSPECTOR = "inspector", "Quality Inspector"
        RETAILER = "retailer", "Retailer"
        CONSUMER = "consumer", "Consumer"

    username = None
    email = models.EmailField("email address", unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CONSUMER,
        db_index=True,
    )
    phone = models.CharField(max_length=32, blank=True)
    organization = models.CharField(max_length=150, blank=True)
    is_verified = models.BooleanField(
        default=False,
        help_text=(
            "Designates whether an administrator has verified this account "
            "for supply-chain operations."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ["-date_joined", "-id"]
        verbose_name = "user"
        verbose_name_plural = "users"

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return self.get_full_name() or self.email

    @property
    def is_admin_role(self):
        """True for superusers and accounts holding the administrator role."""
        return self.is_superuser or self.role == self.Role.ADMIN

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"
