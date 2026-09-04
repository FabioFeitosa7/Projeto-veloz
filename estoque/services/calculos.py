from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_CEILING
from enum import Enum


MARGEM_SEGURANCA = Decimal("1.20")
ZERO = Decimal("0")
UNIDADES_VALIDAS = {"KG", "L", "UN"}
ROTULOS_UNIDADE = {
    "KG": "Kg",
    "L": "Litros",
    "UN": "Unidades",
}


class ErroRegraNegocio(ValueError):
    """Indica que os dados não podem produzir um cálculo válido."""


class SituacaoValidade(str, Enum):
    DENTRO_DA_VALIDADE = "dentro_da_validade"
    PROXIMO_DO_VENCIMENTO = "proximo_do_vencimento"
    VENCE_HOJE = "vence_hoje"
    VENCIDO = "vencido"


class MotivoReposicao(str, Enum):
    NORMAL = "normal"
    FALTA = "falta"
    VENCIMENTO = "vencimento"
    FALTA_E_VENCIMENTO = "falta_e_vencimento"


@dataclass(frozen=True, slots=True)
class ResultadoReposicao:
    situacao_validade: SituacaoValidade
    motivo: MotivoReposicao
    estoque_aproveitavel: Decimal
    meta_resultante: Decimal
    quantidade_calculada: Decimal
    quantidade_compra: Decimal


@dataclass(frozen=True, slots=True)
class ResumoValidade:
    situacao: SituacaoValidade
    dias_restantes: int
    descricao: str


def _decimal(valor: Decimal | int | str, nome: str) -> Decimal:
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError) as erro:
        raise ErroRegraNegocio(f"{nome} deve ser um número válido.") from erro

    if not numero.is_finite():
        raise ErroRegraNegocio(f"{nome} deve ser um número finito.")
    return numero


def _validar_quantidade(numero: Decimal, nome: str) -> None:
    if numero < ZERO:
        raise ErroRegraNegocio(f"{nome} não pode ser negativo.")


def _eh_inteiro(numero: Decimal) -> bool:
    return numero == numero.to_integral_value()


def classificar_validade(
    data_validade: date,
    data_apuracao: date,
) -> SituacaoValidade:
    """Classifica a validade usando a data em que o fechamento é finalizado."""
    dias_restantes = (data_validade - data_apuracao).days

    if dias_restantes < 0:
        return SituacaoValidade.VENCIDO
    if dias_restantes == 0:
        return SituacaoValidade.VENCE_HOJE
    if dias_restantes <= 7:
        return SituacaoValidade.PROXIMO_DO_VENCIMENTO
    return SituacaoValidade.DENTRO_DA_VALIDADE


def resumir_validade(
    data_validade: date,
    data_referencia: date,
) -> ResumoValidade:
    """Retorna a classificação e um texto acessível sobre a validade."""
    dias_restantes = (data_validade - data_referencia).days
    situacao = classificar_validade(data_validade, data_referencia)

    if situacao == SituacaoValidade.VENCIDO:
        dias_vencido = abs(dias_restantes)
        sufixo = "dia" if dias_vencido == 1 else "dias"
        descricao = f"Vencido há {dias_vencido} {sufixo}"
    elif situacao == SituacaoValidade.VENCE_HOJE:
        descricao = "Vence hoje"
    elif situacao == SituacaoValidade.PROXIMO_DO_VENCIMENTO:
        sufixo = "dia" if dias_restantes == 1 else "dias"
        descricao = f"Vence em {dias_restantes} {sufixo}"
    else:
        descricao = "Dentro da validade"

    return ResumoValidade(
        situacao=situacao,
        dias_restantes=dias_restantes,
        descricao=descricao,
    )


def calcular_reposicao(
    *,
    meta_atual: Decimal | int | str,
    consumo_mensal: Decimal | int | str,
    estoque_restante: Decimal | int | str,
    unidade: str,
    data_validade: date,
    data_apuracao: date,
    houve_falta: bool,
) -> ResultadoReposicao:
    """Calcula a meta e a compra de um ingrediente no fechamento mensal."""
    unidade_normalizada = unidade.strip().upper()
    if unidade_normalizada not in UNIDADES_VALIDAS:
        raise ErroRegraNegocio("Unidade de medida inválida.")

    meta = _decimal(meta_atual, "Meta atual")
    consumo = _decimal(consumo_mensal, "Consumo mensal")
    estoque = _decimal(estoque_restante, "Estoque restante")

    if meta <= ZERO:
        raise ErroRegraNegocio("Meta atual deve ser maior que zero.")
    _validar_quantidade(consumo, "Consumo mensal")
    _validar_quantidade(estoque, "Estoque restante")

    if unidade_normalizada == "UN":
        quantidades = (
            (meta, "Meta atual"),
            (consumo, "Consumo mensal"),
            (estoque, "Estoque restante"),
        )
        for quantidade, nome in quantidades:
            if not _eh_inteiro(quantidade):
                raise ErroRegraNegocio(f"{nome} deve ser inteiro para unidades.")

    if houve_falta and estoque != ZERO:
        raise ErroRegraNegocio(
            "Estoque restante deve ser zero quando houve falta antecipada."
        )

    situacao = classificar_validade(data_validade, data_apuracao)
    estava_vencido = situacao == SituacaoValidade.VENCIDO

    meta_resultante = consumo * MARGEM_SEGURANCA if houve_falta else meta
    if unidade_normalizada == "UN":
        meta_resultante = meta_resultante.quantize(Decimal("1"), rounding=ROUND_CEILING)

    estoque_aproveitavel = ZERO if estava_vencido else estoque
    quantidade_calculada = meta_resultante - estoque_aproveitavel
    quantidade_compra = max(quantidade_calculada, ZERO)

    if unidade_normalizada == "UN":
        quantidade_compra = quantidade_compra.quantize(
            Decimal("1"),
            rounding=ROUND_CEILING,
        )

    if houve_falta and estava_vencido:
        motivo = MotivoReposicao.FALTA_E_VENCIMENTO
    elif houve_falta:
        motivo = MotivoReposicao.FALTA
    elif estava_vencido:
        motivo = MotivoReposicao.VENCIMENTO
    else:
        motivo = MotivoReposicao.NORMAL

    return ResultadoReposicao(
        situacao_validade=situacao,
        motivo=motivo,
        estoque_aproveitavel=estoque_aproveitavel,
        meta_resultante=meta_resultante,
        quantidade_calculada=quantidade_calculada,
        quantidade_compra=quantidade_compra,
    )


def formatar_quantidade(quantidade: Decimal | int | str) -> str:
    """Formata decimal sem zeros desnecessários e com vírgula para exibição."""
    numero = _decimal(quantidade, "Quantidade")
    texto = format(numero, "f")

    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def formatar_item_compra(
    *,
    ingrediente: str,
    quantidade: Decimal | int | str,
    unidade: str,
) -> str | None:
    """Produz a linha exigida no desafio ou omite compras não positivas."""
    numero = _decimal(quantidade, "Quantidade")
    if numero <= ZERO:
        return None

    unidade_normalizada = unidade.strip().upper()
    try:
        rotulo = ROTULOS_UNIDADE[unidade_normalizada]
    except KeyError as erro:
        raise ErroRegraNegocio("Unidade de medida inválida.") from erro

    return f"Comprar: {formatar_quantidade(numero)} {rotulo} de {ingrediente.strip()}"
