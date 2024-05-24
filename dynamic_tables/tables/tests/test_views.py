import json

from django.apps import apps
from django.db import connection, models
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from tables.helpers import construct_dynamic_model
from tables.models import DynamicModel, DynamicModelField


class DynamicModelViewTestCase(APITestCase):

    def setUp(self):
        self.DynamicModel, self.dynamic_model = self._construct_model()
        self.urls = {
            "create_table": reverse("api:table-list"),
            "get_table_data": reverse("api:table-rows", (self.dynamic_model.pk,)),
            "add_table_data": reverse("api:table-row", (self.dynamic_model.pk,)),
            "edit_table": reverse("api:table-edit", (self.dynamic_model.pk,)),
        }

    def _construct_model(self):
        dynamic_model = DynamicModel.objects.create(name="DynamicModel2")
        DynamicModelField.objects.create(
            dynamic_model=dynamic_model,
            name="field_1",
            type=DynamicModelField.DynamicModelFieldType.STRING.value,
            allow_null=False,
            allow_blank=False,
        )
        DynamicModelField.objects.create(
            dynamic_model=dynamic_model, name="field_2", type=DynamicModelField.DynamicModelFieldType.BOOLEAN.value
        )
        DynamicModelField.objects.create(
            dynamic_model=dynamic_model,
            name="field_3",
            type=DynamicModelField.DynamicModelFieldType.NUMBER.value,
            allow_blank=False,
        )
        Model = construct_dynamic_model(dynamic_model)
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(Model)
        return Model, dynamic_model

    def test_create_success(self):
        self.assertEqual(DynamicModel.objects.count(), 1)
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
        self.assertEqual(DynamicModel.objects.count(), 2)
        dynamic_model = DynamicModel.objects.last()
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

    def test_non_letters_table_name(self):
        data = {
            "name": "...",
            "fields": [{"name": "field_1", "type": "boolean"}],
        }
        response = self.client.post(self.urls["create_table"], data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["name"][0], "Only letters are allowed.")

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

    def test_get_table_data_success(self):
        response = self.client.get(self.urls["get_table_data"])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_get_table_data_success_with_data(self):
        self.DynamicModel.objects.create(field_1="Test1", field_2="False", field_3=1)
        self.DynamicModel.objects.create(field_1="Test2", field_2="False", field_3=2)
        self.DynamicModel.objects.create(field_1="Test3", field_2="False", field_3=3)

        expected_data = [
            {"field_1": "Test1", "field_2": False, "field_3": 1.0, "id": 1},
            {"field_1": "Test2", "field_2": False, "field_3": 2.0, "id": 2},
            {"field_1": "Test3", "field_2": False, "field_3": 3.0, "id": 3},
        ]

        response = self.client.get(self.urls["get_table_data"])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), expected_data)

    def test_add_table_data_success(self):
        data = {
            "field_1": "Test1",
            "field_2": False,
            "field_3": 1,
        }
        response = self.client.post(self.urls["add_table_data"], data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        DynamicModel = apps.get_model("tables", "DynamicModel2")
        self.assertEqual(DynamicModel.objects.count(), 1)
        dynamic_model = DynamicModel.objects.first()
        self.assertEqual(dynamic_model.field_1, data["field_1"])
        self.assertEqual(dynamic_model.field_2, data["field_2"])
        self.assertEqual(dynamic_model.field_3, data["field_3"])

    def test_add_table_data_incorrect_data_type(self):
        data = {
            "field_1": "Test1",
            "field_2": False,
            "field_3": "Test2",
        }
        response = self.client.post(self.urls["add_table_data"], data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["field_3"][0], "A valid number is required.")
        DynamicModel = apps.get_model("tables", "DynamicModel2")
        self.assertEqual(DynamicModel.objects.count(), 0)

    def test_add_table_data_none(self):
        data = {
            "field_1": "Test1",
            "field_3": "",
        }
        response = self.client.post(self.urls["add_table_data"], data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        DynamicModel = apps.get_model("tables", "DynamicModel2")
        self.assertEqual(DynamicModel.objects.count(), 1)
        dynamic_model = DynamicModel.objects.first()
        self.assertEqual(dynamic_model.field_1, data["field_1"])
        self.assertEqual(dynamic_model.field_2, None)
        self.assertEqual(dynamic_model.field_3, None)

    def test_add_table_data_incorrect_none(self):
        data = {}
        response = self.client.post(self.urls["add_table_data"], data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["field_1"][0], "This field is required.")
        DynamicModel = apps.get_model("tables", "DynamicModel2")
        self.assertEqual(DynamicModel.objects.count(), 0)
