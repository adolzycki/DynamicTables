from django.db import connection, transaction
from rest_framework import status, mixins, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from tables.helpers import construct_dynamic_model, construct_dynamic_serializer, construct_field
from tables.models import DynamicModel, DynamicModelField
from tables.serializers import (
    DynamicModelSerializer,
    DynamicModelFieldSerializer,
    DynamicModelFieldAlterationSerializer,
)


class DynamicModelView(mixins.CreateModelMixin, GenericViewSet):
    serializer_class = DynamicModelSerializer
    queryset = DynamicModel.objects.all()

    def perform_create(self, serializer):
        instance = serializer.save()
        Dynamic = construct_dynamic_model(instance)
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(Dynamic)

    @action(methods=["GET"], detail=True, url_path="rows")
    def get_data(self, request, *args, **kwargs):
        object = self.get_object()
        Dynamic = construct_dynamic_model(object)
        serializer_class = construct_dynamic_serializer(Dynamic, "__all__")
        serializer = serializer_class(Dynamic.objects.all(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=True, url_path="row")
    def add_data(self, request, *args, **kwargs):
        object = self.get_object()
        Dynamic = construct_dynamic_model(object)
        serializer_class = construct_dynamic_serializer(Dynamic, "__all__")
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = Dynamic.objects.create(**serializer.validated_data)
        serializer = serializer_class(instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # @action(methods=["PUT"], detail=True, url_path="edit")
    # def update_scheme(self, request, *args, **kwargs):
    #     object = self.get_object()
    #     serializer = DynamicModelFieldAlterationSerializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     Dynamic = construct_dynamic_model(object)
    #     field_action = serializer.validated_data.pop('action')
    #     field_pk = serializer.validated_data.get('id', None)
    #     if field_action in ['update', 'delete'] and not object.fields.filter(pk=field_pk).exists():
    #         raise serializers.ValidationError("Field with this id does not exists for this model.")
    #     with connection.schema_editor() as schema_editor:
    #         with transaction.atomic():
    #             if field_action == 'create':
    #                 dynamic_model_field = DynamicModelField.objects.create(dynamic_model=object, **serializer.validated_data)
    #                 schema_editor.add_field(Dynamic, Dynamic._meta.get_field(dynamic_model_field.name))
    #             elif field_action == 'update':
    #                 edited_model_field = DynamicModelField.objects.get(pk=field_pk)
    #                 DynamicModelField.objects.filters(pk=field_pk).update(**serializer.validated_data)
    #                 new_model_field = DynamicModelField.objects.get(pk=field_pk)
    #                 new_object = self.get_object()
    #                 NewDynamic = construct_dynamic_model(new_object)
    #                 schema_editor.alter_field(Dynamic, Dynamic._meta.get_field(edited_model_field.name), NewDynamic._meta.get_field(new_model_field.name))
    #             else:
    #                 dynamic_model_field = DynamicModelField.objects.get(pk=field_pk)
    #                 schema_editor.remove_field(Dynamic, Dynamic._meta.get_field(dynamic_model_field.name))
    #                 DynamicModelField.objects.get(pk=field_pk).delete()
    #
    #     serializer = self.get_serializer(object)
    #     return Response(serializer.data, status=status.HTTP_200_OK)
