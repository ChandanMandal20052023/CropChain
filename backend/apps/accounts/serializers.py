"""Serializers for authentication, profile, and user administration."""

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


def tokens_for_user(user):
    """Return a JWT access/refresh pair carrying basic user claims."""
    refresh = RefreshToken.for_user(user)
    refresh["email"] = user.email
    refresh["role"] = user.role
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


def normalize_email(value):
    return value.strip().lower()


def validate_unique_email(value, instance=None):
    queryset = User.objects.filter(email__iexact=value)
    if instance is not None:
        queryset = queryset.exclude(pk=instance.pk)
    if queryset.exists():
        raise serializers.ValidationError(
            "A user with this email address already exists."
        )
    return value


class UserSummarySerializer(serializers.ModelSerializer):
    """Compact account representation for nesting in other resources."""

    full_name = serializers.CharField(read_only=True)
    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "role",
            "role_label",
            "organization",
        )


class UserSerializer(serializers.ModelSerializer):
    """Read-only representation of an account."""

    full_name = serializers.CharField(read_only=True)
    role_label = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "role",
            "role_label",
            "phone",
            "organization",
            "is_verified",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
        )
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    """Self-registration. Administrator accounts cannot be self-assigned."""

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        validators=[validate_password],
    )
    password_confirm = serializers.CharField(
        write_only=True, trim_whitespace=False
    )

    class Meta:
        model = User
        fields = (
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "role",
            "phone",
            "organization",
        )

    def validate_email(self, value):
        return validate_unique_email(normalize_email(value))

    def validate_role(self, value):
        if value == User.Role.ADMIN:
            raise serializers.ValidationError(
                "The administrator role cannot be self-assigned."
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "The two password fields did not match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        role = validated_data.get("role", User.Role.CONSUMER)

        return User.objects.create_user(
            password=password,
            # Consumers do not take part in supply-chain operations, so they
            # do not need administrator verification.
            is_verified=role == User.Role.CONSUMER,
            **validated_data,
        )


class LoginSerializer(serializers.Serializer):
    """Validate email/password credentials and resolve the user."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=normalize_email(attrs["email"]),
            password=attrs["password"],
        )
        if user is None:
            # Deliberately vague: do not reveal whether the email exists or
            # whether the account is inactive.
            raise AuthenticationFailed("Invalid email or password.")
        attrs["user"] = user
        return attrs


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Fields a user may change on their own profile."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone", "organization")


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True, trim_whitespace=False
    )
    new_password = serializers.CharField(
        write_only=True, trim_whitespace=False
    )
    new_password_confirm = serializers.CharField(
        write_only=True, trim_whitespace=False
    )

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError(
                "The current password is incorrect."
            )
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {
                    "new_password_confirm": (
                        "The two password fields did not match."
                    )
                }
            )
        if attrs["new_password"] == attrs["old_password"]:
            raise serializers.ValidationError(
                {"new_password": "The new password must be different."}
            )
        validate_password(
            attrs["new_password"], user=self.context["request"].user
        )
        return attrs

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """Create an account on behalf of an administrator."""

    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        validators=[validate_password],
    )

    class Meta:
        model = User
        fields = (
            "email",
            "password",
            "first_name",
            "last_name",
            "role",
            "phone",
            "organization",
            "is_active",
            "is_verified",
        )

    def validate_email(self, value):
        return validate_unique_email(normalize_email(value))

    def validate_role(self, value):
        request = self.context.get("request")
        if (
            value == User.Role.ADMIN
            and request is not None
            and not request.user.is_superuser
        ):
            raise PermissionDenied(
                "Only superusers can create administrator accounts."
            )
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        if user.role == User.Role.ADMIN and not user.is_staff:
            user.is_staff = True
            user.save(update_fields=["is_staff", "updated_at"])
        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """Update an account on behalf of an administrator."""

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "role",
            "phone",
            "organization",
            "is_active",
            "is_verified",
        )

    def validate_email(self, value):
        return validate_unique_email(
            normalize_email(value), instance=self.instance
        )

    def validate(self, attrs):
        request = self.context.get("request")
        actor = getattr(request, "user", None)
        instance = self.instance

        if instance is not None and actor is not None:
            if (
                instance != actor
                and (instance.is_superuser or instance.role == User.Role.ADMIN)
                and not actor.is_superuser
            ):
                raise PermissionDenied(
                    "Only superusers can modify administrator accounts."
                )
            if (
                attrs.get("role") == User.Role.ADMIN
                and not actor.is_superuser
            ):
                raise PermissionDenied(
                    "Only superusers can grant the administrator role."
                )
            if (
                instance.is_superuser
                and "role" in attrs
                and attrs["role"] != instance.role
            ):
                raise serializers.ValidationError(
                    {"role": "The role of a superuser cannot be changed."}
                )
            if instance == actor and attrs.get("is_active") is False:
                raise serializers.ValidationError(
                    {"is_active": "You cannot deactivate your own account."}
                )
        return attrs

    def update(self, instance, validated_data):
        user = super().update(instance, validated_data)
        if user.role == User.Role.ADMIN and not user.is_staff:
            user.is_staff = True
            user.save(update_fields=["is_staff", "updated_at"])
        return user
