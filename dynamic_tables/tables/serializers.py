from rest_framework import serializers
from tables.constants import ActionTypeE
from tables.models import DynamicModel, DynamicModelField


class DynamicModelFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = DynamicModelField
        fields = ("id", "name", "type", "allow_blank", "allow_null")


class DynamicModelFieldAlterationSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False)
    type = serializers.ChoiceField(choices=DynamicModelField.DynamicModelFieldType.choices, required=False)
    allow_blank = serializers.BooleanField(required=False)
    allow_null = serializers.BooleanField(required=False)
    action = serializers.ChoiceField(required=True, choices=ActionTypeE.choices())

    def validate(self, attrs):
        if (attrs["action"] == ActionTypeE.DELETE.value or attrs["action"] == ActionTypeE.UPDATE.value) and attrs.get(
            "id", None
        ) is None:
            raise serializers.ValidationError("Id is required for update or delete")
        if attrs["action"] == ActionTypeE.CREATE.value and (
            attrs.get("name", None) is None or attrs.get("type", None) is None
        ):
            raise serializers.ValidationError("Name and type is required for create")
        if attrs["action"] == ActionTypeE.CREATE.value and not attrs.get("allow_null", None):
            raise serializers.ValidationError("While adding new columns, allow_null is required to be True")
        if attrs["action"] == ActionTypeE.UPDATE.value and attrs.get("type", None) is not None:
            raise serializers.ValidationError("Type of already existing column cannot be updated")
        return attrs


class DynamicModelSerializer(serializers.ModelSerializer):
    fields = DynamicModelFieldSerializer(many=True)

    class Meta:
        model = DynamicModel
        fields = ("id", "name", "fields")

    def create(self, validated_data):
        fields_data = validated_data.pop("fields", [])
        instance = DynamicModel.objects.create(**validated_data)
        for field_data in fields_data:
            DynamicModelField.objects.create(dynamic_model=instance, **field_data)
        return instance

    def validate(self, attrs):
        names = [field["name"] for field in attrs["fields"]]
        if len(names) != len(set(names)):
            raise serializers.ValidationError("Field names must be unique.")
        return attrs
