from django.contrib import admin
from tables.models import DynamicModel, DynamicModelField


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # Disable add permission
        return False

    def has_change_permission(self, request, obj=None):
        # Allow viewing but not modifying
        return False if obj else True

    def has_delete_permission(self, request, obj=None):
        # Disable delete permission
        return False


@admin.register(DynamicModel)
class DynamicModelAdmin(ReadOnlyAdmin):
    list_display = (
        "id",
        "name",
    )


@admin.register(DynamicModelField)
class DynamicModelFieldAdmin(ReadOnlyAdmin):
    list_display = (
        "id",
        "dynamic_model",
        "name",
        "type",
        "allow_blank",
        "allow_null",
    )
