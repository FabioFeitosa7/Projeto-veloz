from dataclasses import dataclass
from datetime import date

from django.db import transaction
from django.utils import timezone

from estoque.models import (
    FechamentoMensal,
    Ingrediente,
    ItemFechamento,
    StatusFechamento,
)
from estoque.services.calculos import (
    MotivoReposicao,
    ResultadoReposicao,
    calcular_reposicao,
    formatar_item_compra,
)


class ErroFechamento(ValueError):
    """Indica que um fechamento não pode ser criado ou alterado."""


@dataclass(frozen=True, slots=True)
class ItemRevisao:
    item: ItemFechamento
    resultado: ResultadoReposicao
    explicacao: str
    linha_compra: str | None


EXPLICACOES = {
    MotivoReposicao.NORMAL: "Reposição pela meta menos o estoque aproveitável.",
    MotivoReposicao.FALTA: (
        "Houve falta: a nova meta considera o consumo acrescido de 20%."
    ),
    MotivoReposicao.VENCIMENTO: (
        "O produto estava vencido: o estoque restante foi desconsiderado."
    ),
    MotivoReposicao.FALTA_E_VENCIMENTO: (
        "Houve falta e vencimento: a meta recebeu 20% e o estoque foi desconsiderado."
    ),
}


@transaction.atomic
def criar_rascunho(referencia: date) -> FechamentoMensal:
    """Cria um fechamento e registra o retrato dos ingredientes ativos."""
    ingredientes = list(Ingrediente.objects.filter(ativo=True))
    if not ingredientes:
        raise ErroFechamento(
            "Cadastre pelo menos um ingrediente ativo antes do fechamento."
        )

    fechamento = FechamentoMensal.objects.create(referencia=referencia)
    ItemFechamento.objects.bulk_create(
        [
            ItemFechamento(
                fechamento=fechamento,
                ingrediente=ingrediente,
                nome_registrado=ingrediente.nome,
                unidade_registrada=ingrediente.unidade,
                meta_anterior=ingrediente.meta_atual,
                validade_registrada=ingrediente.data_validade,
            )
            for ingrediente in ingredientes
        ]
    )
    return fechamento


def calcular_revisao(
    fechamento: FechamentoMensal,
    *,
    data_apuracao: date | None = None,
) -> list[ItemRevisao]:
    """Calcula uma prévia sem persistir resultados ou alterar ingredientes."""
    if fechamento.status != StatusFechamento.RASCUNHO:
        raise ErroFechamento("Apenas um rascunho pode ser revisado.")

    data_apuracao = data_apuracao or timezone.localdate()
    itens = list(fechamento.itens.select_related("ingrediente"))
    if not itens:
        raise ErroFechamento("O fechamento não possui ingredientes.")

    revisao = []
    for item in itens:
        if (
            item.consumo_mensal is None
            or item.estoque_restante is None
            or item.validade_registrada is None
        ):
            raise ErroFechamento(
                f"Preencha todos os dados de {item.nome_registrado} antes de revisar."
            )
        resultado = calcular_reposicao(
            meta_atual=item.meta_anterior,
            consumo_mensal=item.consumo_mensal,
            estoque_restante=item.estoque_restante,
            unidade=item.unidade_registrada,
            data_validade=item.validade_registrada,
            data_apuracao=data_apuracao,
            houve_falta=item.houve_falta,
        )
        revisao.append(
            ItemRevisao(
                item=item,
                resultado=resultado,
                explicacao=EXPLICACOES[resultado.motivo],
                linha_compra=formatar_item_compra(
                    ingrediente=item.nome_registrado,
                    quantidade=resultado.quantidade_compra,
                    unidade=item.unidade_registrada,
                ),
            )
        )
    return revisao


@transaction.atomic
def finalizar_fechamento(
    fechamento_id: int,
    *,
    data_apuracao: date | None = None,
) -> FechamentoMensal:
    """Finaliza uma vez e atualiza itens e ingredientes na mesma transação."""
    fechamento = FechamentoMensal.objects.select_for_update().get(pk=fechamento_id)
    if fechamento.status != StatusFechamento.RASCUNHO:
        raise ErroFechamento("Este fechamento já foi finalizado.")

    revisao = calcular_revisao(
        fechamento,
        data_apuracao=data_apuracao or timezone.localdate(),
    )
    for item_revisao in revisao:
        item = item_revisao.item
        resultado = item_revisao.resultado
        item.estava_vencido = resultado.motivo in {
            MotivoReposicao.VENCIMENTO,
            MotivoReposicao.FALTA_E_VENCIMENTO,
        }
        item.estoque_aproveitavel = resultado.estoque_aproveitavel
        item.meta_resultante = resultado.meta_resultante
        item.quantidade_compra = resultado.quantidade_compra
        item.save(
            update_fields=(
                "estava_vencido",
                "estoque_aproveitavel",
                "meta_resultante",
                "quantidade_compra",
            )
        )

        ingrediente = Ingrediente.objects.select_for_update().get(
            pk=item.ingrediente_id
        )
        ingrediente.meta_atual = resultado.meta_resultante
        ingrediente.estoque_atual = resultado.estoque_aproveitavel
        ingrediente.data_validade = item.validade_registrada
        ingrediente.save(
            update_fields=(
                "meta_atual",
                "estoque_atual",
                "data_validade",
                "atualizado_em",
            )
        )

    fechamento.status = StatusFechamento.FINALIZADO
    fechamento.finalizado_em = timezone.now()
    fechamento.save(update_fields=("status", "finalizado_em", "atualizado_em"))
    return fechamento


@transaction.atomic
def cancelar_fechamento(fechamento_id: int) -> FechamentoMensal:
    """Cancela um rascunho sem apagar o retrato mensal registrado."""
    fechamento = FechamentoMensal.objects.select_for_update().get(pk=fechamento_id)
    if fechamento.status != StatusFechamento.RASCUNHO:
        raise ErroFechamento("Apenas um fechamento em rascunho pode ser cancelado.")

    fechamento.status = StatusFechamento.CANCELADO
    fechamento.cancelado_em = timezone.now()
    fechamento.save(update_fields=("status", "cancelado_em", "atualizado_em"))
    return fechamento
