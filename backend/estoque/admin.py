from django.contrib import admin

from estoque.models import FechamentoMensal, Ingrediente, ItemFechamento


@admin.register(Ingrediente)
class IngredienteAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "unidade",
        "meta_atual",
        "estoque_atual",
        "data_validade",
        "ativo",
    )
    list_filter = ("ativo", "unidade")
    search_fields = ("nome",)
    ordering = ("nome",)


class ItemFechamentoInline(admin.TabularInline):
    model = ItemFechamento
    extra = 0
    show_change_link = True


@admin.register(FechamentoMensal)
class FechamentoMensalAdmin(admin.ModelAdmin):
    list_display = ("referencia", "status", "criado_em", "finalizado_em")
    list_filter = ("status",)
    date_hierarchy = "referencia"
    inlines = (ItemFechamentoInline,)


@admin.register(ItemFechamento)
class ItemFechamentoAdmin(admin.ModelAdmin):
    list_display = (
        "nome_registrado",
        "fechamento",
        "unidade_registrada",
        "houve_falta",
        "estava_vencido",
        "quantidade_compra",
    )
    list_filter = (
        "unidade_registrada",
        "houve_falta",
        "estava_vencido",
    )
    search_fields = ("nome_registrado", "ingrediente__nome")
