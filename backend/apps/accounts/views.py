"""Authentication and account-management API views."""

from django.contrib.auth.models import update_last_login
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .permissions import IsAdmin
from .serializers import (
    AdminUserCreateSerializer,
    AdminUserUpdateSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
    tokens_for_user,
)


class RegisterView(generics.CreateAPIView):
    """Register a new account and return a JWT pair for it."""

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        data = tokens_for_user(user)
        data["user"] = UserSerializer(user).data
        return Response(
            data,
            status=status.HTTP_201_CREATED,
            headers=self.get_success_headers(serializer.data),
        )


class LoginView(APIView):
    """Authenticate with email and password and issue JWT tokens."""

    permission_classes = [AllowAny]
    # Credentials are the only thing needed here. A stale Authorization
    # header (for example an expired token in browser storage) must not
    # prevent the user from logging back in.
    authentication_classes = []
    serializer_class = LoginSerializer

    def get_authenticate_header(self, request):
        # Return 401 rather than 403 for bad credentials even though this
        # view deliberately has no authenticator.
        return "Bearer"

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        update_last_login(None, user)
        data = tokens_for_user(user)
        data["user"] = UserSerializer(user).data
        return Response(data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """Blacklist a refresh token so it can no longer be used."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {
                    "detail": "A refresh token is required.",
                    "code": "refresh_required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            return Response(
                {
                    "detail": "The refresh token is invalid or expired.",
                    "code": "invalid_token",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    """Read or update the authenticated user's own profile."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return ProfileUpdateSerializer
        return UserSerializer

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(
            self.get_object(), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(self.get_object()).data)


class ChangePasswordView(APIView):
    """Change the authenticated user's password."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "detail": (
                    "Password updated successfully. Existing tokens remain "
                    "valid until they expire."
                )
            },
            status=status.HTTP_200_OK,
        )


class RoleListView(APIView):
    """List the roles that can be assigned to an account."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response(
            [
                {
                    "value": value,
                    "label": label,
                    "self_assignable": value != User.Role.ADMIN,
                }
                for value, label in User.Role.choices
            ]
        )


def _parse_boolean(value):
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "yes", "on"}


class UserListCreateView(generics.ListCreateAPIView):
    """List or create accounts. Restricted to administrators."""

    permission_classes = [IsAdmin]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdminUserCreateSerializer
        return UserSerializer

    def get_queryset(self):
        queryset = User.objects.all()
        params = self.request.query_params

        role = params.get("role")
        if role:
            queryset = queryset.filter(role=role)

        is_active = _parse_boolean(params.get("is_active"))
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        is_verified = _parse_boolean(params.get("is_verified"))
        if is_verified is not None:
            queryset = queryset.filter(is_verified=is_verified)

        search = params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(organization__icontains=search)
                | Q(phone__icontains=search)
            )
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserSerializer(user).data, status=status.HTTP_201_CREATED
        )


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or deactivate a single account.

    Deletion is a soft delete: the account is deactivated so that audit and
    traceability records that reference it remain intact.
    """

    permission_classes = [IsAdmin]
    queryset = User.objects.all()
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return AdminUserUpdateSerializer
        return UserSerializer

    def update(self, request, *args, **kwargs):
        partial = True
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()

        if user == request.user:
            return Response(
                {"detail": "You cannot deactivate your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if (
            user.is_superuser or user.role == User.Role.ADMIN
        ) and not request.user.is_superuser:
            raise PermissionDenied(
                "Only superusers can deactivate administrator accounts."
            )

        if user.is_active:
            user.is_active = False
            user.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)
