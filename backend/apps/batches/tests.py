"""Tests for the batches app."""

from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.farms.models import Farm

from .models import Batch


class BatchAPITestCase(APITestCase):
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
            region="Oyo",
            district="Ibadan North",
        )
        self.other_farm = Farm.objects.create(
            owner=self.other_farmer,
            name="Riverside Farm",
            region="Lagos",
        )

    def authenticate(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def batch_payload(self, **overrides):
        payload = {
            "farm": self.farm.pk,
            "crop_name": "Maize",
            "variety": "Yellow",
            "quantity": "250.00",
            "unit": Batch.Unit.KG,
            "planting_date": "2026-03-01",
            "harvest_date": "2026-06-15",
            "description": "First harvest of the season",
            "is_public": True,
        }
        payload.update(overrides)
        return payload

    def create_batch(self, **overrides):
        values = {
            "farm": self.farm,
            "created_by": self.farmer,
            "crop_name": "Maize",
            "quantity": Decimal("100.00"),
            "harvest_date": date(2026, 6, 1),
        }
        values.update(overrides)
        return Batch.objects.create(**values)

    def test_farmer_can_create_a_batch(self):
        self.authenticate(self.farmer)

        response = self.client.post(
            reverse("batch-list"), self.batch_payload(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], Batch.Status.DRAFT)
        self.assertEqual(
            response.data["farm"]["farm_code"], self.farm.farm_code
        )
        self.assertEqual(
            response.data["created_by"]["email"], "farmer@example.com"
        )
        self.assertTrue(response.data["batch_code"].startswith("BATCH-"))
        self.assertEqual(
            response.data["allowed_next_statuses"],
            ["harvested", "recalled"],
        )

        batch = Batch.objects.get(batch_code=response.data["batch_code"])
        self.assertEqual(batch.created_by, self.farmer)

    def test_farmer_cannot_create_a_batch_for_another_farm(self):
        self.authenticate(self.farmer)

        response = self.client.post(
            reverse("batch-list"),
            self.batch_payload(farm=self.other_farm.pk),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_batch_cannot_be_created_for_an_inactive_farm(self):
        self.farm.is_active = False
        self.farm.save(update_fields=["is_active"])
        self.authenticate(self.farmer)

        response = self.client.post(
            reverse("batch-list"), self.batch_payload(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("farm", response.data)

    def test_unverified_farmer_cannot_create_a_batch(self):
        self.authenticate(self.unverified_farmer)

        response = self.client.post(
            reverse("batch-list"), self.batch_payload(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_farmer_cannot_create_a_batch(self):
        self.authenticate(self.consumer)

        response = self.client.post(
            reverse("batch-list"), self.batch_payload(), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_harvest_date_cannot_precede_planting_date(self):
        self.authenticate(self.farmer)

        response = self.client.post(
            reverse("batch-list"),
            self.batch_payload(
                planting_date="2026-06-20", harvest_date="2026-06-01"
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("harvest_date", response.data)

    def test_admin_can_create_a_batch_for_any_farm(self):
        self.authenticate(self.admin)

        response = self.client.post(
            reverse("batch-list"),
            self.batch_payload(farm=self.other_farm.pk),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.data["created_by"]["email"], "root@example.com"
        )

    def test_batch_list_requires_authentication(self):
        response = self.client.get(reverse("batch-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_batch_list_filters(self):
        self.create_batch(status=Batch.Status.HARVESTED)
        self.create_batch(
            farm=self.other_farm,
            created_by=self.other_farmer,
            crop_name="Cassava",
        )
        self.authenticate(self.farmer)

        response = self.client.get(reverse("batch-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        response = self.client.get(
            reverse("batch-list"), {"mine": "true"}
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["farm"]["id"], self.farm.pk)

        response = self.client.get(
            reverse("batch-list"), {"status": Batch.Status.HARVESTED}
        )
        self.assertEqual(len(response.data), 1)

        response = self.client.get(reverse("batch-list"), {"crop": "cass"})
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["crop_name"], "Cassava")

        response = self.client.get(
            reverse("batch-list"), {"farm": self.other_farm.pk}
        )
        self.assertEqual(len(response.data), 1)

        response = self.client.get(
            reverse("batch-list"), {"search": self.farm.farm_code}
        )
        self.assertEqual(len(response.data), 1)

    def test_owner_can_update_a_batch(self):
        batch = self.create_batch()
        self.authenticate(self.farmer)

        response = self.client.patch(
            reverse("batch-detail", args=[batch.pk]),
            {"variety": "White", "quantity": "120.50"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        batch.refresh_from_db()
        self.assertEqual(batch.variety, "White")
        self.assertEqual(batch.quantity, Decimal("120.50"))

    def test_other_farmer_cannot_update_a_batch(self):
        batch = self.create_batch()
        self.authenticate(self.other_farmer)

        response = self.client.patch(
            reverse("batch-detail", args=[batch.pk]),
            {"variety": "Stolen"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_batch_status_follows_the_lifecycle(self):
        batch = self.create_batch()
        self.authenticate(self.farmer)

        response = self.client.patch(
            reverse("batch-detail", args=[batch.pk]),
            {"status": Batch.Status.HARVESTED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Batch.Status.HARVESTED)

        response = self.client.patch(
            reverse("batch-detail", args=[batch.pk]),
            {"status": Batch.Status.SOLD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

        response = self.client.patch(
            reverse("batch-detail", args=[batch.pk]),
            {"status": Batch.Status.RECALLED},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        batch.refresh_from_db()
        self.assertEqual(batch.status, Batch.Status.RECALLED)

    def test_draft_batch_can_be_deleted(self):
        batch = self.create_batch()
        self.authenticate(self.farmer)

        response = self.client.delete(
            reverse("batch-detail", args=[batch.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Batch.objects.filter(pk=batch.pk).exists())

    def test_published_batch_cannot_be_deleted(self):
        batch = self.create_batch(status=Batch.Status.HARVESTED)
        self.authenticate(self.farmer)

        response = self.client.delete(
            reverse("batch-detail", args=[batch.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Batch.objects.filter(pk=batch.pk).exists())

    def test_variety_of_units_and_labels_are_returned(self):
        batch = self.create_batch(unit=Batch.Unit.CRATE)
        self.authenticate(self.farmer)

        response = self.client.get(
            reverse("batch-detail", args=[batch.pk])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unit"], Batch.Unit.CRATE)
        self.assertEqual(response.data["unit_label"], "Crate")
        self.assertEqual(response.data["status_label"], "Draft")
        self.assertEqual(
            response.data["farm"]["name"], "Green Fields"
        )
