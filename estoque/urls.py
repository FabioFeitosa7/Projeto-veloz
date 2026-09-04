from django.urls import path

from estoque import views

app_name = "estoque"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("ingredientes/", views.ingrediente_lista, name="ingrediente_lista"),
    path("ingredientes/novo/", views.ingrediente_novo, name="ingrediente_novo"),
    path(
        "ingredientes/<int:ingrediente_id>/",
        views.ingrediente_detalhe,
        name="ingrediente_detalhe",
    ),
    path(
        "ingredientes/<int:ingrediente_id>/editar/",
        views.ingrediente_editar,
        name="ingrediente_editar",
    ),
    path(
        "ingredientes/<int:ingrediente_id>/desativar/",
        views.ingrediente_desativar,
        name="ingrediente_desativar",
    ),
    path(
        "ingredientes/<int:ingrediente_id>/reativar/",
        views.ingrediente_reativar,
        name="ingrediente_reativar",
    ),
    path(
        "fechamentos/iniciar/",
        views.fechamento_inicio,
        name="fechamento_inicio",
    ),
    path(
        "fechamentos/novo/",
        views.fechamento_novo,
        name="fechamento_novo",
    ),
    path(
        "fechamentos/<int:fechamento_id>/editar/",
        views.fechamento_editar,
        name="fechamento_editar",
    ),
    path(
        "fechamentos/<int:fechamento_id>/revisao/",
        views.fechamento_revisao,
        name="fechamento_revisao",
    ),
    path(
        "fechamentos/<int:fechamento_id>/finalizar/",
        views.fechamento_finalizar,
        name="fechamento_finalizar",
    ),
    path(
        "fechamentos/",
        views.fechamento_historico,
        name="fechamento_historico",
    ),
    path(
        "fechamentos/<int:fechamento_id>/",
        views.fechamento_detalhe,
        name="fechamento_detalhe",
    ),
    path(
        "fechamentos/<int:fechamento_id>/lista.txt",
        views.fechamento_download_txt,
        name="fechamento_download_txt",
    ),
    path(
        "fechamentos/<int:fechamento_id>/lista.csv",
        views.fechamento_download_csv,
        name="fechamento_download_csv",
    ),
]
