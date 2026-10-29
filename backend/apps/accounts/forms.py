"""Forms used by the Django admin for the custom user model."""

from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User


class UserCreationForm(forms.ModelForm):
    """Create a user from the Django admin with a validated password."""

    password1 = forms.CharField(
        label="Password", strip=False, widget=forms.PasswordInput
    )
    password2 = forms.CharField(
        label="Password confirmation", strip=False, widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = (
            "email",
            "role",
            "first_name",
            "last_name",
            "phone",
            "organization",
            "is_verified",
            "is_active",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                "A user with this email address already exists."
            )
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error(
                "password2", "The two password fields did not match."
            )
        elif password2:
            candidate = User(
                email=cleaned_data.get("email") or "",
                first_name=cleaned_data.get("first_name") or "",
                last_name=cleaned_data.get("last_name") or "",
            )
            try:
                validate_password(password2, user=candidate)
            except ValidationError as error:
                self.add_error("password2", error)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """Edit a user from the Django admin without exposing the password hash."""

    password = ReadOnlyPasswordHashField(
        label="Password",
        help_text=(
            "Raw passwords are not stored, so there is no way to see this "
            "user's password, but you can change it using the password form."
        ),
    )

    class Meta:
        model = User
        fields = (
            "email",
            "password",
            "role",
            "first_name",
            "last_name",
            "phone",
            "organization",
            "is_verified",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        queryset = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError(
                "A user with this email address already exists."
            )
        return email
