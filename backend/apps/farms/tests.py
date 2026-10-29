"""Tests for the farms app."""

from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.batches.models import Batch

from .models import Farm


class FarmAPITestCase(APITestCase):
    password = "InitialPass!234"

    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="root@example.com", password=self.password
        )
        self.farmer = User.objects.create_user(
            email="farmer@example.com",
            password=self.password,
            role=User.Role.FARMER,
            is_verified=True,
            first_name="Femi",
            last_name="Farmer",
        )
        self.other_farmer = User.objects.create_user(
            email="other@example.com",
            password=self.password,
            role=User.Role.FARMER,
            is_verified=True,
        )
        self.unverified_farmer = User.objects.create_user(
            email="pending@example.com",
            password=self.password,
            role=User.Role.FARMER,
            is_verified=False,
        )
        self.consumer = User.objects.create_user(
            email="consumer@example.com",
            password=self.password,
            role=User.Role.CONSUMER,
            is_verified=True,
        )

        self.farm = Farm.objects.create(
            owner=self.farmer,
            name="Green Fields",
            country="Nigeria",
            region="Oyo",
            district="Ibadan North",
            village="Bodija",
            size_hectares=Decimal("4.50"),
        )

    def authenticate(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def farm_payload(self, **overrides):
        payload = {
            "name": "Sunrise Farm",
            "description": "Maize and cassava",
            "country": "Nigeria",
            "region": "Ogun",
            "district": "Abeokuta South",
            "village": "Kuto",
            "latitude": "7.147500",
            "longitude": "3.361900",
            "size_hectares": "12.50",
        }
        payload.update(overrides)
        return payload

    def test_farmer_can_create_a_farm(self):
        self.authenticate(self.farmer)

        response = self.client.post(
            reverse("farm-list"), self.farm_payload(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["owner"]["email"], "farmer@example.com")
        self.assertFalse(response.data["is_verified"])
        self.assertTrue(response.data["farm_code"].startswith("FARM-"))

        farm = Farm.objects.get(farm_code=response.data["farm_code"])
        self.assertEqual(farm.owner, self.farmer)

    def test_unverified_farmer_cannot_create_a_farm(self):
        self.authenticate(self.unverified_farmer)

        response = self.client.post(
            reverse("farm-list"), self.farm_payload(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_farmer_cannot_create_a_farm(self):
        self.authenticate(self.consumer)

        response = self.client.post(
            reverse("farm-list"), self.farm_payload(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_farmer_cannot_assign_ownership_to_someone_else(self):
        self.authenticate(self.farmer)

        response = self.client.post(
            reverse("farm-list"),
            self.farm_payload(owner=self.other_farmer.pk),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_a_farm_for_a_farmer(self):
        self.authenticate(self.admin)

        response = self.client.post(
            reverse("farm-list"),
            self.farm_payload(owner=self.farmer.pk),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["owner"]["email"], "farmer@example.com")

    def test_admin_must_specify_an_owner(self):
        self.authenticate(self.admin)

        response = self.client.post(
            reverse("farm-list"), self.farm_payload(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("owner", response.data)

    def test_farm_list_requires_authentication(self):
        response = self.client.get(reverse("farm-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_farm_list_filters_by_mine_and_search(self):
        Farm.objects.create(
            owner=self.other_farmer,
            name="Riverside Farm",
            region="Lagos",
            district="Epe",
        )
        self.authenticate(self.farmer)

        response = self.client.get(reverse("farm-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        response = self.client.get(reverse("farm-list"), {"mine": "true"})
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["farm_code"], self.farm.farm_code)

        response = self.client.get(
            reverse("farm-list"), {"search": "Riverside"}
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Riverside Farm")

    def test_farm_detail_includes_batch_count(self):
        Batch.objects.create(
            farm=self.farm,
            created_by=self.farmer,
            crop_name="Maize",
            quantity=Decimal("100.00"),
            harvest_date=date(2026, 6, 1),
        )
        self.authenticate(self.farmer)

        response = self.client.get(
            reverse("farm-detail", args=[self.farm.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["batches_count"], 1)

    def test_owner_can_update_a_farm(self):
        self.authenticate(self.farmer)

        response = self.client.patch(
            reverse("farm-detail", args=[self.farm.pk]),
            {"name": "Green Fields Updated", "size_hectares": "5.00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.farm.refresh_from_db()
        self.assertEqual(self.farm.name, "Green Fields Updated")
        self.assertEqual(self.farm.size_hectares, Decimal("5.00"))

    def test_other_farmer_cannot_update_a_farm(self):
        self.authenticate(self.other_farmer)

        response = self.client.patch(
            reverse("farm-detail", args=[self.farm.pk]),
            {"name": "Stolen"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_only_admins_can_verify_a_farm(self):
        self.authenticate(self.farmer)

        response = self.client.patch(
            reverse("farm-detail", args=[self.farm.pk]),
            {"is_verified": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.authenticate(self.admin)
        response = self.client.patch(
            reverse("farm-detail", args=[self.farm.pk]),
            {"is_verified": True},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.farm.refresh_from_db()
        self.assertTrue(self.farm.is_verified)

    def test_owner_can_deactivate_a_farm(self):
        self.authenticate(self.farmer)

        response = self.client.patch(
            reverse("farm-detail", args=[self.farm.pk]),
            {"is_active": False},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.farm.refresh_from_db()
        self.assertFalse(self.farm.is_active)

    def test_farm_with_batches_cannot_be_deleted(self):
        Batch.objects.create(
            farm=self.farm,
            created_by=self.farmer,
            crop_name="Cassava",
            quantity=Decimal("50.00"),
            harvest_date=date(2026, 6, 1),
        )
        self.authenticate(self.farmer)

        response = self.client.delete(
            reverse("farm-detail", args=[self.farm.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Farm.objects.filter(pk=self.farm.pk).exists())

    def test_owner_can_delete_an_empty_farm(self):
        self.authenticate(self.farmer)

        response = self.client.delete(
            reverse("farm-detail", args=[self.farm.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Farm.objects.filter(pk=self.farm.pk).exists())
