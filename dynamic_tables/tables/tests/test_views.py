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
        self.dynamic_model, self.field_1, self.field_2, self.field_3, self.CustomModel = self._construct_model(
            "DynamicModel2"
        )
        self.urls = {
            "create_table": reverse("api:table-list"),
            "get_table_data": reverse("api:table-rows", (self.dynamic_model.pk,)),
            "add_table_data": reverse("api:table-row", (self.dynamic_model.pk,)),
            "edit_table": reverse("api:table-edit", (self.dynamic_model.pk,)),
        }

    def _construct_model(self, model_name):
        dynamic_model = DynamicModel.objects.create(name=model_name)
        field_1 = DynamicModelField.objects.create(
            dynamic_model=dynamic_model,
            name="field_1",
            type=DynamicModelField.DynamicModelFieldType.STRING.value,
            allow_null=False,
        )
        field_2 = DynamicModelField.objects.create(
            dynamic_model=dynamic_model, name="field_2", type=DynamicModelField.DynamicModelFieldType.BOOLEAN.value
        )
        field_3 = DynamicModelField.objects.create(
            dynamic_model=dynamic_model,
            name="field_3",
            type=DynamicModelField.DynamicModelFieldType.NUMBER.value,
        )
        CustomModel = construct_dynamic_model(dynamic_model)
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(CustomModel)
        return dynamic_model, field_1, field_2, field_3, CustomModel

    def _create_dynamic_model_in_chain(self):
        data = {
            "name": "Test",
            "fields": [
                {"name": "field_1", "type": "boolean"},
                {"name": "field_2", "type": "string"},
                {"name": "field_3", "type": "number"},
            ],
        }
        response = self.client.post(self.urls["create_table"], data=json.dumps(data), content_type="application/json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.json()["id"]

    def _add_data_in_chain(self, created_instance_pk):
        for i in range(5):
            data = {
                "field_1": False,
                "field_2": f"Test{i}",
                "field_3": i,
            }
            self.client.post(reverse("api:table-row", (created_instance_pk,)), data)
            self.client.post(reverse("api:table-row", (created_instance_pk,)), {})

    def _edit_field_name_in_chain(self, created_instance_pk, field_id):
        data = {"id": field_id, "action": "update", "name": f"name_{field_id}", "allow_null": True}
        self.client.put(reverse("api:table-edit", (created_instance_pk,)), data)

    def _delete_field_in_chain(self, created_instance_pk, field_id):
        data = {
            "id": field_id,
            "action": "delete",
        }
        self.client.put(reverse("api:table-edit", (created_instance_pk,)), data)

    def _add_field_in_chain(self, created_instance_pk):
        data = {"action": "create", "name": "field_4", "type": "string", "allow_null": True}
        self.client.put(reverse("api:table-edit", (created_instance_pk,)), data)

    def _edit_field_null_in_chain(self, created_instance_pk, field_id):
        data = {"id": field_id, "action": "update", "allow_null": False}
        self.client.put(reverse("api:table-edit", (created_instance_pk,)), data)

    def test_create_success(self):
        self.assertEqual(DynamicModel.objects.count(), 1)
        data = {
            "name": "Test",
            "fields": [
                {"name": "field_1", "type": "boolean", "allow_null": True},
                {"name": "field_2", "type": "string", "allow_null": False},
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
        self.assertTrue(any(isinstance(field, models.TextField) and not field.null for field in fields))
        self.assertTrue(any(isinstance(field, models.BooleanField) and field.null for field in fields))
        self.assertTrue(any(isinstance(field, models.FloatField) and field.null for field in fields))

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
        self.CustomModel.objects.create(field_1="Test1", field_2="False", field_3=1)
        self.CustomModel.objects.create(field_1="Test2", field_2="False", field_3=2)
        self.CustomModel.objects.create(field_1="Test3", field_2="False", field_3=3)

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

    def test_edit_field_name_success(self):
        data = {
            "id": self.field_3.id,
            "action": "update",
            "name": "name_3",
            "allow_null": True,
        }
        response = self.client.put(self.urls["edit_table"], data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.field_3.refresh_from_db()
        self.assertEqual(self.field_3.name, data["name"])
        DynamicModel = apps.get_model("tables", "DynamicModel2")
        fields = DynamicModel._meta.get_fields()
        self.assertTrue(any(isinstance(field, models.FloatField) and field.name == data["name"] for field in fields))

    def test_edit_field_name_incorrect_id_on_update(self):
        _, field_1, _, _, _ = self._construct_model("DynamicModel3")
        data = {
            "id": field_1.id,
            "action": "update",
            "name": "name_3",
            "allow_null": True,
        }
        response = self.client.put(self.urls["edit_table"], data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["non_field_errors"][0], "Field with this id does not exists for this model.")

    def test_edit_field_missing_id(self):
        data = {
            "action": "update",
            "name": "name_3",
        }
        response = self.client.put(self.urls["edit_table"], data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["non_field_errors"][0], "Id is required for update or delete")

    def test_edit_field_type(self):
        data = {
            "id": self.field_3.id,
            "action": "update",
            "type": "boolean",
            "allow_null": True,
        }
        response = self.client.put(self.urls["edit_table"], data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["non_field_errors"][0], "Type of already existing column cannot be updated")

    def test_add_field_type(self):
        data = {
            "action": "create",
            "name": "boolean_field",
            "type": "boolean",
        }
        response = self.client.put(self.urls["edit_table"], data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            "While adding or modifying columns, allow_null is required to be True",
        )

    def test_field_name_incorrect_id_on_delete(self):
        _, field_1, _, _, _ = self._construct_model("DynamicModel3")
        data = {
            "id": field_1.id,
            "action": "delete",
            "name": "name_3",
        }
        response = self.client.put(self.urls["edit_table"], data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["non_field_errors"][0], "Field with this id does not exists for this model.")

    def test_delete_field(self):
        data = {
            "id": self.field_3.id,
            "action": "delete",
        }
        self.assertEqual(self.dynamic_model.fields.count(), 3)
        response = self.client.put(self.urls["edit_table"], data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.dynamic_model.fields.count(), 2)
        DynamicModel = construct_dynamic_model(self.dynamic_model)
        fields = DynamicModel._meta.get_fields()
        instance = DynamicModel()
        setattr(instance, self.field_3.name, "Test")
        instance.save()
        instance_new = DynamicModel.objects.get(id=instance.pk)
        self.assertFalse(any(isinstance(field, models.FloatField) for field in fields))
        with self.assertRaises(AttributeError):
            getattr(instance_new, self.field_3.name)

    def test_delete_field_missing_id(self):
        data = {
            "action": "delete",
            "name": "name_3",
        }
        response = self.client.put(self.urls["edit_table"], data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["non_field_errors"][0], "Id is required for update or delete")

    def test_create_field_missing_type(self):
        data = {"action": "create", "name": "Test_1"}
        response = self.client.put(self.urls["edit_table"], data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["non_field_errors"][0], "Name and type is required for create")

    def test_create_field_missing_name(self):
        data = {"action": "create", "type": "string"}
        response = self.client.put(self.urls["edit_table"], data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["non_field_errors"][0], "Name and type is required for create")

    def test_create_field_string(self):
        data = {"id": 1, "action": "create", "type": "string", "name": "Test_1", "allow_null": True}
        response = self.client.put(self.urls["edit_table"], data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        DynamicModel = construct_dynamic_model(self.dynamic_model)
        instance = DynamicModel()
        setattr(instance, data["name"], "New_name")
        instance.save()
        instance_new = DynamicModel.objects.get(id=instance.pk)
        self.assertEqual(instance_new.Test_1, "New_name")

    def test_create_field_number(self):
        data = {"id": 1, "action": "create", "type": "number", "name": "Test_1", "allow_null": True}
        response = self.client.put(self.urls["edit_table"], data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        DynamicModel = construct_dynamic_model(self.dynamic_model)
        instance = DynamicModel()
        setattr(instance, data["name"], 32)
        instance.save()
        instance_new = DynamicModel.objects.get(id=instance.pk)
        self.assertEqual(instance_new.Test_1, 32.0)

    def test_create_field_already_exists(self):
        data = {"id": 1, "action": "create", "type": "boolean", "name": self.field_3.name, "allow_null": True}
        response = self.client.put(self.urls["edit_table"], data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["non_field_errors"][0], "Field with this name already exists in this model.")

    def test_create_field_without_allow_null(self):
        data = {
            "id": 1,
            "action": "create",
            "type": "boolean",
            "name": self.field_3.name,
        }
        response = self.client.put(self.urls["edit_table"], data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            "While adding or modifying columns, allow_null is required to be True",
        )

    def test_create_field_without_allow_false(self):
        data = {"id": 1, "action": "create", "type": "boolean", "name": self.field_3.name, "allow_null": False}
        response = self.client.put(self.urls["edit_table"], data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["non_field_errors"][0],
            "While adding or modifying columns, allow_null is required to be True",
        )

    def test_chain_actions_create_and_get(self):
        created_instance_pk = self._create_dynamic_model_in_chain()
        self._add_data_in_chain(created_instance_pk)
        response = self.client.get(reverse("api:table-rows", (created_instance_pk,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.json()
        self.assertEqual(len(rows), 10)

    def test_chain_actions_create_and_get_empty(self):
        created_instance_pk = self._create_dynamic_model_in_chain()
        response = self.client.get(reverse("api:table-rows", (created_instance_pk,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_chain_actions_create_add_edit_and_get(self):
        created_instance_pk = self._create_dynamic_model_in_chain()
        self._add_data_in_chain(created_instance_pk)
        for field in DynamicModel.objects.get(pk=created_instance_pk).fields.all():
            self._edit_field_name_in_chain(created_instance_pk, field.pk)
        self._add_data_in_chain(created_instance_pk)
        response = self.client.get(reverse("api:table-rows", (created_instance_pk,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 20)

    def test_chain_actions_create_add_delete_and_get(self):
        created_instance_pk = self._create_dynamic_model_in_chain()
        self._add_data_in_chain(created_instance_pk)
        field = DynamicModel.objects.get(pk=created_instance_pk).fields.first()
        self._delete_field_in_chain(created_instance_pk, field.pk)
        self._add_data_in_chain(created_instance_pk)
        response = self.client.get(reverse("api:table-rows", (created_instance_pk,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 20)

    def test_chain_actions_create_add_modify_and_get(self):
        created_instance_pk = self._create_dynamic_model_in_chain()
        self._add_data_in_chain(created_instance_pk)
        self._add_field_in_chain(created_instance_pk)
        self._add_data_in_chain(created_instance_pk)
        response = self.client.get(reverse("api:table-rows", (created_instance_pk,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 20)
