from django.core.validators import RegexValidator
from django.db import models


class DynamicModel(models.Model):
    name = models.CharField(
        max_length=32,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^[a-zA-Z]+$",
                message="Only letters are allowed.",
            )
        ],
    )

    def __str__(self):
        return f"{self.name}"


class DynamicModelField(models.Model):
    class DynamicModelFieldType(models.TextChoices):
        STRING = "string", "String"
        BOOLEAN = "boolean", "Boolean"
        NUMBER = "number", "Number"

    class Meta:
        constraints = [models.UniqueConstraint(fields=["dynamic_model", "name"], name="unique_dynamic_model_name")]

    dynamic_model = models.ForeignKey(DynamicModel, on_delete=models.CASCADE, related_name="fields", default=None)
    name = models.CharField(max_length=32)
    type = models.CharField(max_length=32, choices=DynamicModelFieldType.choices)
    allow_blank = models.BooleanField(default=True)
    allow_null = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.dynamic_model.name} - {self.name} - {self.type}"
