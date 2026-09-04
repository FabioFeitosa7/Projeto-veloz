from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from estoque.forms import (
    FechamentoMensalForm,
    IngredienteForm,
    ItemFechamentoFormSet,
)
from estoque.models import FechamentoMensal, Ingrediente, StatusFechamento
from estoque.services.calculos import SituacaoValidade, resumir_validade
from estoque.services.fechamentos import (
    ErroFechamento,
    calcular_revisao,
    criar_rascunho,
    finalizar_fechamento,
)
from estoque.services.exportacoes import (
    ErroExportacao,
    gerar_csv,
    gerar_txt,
    obter_itens_compra,
)


def _adicionar_resumo_validade(ingredientes, data_referencia):
    ingredientes = list(ingredientes)
    for ingrediente in ingredientes:
        ingrediente.resumo_validade = resumir_validade(
            ingrediente.data_validade,
            data_referencia,
        )
        percentual = ingrediente.estoque_atual / ingrediente.meta_atual * 100
        ingrediente.percentual_estoque = min(max(percentual, 0), 100)
    return ingredientes


def dashboard(request: HttpRequest) -> HttpResponse:
    hoje = timezone.localdate()
    ingredientes = _adicionar_resumo_validade(
        Ingrediente.objects.filter(ativo=True),
        hoje,
    )
    alertas = [
        ingrediente
        for ingrediente in ingredientes
        if ingrediente.resumo_validade.situacao
        != SituacaoValidade.DENTRO_DA_VALIDADE
    ]
    alertas.sort(key=lambda ingrediente: ingrediente.data_validade)

    proximos = {
        SituacaoValidade.PROXIMO_DO_VENCIMENTO,
        SituacaoValidade.VENCE_HOJE,
    }
    contexto = {
        "hoje": hoje,
        "ingredientes": ingredientes,
        "alertas": alertas,
        "total_ingredientes": len(ingredientes),
        "total_proximos": sum(
            ingrediente.resumo_validade.situacao in proximos
            for ingrediente in ingredientes
        ),
        "total_vencidos": sum(
            ingrediente.resumo_validade.situacao == SituacaoValidade.VENCIDO
            for ingrediente in ingredientes
        ),
    }
    return render(request, "estoque/dashboard.html", contexto)


def ingrediente_lista(request: HttpRequest) -> HttpResponse:
    busca = request.GET.get("q", "").strip()
    situacao = request.GET.get("situacao", "ativos")
    ingredientes = Ingrediente.objects.all()

    if situacao == "inativos":
        ingredientes = ingredientes.filter(ativo=False)
    elif situacao == "todos":
        pass
    else:
        situacao = "ativos"
        ingredientes = ingredientes.filter(ativo=True)

    if busca:
        ingredientes = ingredientes.filter(Q(nome__icontains=busca))

    contexto = {
        "ingredientes": _adicionar_resumo_validade(
            ingredientes,
            timezone.localdate(),
        ),
        "busca": busca,
        "situacao": situacao,
    }
    return render(request, "estoque/ingrediente_lista.html", contexto)


def ingrediente_detalhe(
    request: HttpRequest,
    ingrediente_id: int,
) -> HttpResponse:
    ingrediente = get_object_or_404(Ingrediente, pk=ingrediente_id)
    ingrediente.resumo_validade = resumir_validade(
        ingrediente.data_validade,
        timezone.localdate(),
    )
    return render(
        request,
        "estoque/ingrediente_detalhe.html",
        {"ingrediente": ingrediente},
    )


def ingrediente_novo(request: HttpRequest) -> HttpResponse:
    formulario = IngredienteForm(request.POST or None)
    if request.method == "POST" and formulario.is_valid():
        ingrediente = formulario.save()
        messages.success(request, "Ingrediente cadastrado com sucesso.")
        return redirect("estoque:ingrediente_detalhe", ingrediente_id=ingrediente.pk)

    return render(
        request,
        "estoque/ingrediente_form.html",
        {"formulario": formulario, "titulo": "Novo ingrediente"},
    )


