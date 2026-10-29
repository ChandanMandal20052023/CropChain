"""URL routes for authentication and account management."""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="auth-register"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", views.MeView.as_view(), name="auth-me"),
    path(
        "auth/change-password/",
        views.ChangePasswordView.as_view(),
        name="auth-change-password",
    ),
    path("auth/roles/", views.RoleListView.as_view(), name="auth-roles"),
    path("users/", views.UserListCreateView.as_view(), name="user-list"),
    path(
        "users/<int:pk>/",
        views.UserDetailView.as_view(),
        name="user-detail",
    ),
]
