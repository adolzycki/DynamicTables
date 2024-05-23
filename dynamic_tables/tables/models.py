from django.db import models


class DynamicModel(models.Model):
    name = models.CharField(max_length=32, unique=True)


class DynamicModelField(models.Model):
    class DynamicModelFieldType(models.TextChoices):
        STRING = "string", "String"
        BOOLEAN = "boolean", "Boolean"
        NUMBER = "number", "Number"

    dynamic_model = models.ForeignKey(DynamicModel, on_delete=models.CASCADE, related_name="fields", default=None)
    name = models.CharField(max_length=32, unique=True)
    type = models.CharField(max_length=32, choices=DynamicModelFieldType.choices)
    allow_blank = models.BooleanField(default=False)
    allow_null = models.BooleanField(default=False)