def ingrediente_editar(
    request: HttpRequest,
    ingrediente_id: int,
) -> HttpResponse:
    ingrediente = get_object_or_404(Ingrediente, pk=ingrediente_id)
    formulario = IngredienteForm(request.POST or None, instance=ingrediente)
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        messages.success(request, "Ingrediente atualizado com sucesso.")
        return redirect("estoque:ingrediente_detalhe", ingrediente_id=ingrediente.pk)

    return render(
        request,
        "estoque/ingrediente_form.html",
        {
            "formulario": formulario,
            "ingrediente": ingrediente,
            "titulo": "Editar ingrediente",
        },
    )


@require_POST
def ingrediente_desativar(
    request: HttpRequest,
    ingrediente_id: int,
) -> HttpResponse:
    ingrediente = get_object_or_404(Ingrediente, pk=ingrediente_id)
    if ingrediente.ativo:
        ingrediente.ativo = False
        ingrediente.save(update_fields=("ativo", "atualizado_em"))
        messages.success(request, "Ingrediente desativado com sucesso.")
    else:
        messages.info(request, "O ingrediente já estava desativado.")
    return redirect("estoque:ingrediente_detalhe", ingrediente_id=ingrediente.pk)


@require_POST
def ingrediente_reativar(
    request: HttpRequest,
    ingrediente_id: int,
) -> HttpResponse:
    ingrediente = get_object_or_404(Ingrediente, pk=ingrediente_id)
    if not ingrediente.ativo:
        ingrediente.ativo = True
        ingrediente.save(update_fields=("ativo", "atualizado_em"))
        messages.success(request, "Ingrediente reativado com sucesso.")
    else:
        messages.info(request, "O ingrediente já estava ativo.")
    return redirect("estoque:ingrediente_detalhe", ingrediente_id=ingrediente.pk)


def fechamento_inicio(request: HttpRequest) -> HttpResponse:
    rascunho = (
        FechamentoMensal.objects.filter(status=StatusFechamento.RASCUNHO)
        .order_by("-referencia")
        .first()
    )
    if rascunho:
        return redirect("estoque:fechamento_editar", fechamento_id=rascunho.pk)
    return redirect("estoque:fechamento_novo")


def fechamento_novo(request: HttpRequest) -> HttpResponse:
    hoje = timezone.localdate()
    referencia_inicial = hoje.replace(day=1)
    formulario = FechamentoMensalForm(
        request.POST or None,
        initial={"referencia": referencia_inicial},
    )

    if request.method == "POST" and formulario.is_valid():
        try:
            fechamento = criar_rascunho(formulario.cleaned_data["referencia"])
        except ErroFechamento as erro:
            formulario.add_error(None, str(erro))
        else:
            messages.success(
                request,
                "Fechamento criado. Preencha os dados e salve o rascunho.",
            )
            return redirect(
                "estoque:fechamento_editar",
                fechamento_id=fechamento.pk,
            )

    return render(
        request,
        "estoque/fechamento_novo.html",
        {"formulario": formulario},
    )


def fechamento_editar(
    request: HttpRequest,
    fechamento_id: int,
) -> HttpResponse:
    fechamento = get_object_or_404(FechamentoMensal, pk=fechamento_id)
    if fechamento.status != StatusFechamento.RASCUNHO:
        return HttpResponseForbidden(
            "Um fechamento finalizado não pode ser editado."
        )

    itens = fechamento.itens.select_related("ingrediente").all()
    deseja_revisar = request.method == "POST" and request.POST.get("acao") == "revisar"
    formulario = ItemFechamentoFormSet(
        request.POST or None,
        queryset=itens,
        prefix="itens",
        form_kwargs={"exigir_preenchimento": deseja_revisar},
    )
    if request.method == "POST" and formulario.is_valid():
        formulario.save()
        if deseja_revisar:
            return redirect(
                "estoque:fechamento_revisao",
                fechamento_id=fechamento.pk,
            )
        messages.success(
            request,
            "Fechamento salvo como rascunho. Nenhuma meta foi alterada.",
        )
        return redirect(
            "estoque:fechamento_editar",
            fechamento_id=fechamento.pk,
        )

    preenchidos = fechamento.itens.filter(
        consumo_mensal__isnull=False,
        estoque_restante__isnull=False,
        validade_registrada__isnull=False,
    ).count()
    contexto = {
        "fechamento": fechamento,
        "formulario": formulario,
        "preenchidos": preenchidos,
        "total_itens": fechamento.itens.count(),
    }
    return render(request, "estoque/fechamento_form.html", contexto)


