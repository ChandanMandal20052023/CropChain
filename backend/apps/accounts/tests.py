"""Tests for the accounts app."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


class AccountAPITestCase(APITestCase):
    password = "InitialPass!234"

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            email="root@example.com",
            password=self.password,
            first_name="Root",
            last_name="Admin",
        )
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password=self.password,
            role=User.Role.ADMIN,
            is_verified=True,
            is_staff=True,
            first_name="Ada",
            last_name="Admin",
        )
        self.farmer = User.objects.create_user(
            email="farmer@example.com",
            password=self.password,
            role=User.Role.FARMER,
            is_verified=True,
            first_name="Femi",
            last_name="Farmer",
        )
        self.consumer = User.objects.create_user(
            email="consumer@example.com",
            password=self.password,
            role=User.Role.CONSUMER,
            is_verified=True,
        )

    def login(self, email, password=None):
        return self.client.post(
            reverse("auth-login"),
            {"email": email, "password": password or self.password},
            format="json",
        )

    def authenticate(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def logout_credentials(self):
        self.client.credentials()

    # Registration

    def test_register_consumer_returns_tokens_and_profile(self):
        response = self.client.post(
            reverse("auth-register"),
            {
                "email": "New.Consumer@Example.com",
                "password": "AnotherPass!234",
                "password_confirm": "AnotherPass!234",
                "first_name": "New",
                "last_name": "Consumer",
                "role": User.Role.CONSUMER,
                "phone": "+2348000000000",
                "organization": "",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["role"], User.Role.CONSUMER)
        self.assertTrue(response.data["user"]["is_verified"])

        user = User.objects.get(email="new.consumer@example.com")
        self.assertTrue(user.check_password("AnotherPass!234"))

    def test_register_business_role_starts_unverified(self):
        response = self.client.post(
            reverse("auth-register"),
            {
                "email": "new.farmer@example.com",
                "password": "AnotherPass!234",
                "password_confirm": "AnotherPass!234",
                "role": User.Role.FARMER,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="new.farmer@example.com")
        self.assertFalse(user.is_verified)
        self.assertFalse(response.data["user"]["is_verified"])

    def test_register_cannot_self_assign_admin_role(self):
        response = self.client.post(
            reverse("auth-register"),
            {
                "email": "sneaky@example.com",
                "password": "AnotherPass!234",
                "password_confirm": "AnotherPass!234",
                "role": User.Role.ADMIN,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("role", response.data)
        self.assertFalse(User.objects.filter(email="sneaky@example.com").exists())

    def test_register_rejects_duplicate_email_case_insensitively(self):
        response = self.client.post(
            reverse("auth-register"),
            {
                "email": "FARMER@EXAMPLE.COM",
                "password": "AnotherPass!234",
                "password_confirm": "AnotherPass!234",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_rejects_mismatched_passwords(self):
        response = self.client.post(
            reverse("auth-register"),
            {
                "email": "mismatch@example.com",
                "password": "AnotherPass!234",
                "password_confirm": "DifferentPass!234",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.data)

    def test_register_rejects_weak_password(self):
        response = self.client.post(
            reverse("auth-register"),
            {
                "email": "weak@example.com",
                "password": "12345678",
                "password_confirm": "12345678",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    # Login and tokens

    def test_login_is_case_insensitive_and_records_last_login(self):
        response = self.login("FARMER@EXAMPLE.COM")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], "farmer@example.com")
        self.assertEqual(response.data["user"]["role"], User.Role.FARMER)

        self.farmer.refresh_from_db()
        self.assertIsNotNone(self.farmer.last_login)

    def test_login_rejects_wrong_password(self):
        response = self.login("farmer@example.com", "WrongPass!234")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_ignores_a_stale_authorization_header(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token")

        response = self.login("farmer@example.com")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_login_rejects_inactive_account(self):
        self.consumer.is_active = False
        self.consumer.save(update_fields=["is_active"])

        response = self.login("consumer@example.com")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_returns_a_usable_access_token(self):
        tokens = self.login("farmer@example.com").data
        self.logout_credentials()

        response = self.client.post(
            reverse("auth-refresh"),
            {"refresh": tokens["refresh"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        # Rotation is enabled, so a fresh refresh token is issued too.
        self.assertIn("refresh", response.data)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )
        me = self.client.get(reverse("auth-me"))
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["email"], "farmer@example.com")

    def test_logout_blacklists_the_refresh_token(self):
        tokens = self.login("farmer@example.com").data
        self.authenticate(self.farmer)

        response = self.client.post(
            reverse("auth-logout"),
            {"refresh": tokens["refresh"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.logout_credentials()
        refresh = self.client.post(
            reverse("auth-refresh"),
            {"refresh": tokens["refresh"]},
            format="json",
        )
        self.assertEqual(refresh.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_requires_a_refresh_token(self):
        self.authenticate(self.farmer)

        response = self.client.post(
            reverse("auth-logout"), {}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # Profile and password

    def test_me_requires_authentication(self):
        response = self.client.get(reverse("auth-me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_reads_and_updates_own_profile(self):
        self.authenticate(self.farmer)

        response = self.client.get(reverse("auth-me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "farmer@example.com")

        response = self.client.patch(
            reverse("auth-me"),
            {
                "first_name": "Updated",
                "phone": "+2348111111111",
                "role": User.Role.ADMIN,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Updated")
        self.assertEqual(response.data["phone"], "+2348111111111")
        # Role is not editable through the profile endpoint.
        self.assertEqual(response.data["role"], User.Role.FARMER)

    def test_change_password(self):
        self.authenticate(self.farmer)

        wrong = self.client.post(
            reverse("auth-change-password"),
            {
                "old_password": "NopePass!234",
                "new_password": "UpdatedPass!234",
                "new_password_confirm": "UpdatedPass!234",
            },
            format="json",
        )
        self.assertEqual(wrong.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("old_password", wrong.data)

        response = self.client.post(
            reverse("auth-change-password"),
            {
                "old_password": self.password,
                "new_password": "UpdatedPass!234",
                "new_password_confirm": "UpdatedPass!234",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.logout_credentials()
        self.assertEqual(
            self.login("farmer@example.com").status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.login("farmer@example.com", "UpdatedPass!234").status_code,
            status.HTTP_200_OK,
        )

    def test_roles_endpoint_is_public_and_hides_admin_from_self_signup(self):
        response = self.client.get(reverse("auth-roles"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        roles = {item["value"]: item for item in response.data}
        self.assertIn(User.Role.FARMER, roles)
        self.assertIn(User.Role.INSPECTOR, roles)
        self.assertFalse(roles[User.Role.ADMIN]["self_assignable"])

    # User administration

    def test_admin_can_list_and_filter_users(self):
        self.authenticate(self.admin)

        response = self.client.get(reverse("user-list"), {"role": "farmer"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["email"], "farmer@example.com")

        response = self.client.get(reverse("user-list"), {"search": "Ada"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["email"], "admin@example.com")

    def test_non_admin_cannot_manage_users(self):
        self.authenticate(self.farmer)

        response = self.client.get(reverse("user-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.logout_credentials()
        response = self.client.get(reverse("user-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_create_a_user(self):
        self.authenticate(self.admin)

        response = self.client.post(
            reverse("user-list"),
            {
                "email": "inspector@example.com",
                "password": "InspectorPass!234",
                "first_name": "Ines",
                "last_name": "Inspector",
                "role": User.Role.INSPECTOR,
                "phone": "",
                "organization": "Quality Board",
                "is_active": True,
                "is_verified": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="inspector@example.com")
        self.assertEqual(user.role, User.Role.INSPECTOR)
        self.assertTrue(user.is_verified)
        self.assertFalse(user.is_staff)

    def test_admin_cannot_create_another_admin(self):
        self.authenticate(self.admin)

        response = self.client.post(
            reverse("user-list"),
            {
                "email": "admin2@example.com",
                "password": "AnotherAdmin!234",
                "role": User.Role.ADMIN,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(User.objects.filter(email="admin2@example.com").exists())

    def test_superuser_can_create_an_admin(self):
        self.authenticate(self.superuser)

        response = self.client.post(
            reverse("user-list"),
            {
                "email": "admin2@example.com",
                "password": "AnotherAdmin!234",
                "role": User.Role.ADMIN,
                "is_verified": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="admin2@example.com")
        self.assertEqual(user.role, User.Role.ADMIN)
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_admin_can_update_a_user(self):
        self.authenticate(self.admin)

        response = self.client.patch(
            reverse("user-detail", args=[self.farmer.pk]),
            {"is_verified": False, "organization": "Green Fields"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.farmer.refresh_from_db()
        self.assertFalse(self.farmer.is_verified)
        self.assertEqual(self.farmer.organization, "Green Fields")

    def test_admin_cannot_modify_a_superuser(self):
        self.authenticate(self.admin)

        response = self.client.patch(
            reverse("user-detail", args=[self.superuser.pk]),
            {"first_name": "Hacked"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.delete(
            reverse("user-detail", args=[self.superuser.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_deactivate_their_own_account(self):
        self.authenticate(self.admin)

        response = self.client.delete(
            reverse("user-detail", args=[self.admin.pk])
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.patch(
            reverse("user-detail", args=[self.admin.pk]),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_deactivates_a_user_without_deleting_the_record(self):
        self.authenticate(self.admin)

        response = self.client.delete(
            reverse("user-detail", args=[self.consumer.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.consumer.refresh_from_db()
        self.assertFalse(self.consumer.is_active)

        self.logout_credentials()
        self.assertEqual(
            self.login("consumer@example.com").status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
