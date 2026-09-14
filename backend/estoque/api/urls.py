from django.urls import include, path
from rest_framework.routers import DefaultRouter

from estoque.api.views import (
    DashboardAPIView,
    DownloadListaCsvAPIView,
    DownloadListaTxtAPIView,
    FechamentoViewSet,
    IngredienteViewSet,
)

router = DefaultRouter()
router.register("ingredientes", IngredienteViewSet, basename="ingrediente")
router.register("fechamentos", FechamentoViewSet, basename="fechamento")

urlpatterns = [
    path("dashboard/", DashboardAPIView.as_view(), name="dashboard"),
    path(
        "fechamentos/<int:pk>/lista.txt",
        DownloadListaTxtAPIView.as_view(),
        name="fechamento-lista-txt",
    ),
    path(
        "fechamentos/<int:pk>/lista.csv",
        DownloadListaCsvAPIView.as_view(),
        name="fechamento-lista-csv",
    ),
    path("", include(router.urls)),
]
