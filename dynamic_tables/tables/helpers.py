from django.db import models
from rest_framework import serializers
from tables.models import DynamicModelField


def construct_dynamic_model(dynamic_model):
    attrs = {"__module__": "tables.models"}
    for field in dynamic_model.fields.all():
        attrs[field.name] = construct_field(field)

    return type(dynamic_model.name, (models.Model,), attrs)


def construct_dynamic_serializer(model, fields):
    MetaClass = type("Meta", (), {"model": model, "fields": fields})
    return type(f"DynamicSerializer", (serializers.ModelSerializer,), {"Meta": MetaClass})


def construct_field(field):
    if field.type == DynamicModelField.DynamicModelFieldType.STRING:
        return models.TextField(null=field.allow_null, blank=field.allow_blank)
    if field.type == DynamicModelField.DynamicModelFieldType.NUMBER:
        return models.FloatField(null=field.allow_null, blank=field.allow_blank)
    if field.type == DynamicModelField.DynamicModelFieldType.BOOLEAN:
        return models.BooleanField(null=field.allow_null, blank=field.allow_blank)
