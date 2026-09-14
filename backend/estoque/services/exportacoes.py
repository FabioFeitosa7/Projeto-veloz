import csv
import io
from dataclasses import dataclass
from decimal import Decimal

from estoque.models import FechamentoMensal, StatusFechamento
from estoque.services.calculos import formatar_item_compra, formatar_quantidade


class ErroExportacao(ValueError):
    """Indica que um fechamento não está disponível para exportação."""


@dataclass(frozen=True, slots=True)
class ItemListaCompra:
    ingrediente: str
    quantidade: Decimal
    unidade: str
    unidade_exibicao: str
    linha: str


def obter_itens_compra(fechamento: FechamentoMensal) -> list[ItemListaCompra]:
    """Retorna a lista finalizada, positiva e ordenada pelo nome registrado."""
    fechamento.refresh_from_db(fields=("status",))
    if fechamento.status != StatusFechamento.FINALIZADO:
        raise ErroExportacao(
            "Revise e finalize o fechamento antes de gerar a lista de compras."
        )

    itens = []
    for item in fechamento.itens.filter(quantidade_compra__gt=0):
        linha = formatar_item_compra(
            ingrediente=item.nome_registrado,
            quantidade=item.quantidade_compra,
            unidade=item.unidade_registrada,
        )
        itens.append(
            ItemListaCompra(
                ingrediente=item.nome_registrado,
                quantidade=item.quantidade_compra,
                unidade=item.unidade_registrada,
                unidade_exibicao=item.get_unidade_registrada_display(),
                linha=linha,
            )
        )
    return itens


def gerar_txt(fechamento: FechamentoMensal) -> str:
    itens = obter_itens_compra(fechamento)
    linhas = [f"Lista de compras — {fechamento.referencia:%m/%Y}", ""]
    linhas.extend(item.linha for item in itens)
    if not itens:
        linhas.append("Nenhum item precisa ser comprado")
    return "\n".join(linhas) + "\n"


def gerar_csv(fechamento: FechamentoMensal) -> str:
    itens = obter_itens_compra(fechamento)
    arquivo = io.StringIO(newline="")
    escritor = csv.writer(arquivo)
    escritor.writerow(("ingrediente", "quantidade", "unidade"))
    for item in itens:
        escritor.writerow(
            (
                item.ingrediente,
                formatar_quantidade(item.quantidade),
                item.unidade_exibicao,
            )
        )
    if not itens:
        escritor.writerow(("Nenhum item precisa ser comprado", "", ""))
    return arquivo.getvalue()
