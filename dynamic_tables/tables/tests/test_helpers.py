from django.db import models
from django.test import TestCase
from rest_framework import serializers
from tables.helpers import construct_dynamic_model, construct_dynamic_serializer, construct_field
from tables.models import DynamicModel, DynamicModelField


class ConstructDynamicModelTestCase(TestCase):
    def setUp(self):
        self.dynamic_model = DynamicModel.objects.create(name="TestModel")
        self.string_field = DynamicModelField.objects.create(
            name="string_field",
            type=DynamicModelField.DynamicModelFieldType.STRING,
            allow_null=True,
            dynamic_model=self.dynamic_model,
        )
        self.number_field = DynamicModelField.objects.create(
            name="number_field",
            type=DynamicModelField.DynamicModelFieldType.NUMBER,
            allow_null=False,
            dynamic_model=self.dynamic_model,
        )
        self.boolean_field = DynamicModelField.objects.create(
            name="boolean_field",
            type=DynamicModelField.DynamicModelFieldType.BOOLEAN,
            allow_null=True,
            dynamic_model=self.dynamic_model,
        )

    def test_construct_dynamic_model(self):
        DynamicModelClass = construct_dynamic_model(self.dynamic_model)
        self.assertTrue(issubclass(DynamicModelClass, models.Model))
        self.assertTrue(hasattr(DynamicModelClass, "string_field"))
        self.assertTrue(hasattr(DynamicModelClass, "number_field"))
        self.assertTrue(hasattr(DynamicModelClass, "boolean_field"))

    def test_construct_dynamic_serializer(self):
        DynamicModelClass = construct_dynamic_model(self.dynamic_model)
        fields = ["string_field", "number_field", "boolean_field"]
        DynamicSerializerClass = construct_dynamic_serializer(DynamicModelClass, fields)
        self.assertTrue(issubclass(DynamicSerializerClass, serializers.ModelSerializer))
        self.assertEqual(DynamicSerializerClass.Meta.model, DynamicModelClass)
        self.assertEqual(DynamicSerializerClass.Meta.fields, fields)

    def test_construct_field(self):
        string_field_instance = construct_field(self.string_field)
        self.assertIsInstance(string_field_instance, models.TextField)
        self.assertTrue(string_field_instance.null)

        number_field_instance = construct_field(self.number_field)
        self.assertIsInstance(number_field_instance, models.FloatField)
        self.assertFalse(number_field_instance.null)

        boolean_field_instance = construct_field(self.boolean_field)
        self.assertIsInstance(boolean_field_instance, models.BooleanField)
        self.assertTrue(boolean_field_instance.null)
