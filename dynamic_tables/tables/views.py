from django.db import connection, transaction
from drf_yasg.utils import no_body, swagger_auto_schema
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

    @swagger_auto_schema(
        tags=["Tables"],
        operation_summary="Create a new dynamic model instance.",
        responses={
            201: DynamicModelSerializer,
            400: "Bad Request: Indicates one of the following issues: invalid input data, missing required fields, or other client-side errors.",
        },
    )
    def create(self, request, *args, **kwargs):
        """
        Create a new dynamic model instance.

        This endpoint creates a new instance of the dynamic model based on the
        provided data in the request body.

        Returns serialized data of the created dynamic model instance with status 201.
        """
        return super().create(request, *args, **kwargs)

    @transaction.atomic()
    def perform_create(self, serializer):
        instance = serializer.save()
        Dynamic = construct_dynamic_model(instance)
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(Dynamic)

    @swagger_auto_schema(
        tags=["Tables"],
        operation_summary="Retrieve rows for a dynamic model.",
        responses={200: "List of rows for the dynamic model."},
    )
    @action(methods=["GET"], detail=True, url_path="rows")
    def rows(self, request, *args, **kwargs):
        """
        Endpoint to retrieve rows for a dynamic model associated with this instance.

        This endpoint dynamically constructs a model and serializer based on the
        current instance's fields and serves all rows of that dynamic model.

        Returns a response with status 200 and a JSON array containing serialized rows.
        """
        object = self.get_object()
        Dynamic = construct_dynamic_model(object)
        serializer_class = construct_dynamic_serializer(Dynamic, "__all__")
        serializer = serializer_class(Dynamic.objects.all(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Tables"],
        operation_summary="Create a row for a dynamic model.",
        request_body=no_body,
        responses={
            201: "Serialized data of the created row.",
            400: "Bad Request: Indicates one of the following issues: invalid input data, missing required fields, or other client-side errors.",
        },
    )
    @action(methods=["POST"], detail=True, url_path="row")
    def row(self, request, *args, **kwargs):
        """
        Endpoint to create a row in a dynamic model associated with this instance.

        This endpoint dynamically constructs a model and serializer based on the
        current instance's fields and creates a new row using the provided data.

        Returns a response with status 201 and the serialized data of the created row.
        """
        object = self.get_object()
        Dynamic = construct_dynamic_model(object)
        serializer_class = construct_dynamic_serializer(Dynamic, "__all__")
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = Dynamic.objects.create(**serializer.validated_data)
        serializer = serializer_class(instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @transaction.atomic()
    @swagger_auto_schema(
        tags=["Tables"],
        responses={
            200: "Serialized data of the updated dynamic model instance.",
            400: "Bad Request: Indicates one of the following issues: invalid input data, missing required fields, or other client-side errors.",
        },
        operation_summary="Edit dynamic model field.",
        request_body=DynamicModelFieldAlterationSerializer(),
    )
    @action(methods=["PUT"], detail=False, url_path=r"(?P<pk>[^/.]+)")
    def edit(self, request, *args, **kwargs):
        """
        Endpoint to edit a field in a dynamic model associated with this instance.

        This endpoint allows editing of fields in the dynamic model based on the
        provided data in the request body.

        Returns a response with status 200 and the serialized data of the updated dynamic model instance.
        """
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
            else:
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