def fechamento_revisao(
    request: HttpRequest,
    fechamento_id: int,
) -> HttpResponse:
    fechamento = get_object_or_404(FechamentoMensal, pk=fechamento_id)
    if fechamento.status != StatusFechamento.RASCUNHO:
        return HttpResponseForbidden("Este fechamento já foi finalizado.")
    try:
        revisao = calcular_revisao(fechamento)
    except ErroFechamento as erro:
        messages.error(request, str(erro))
        return redirect("estoque:fechamento_editar", fechamento_id=fechamento.pk)

    return render(
        request,
        "estoque/fechamento_revisao.html",
        {
            "fechamento": fechamento,
            "revisao": revisao,
            "compras": [item for item in revisao if item.linha_compra],
        },
    )


@require_POST
def fechamento_finalizar(
    request: HttpRequest,
    fechamento_id: int,
) -> HttpResponse:
    try:
        finalizar_fechamento(fechamento_id)
    except FechamentoMensal.DoesNotExist:
        return HttpResponse(status=404)
    except ErroFechamento as erro:
        messages.error(request, str(erro))
        return redirect("estoque:fechamento_editar", fechamento_id=fechamento_id)

    messages.success(request, "Fechamento finalizado e estoque atualizado.")
    return redirect("estoque:fechamento_detalhe", fechamento_id=fechamento_id)


def fechamento_historico(request: HttpRequest) -> HttpResponse:
    fechamentos = FechamentoMensal.objects.annotate(
        total_itens=Count("itens"),
        total_compras=Count(
            "itens",
            filter=Q(itens__quantidade_compra__gt=0),
        ),
    )
    return render(
        request,
        "estoque/fechamento_historico.html",
        {"fechamentos": fechamentos},
    )


def fechamento_detalhe(
    request: HttpRequest,
    fechamento_id: int,
) -> HttpResponse:
    fechamento = get_object_or_404(FechamentoMensal, pk=fechamento_id)
    itens = fechamento.itens.all()
    compras = []
    if fechamento.status == StatusFechamento.FINALIZADO:
        compras = obter_itens_compra(fechamento)
    return render(
        request,
        "estoque/fechamento_detalhe.html",
        {"fechamento": fechamento, "itens": itens, "compras": compras},
    )


def _resposta_download(fechamento, conteudo, extensao, content_type):
    nome = f"lista-compras-{fechamento.referencia:%Y-%m}.{extensao}"
    resposta = HttpResponse(conteudo, content_type=content_type)
    resposta["Content-Disposition"] = f'attachment; filename="{nome}"'
    return resposta


def fechamento_download_txt(
    request: HttpRequest,
    fechamento_id: int,
) -> HttpResponse:
    fechamento = get_object_or_404(FechamentoMensal, pk=fechamento_id)
    try:
        conteudo = gerar_txt(fechamento)
    except ErroExportacao as erro:
        return HttpResponseForbidden(str(erro))
    return _resposta_download(
        fechamento,
        conteudo,
        "txt",
        "text/plain; charset=utf-8",
    )


def fechamento_download_csv(
    request: HttpRequest,
    fechamento_id: int,
) -> HttpResponse:
    fechamento = get_object_or_404(FechamentoMensal, pk=fechamento_id)
    try:
        conteudo = gerar_csv(fechamento)
    except ErroExportacao as erro:
        return HttpResponseForbidden(str(erro))
    return _resposta_download(
        fechamento,
        "\ufeff" + conteudo,
        "csv",
        "text/csv; charset=utf-8",
    )
