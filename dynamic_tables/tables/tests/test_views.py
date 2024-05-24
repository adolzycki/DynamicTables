import json

from django.apps import apps
from django.db import models
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from tables.models import DynamicModel


class DynamicModelViewTestCase(APITestCase):

    def setUp(self):
        self.urls = {
            "create_table": reverse("api:table-list"),
            "get_table_data": reverse("api:table-rows", (1,)),
            "add_table_data": reverse("api:table-row", (1,)),
            "edit_table": reverse("api:table-edit", (1,)),
        }

    def test_create_success(self):
        data = {
            "name": "Test",
            "fields": [
                {"name": "field_1", "type": "boolean", "allow_null": True, "allow_blank": False},
                {"name": "field_2", "type": "string", "allow_null": False, "allow_blank": True},
                {"name": "field_3", "type": "number"},
            ],
        }
        response = self.client.post(self.urls["create_table"], data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DynamicModel.objects.count(), 1)
        dynamic_model = DynamicModel.objects.first()
        self.assertEqual(dynamic_model.fields.count(), 3)
        self.assertTrue(
            dynamic_model.fields.filter(name=data["fields"][0]["name"], type=data["fields"][0]["type"]).exists()
        )
        self.assertTrue(
            dynamic_model.fields.filter(name=data["fields"][1]["name"], type=data["fields"][1]["type"]).exists()
        )
        self.assertTrue(
            dynamic_model.fields.filter(name=data["fields"][2]["name"], type=data["fields"][2]["type"]).exists()
        )

        self.assertTrue(apps.get_model("tables", data["name"]))
        Test = apps.get_model("tables", data["name"])
        fields = Test._meta.get_fields()
        self.assertTrue(any(isinstance(field, models.TextField) and not field.null and field.blank for field in fields))
        self.assertTrue(
            any(isinstance(field, models.BooleanField) and field.null and not field.blank for field in fields)
        )
        self.assertTrue(any(isinstance(field, models.FloatField) and field.null and field.blank for field in fields))

    def test_same_field_name_twice(self):
        data = {
            "name": "Test",
            "fields": [{"name": "field_1", "type": "boolean"}, {"name": "field_1", "type": "number"}],
        }
        response = self.client.post(self.urls["create_table"], data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["non_field_errors"][0], "Field names must be unique.")

    def test_same_model_name_twice(self):
        data = {
            "name": "Test",
            "fields": [
                {"name": "field_1", "type": "boolean"},
            ],
        }
        response = self.client.post(self.urls["create_table"], data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.post(self.urls["create_table"], data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["name"][0], "dynamic model with this name already exists.")

    def test_incorrect_model_type(self):
        data = {
            "name": "Test",
            "fields": [
                {"name": "field_1", "type": "wrong_type"},
            ],
        }
        response = self.client.post(self.urls["create_table"], data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["fields"][0]["type"][0], '"wrong_type" is not a valid choice.')
