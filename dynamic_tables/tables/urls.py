from rest_framework.routers import DefaultRouter

from tables import views

router = DefaultRouter()
router.register(r"table", views.DynamicModelView, basename="table")

urlpatterns = router.urls