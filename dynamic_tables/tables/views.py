from django.db import connection, transaction
from rest_framework import mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from tables.constants import ActionTypeE
from tables.helpers import construct_dynamic_model, construct_dynamic_serializer, construct_field
from tables.models import DynamicModel, DynamicModelField
from tables.serializers import (
    DynamicModelFieldAlterationSerializer,
    DynamicModelFieldSerializer,
    DynamicModelSerializer,
)


class DynamicModelView(mixins.CreateModelMixin, GenericViewSet):
    serializer_class = DynamicModelSerializer
    queryset = DynamicModel.objects.all()

    @transaction.atomic()
    def perform_create(self, serializer):
        instance = serializer.save()
        Dynamic = construct_dynamic_model(instance)
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(Dynamic)

    @action(methods=["GET"], detail=True, url_path="rows")
    def rows(self, request, *args, **kwargs):
        object = self.get_object()
        Dynamic = construct_dynamic_model(object)
        serializer_class = construct_dynamic_serializer(Dynamic, "__all__")
        serializer = serializer_class(Dynamic.objects.all(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=True, url_path="row")
    def row(self, request, *args, **kwargs):
        object = self.get_object()
        Dynamic = construct_dynamic_model(object)
        serializer_class = construct_dynamic_serializer(Dynamic, "__all__")
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = Dynamic.objects.create(**serializer.validated_data)
        serializer = serializer_class(instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @transaction.atomic()
    @action(methods=["PUT"], detail=True, url_path="edit")
    def edit(self, request, *args, **kwargs):
        object = self.get_object()
        serializer = DynamicModelFieldAlterationSerializer(data=request.data, context={"instance": object})
        serializer.is_valid(raise_exception=True)
        CurrentDynamicModel = construct_dynamic_model(object)
        field_action = serializer.validated_data.pop("action")
        field_pk = serializer.validated_data.pop("id", None)
        field_name = serializer.validated_data.get("name", None)
        try:
            dynamic_model_field = DynamicModelField.objects.get(pk=field_pk)
        except DynamicModelField.DoesNotExist:
            dynamic_model_field = DynamicModelField.objects.create(dynamic_model=object, **serializer.validated_data)
        with connection.schema_editor() as schema_editor:
            if field_action == ActionTypeE.CREATE.value:
                NewDynamic = construct_dynamic_model(object)
                schema_editor.add_field(NewDynamic, NewDynamic._meta.get_field(dynamic_model_field.name))
            elif field_action == ActionTypeE.DELETE.value:
                schema_editor.remove_field(
                    CurrentDynamicModel, CurrentDynamicModel._meta.get_field(dynamic_model_field.name)
                )
                dynamic_model_field.delete()
            elif field_action == ActionTypeE.UPDATE.value:
                current_field_name = dynamic_model_field.name
                for key, value in serializer.validated_data.items():
                    setattr(dynamic_model_field, key, value)
                dynamic_model_field.save()
                NewDynamic = construct_dynamic_model(object)
                schema_editor.alter_field(
                    CurrentDynamicModel,
                    CurrentDynamicModel._meta.get_field(current_field_name),
                    NewDynamic._meta.get_field(field_name if field_name is not None else current_field_name),
                )
        serializer = self.get_serializer(object)
        return Response(serializer.data, status=status.HTTP_200_OK)
