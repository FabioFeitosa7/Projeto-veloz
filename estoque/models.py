from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower


class UnidadeMedida(models.TextChoices):
    QUILOGRAMA = "KG", "Kg"
    LITRO = "L", "Litros"
    UNIDADE = "UN", "Unidades"


class StatusFechamento(models.TextChoices):
    RASCUNHO = "RASCUNHO", "Rascunho"
    FINALIZADO = "FINALIZADO", "Finalizado"


def _eh_inteiro(valor: Decimal | None) -> bool:
    return valor is None or valor == valor.to_integral_value()


class Ingrediente(models.Model):
    nome = models.CharField(max_length=120)
    unidade = models.CharField(max_length=2, choices=UnidadeMedida.choices)
    meta_atual = models.DecimalField(max_digits=12, decimal_places=3)
    estoque_atual = models.DecimalField(max_digits=12, decimal_places=3)
    data_validade = models.DateField()
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("nome",)
        constraints = (
            models.UniqueConstraint(
                Lower("nome"),
                name="ingrediente_nome_ci_unico",
            ),
            models.CheckConstraint(
                condition=models.Q(meta_atual__gt=0),
                name="ingrediente_meta_positiva",
            ),
            models.CheckConstraint(
                condition=models.Q(estoque_atual__gte=0),
                name="ingrediente_estoque_nao_negativo",
            ),
        )

    def __str__(self) -> str:
        return self.nome

    def clean(self) -> None:
        super().clean()
        self.nome = " ".join(self.nome.split())

        erros = {}
        if not self.nome:
            erros["nome"] = "Informe o nome do ingrediente."
        if self.unidade == UnidadeMedida.UNIDADE:
            if not _eh_inteiro(self.meta_atual):
                erros["meta_atual"] = "A meta deve ser inteira para unidades."
            if not _eh_inteiro(self.estoque_atual):
                erros["estoque_atual"] = (
                    "O estoque deve ser inteiro para unidades."
                )
        if self.pk and self.itens_fechamento.exists():
            unidade_original = (
                type(self).objects.filter(pk=self.pk)
                .values_list("unidade", flat=True)
                .first()
            )
            if unidade_original and unidade_original != self.unidade:
                erros["unidade"] = (
                    "A unidade não pode ser alterada após existir histórico."
                )
        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs) -> None:
        self.nome = " ".join(self.nome.split())
        super().save(*args, **kwargs)


class FechamentoMensal(models.Model):
    referencia = models.DateField(unique=True)
    status = models.CharField(
        max_length=10,
        choices=StatusFechamento.choices,
        default=StatusFechamento.RASCUNHO,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    finalizado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-referencia",)
        constraints = (
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status=StatusFechamento.RASCUNHO,
                        finalizado_em__isnull=True,
                    )
                    | models.Q(
                        status=StatusFechamento.FINALIZADO,
                        finalizado_em__isnull=False,
                    )
                ),
                name="fechamento_status_data_coerentes",
            ),
        )

    def __str__(self) -> str:
        return self.referencia.strftime("%m/%Y")

    def clean(self) -> None:
        super().clean()
        if self.referencia:
            self.referencia = self.referencia.replace(day=1)

        if self.status == StatusFechamento.RASCUNHO and self.finalizado_em:
            raise ValidationError(
                {"finalizado_em": "Um rascunho não pode ter data de finalização."}
            )
        if self.status == StatusFechamento.FINALIZADO and not self.finalizado_em:
            raise ValidationError(
                {"finalizado_em": "Informe quando o fechamento foi finalizado."}
            )

    def save(self, *args, **kwargs) -> None:
        if self.referencia:
            self.referencia = self.referencia.replace(day=1)
        super().save(*args, **kwargs)


class ItemFechamento(models.Model):
    fechamento = models.ForeignKey(
        FechamentoMensal,
        on_delete=models.CASCADE,
        related_name="itens",
    )
    ingrediente = models.ForeignKey(
        Ingrediente,
        on_delete=models.PROTECT,
        related_name="itens_fechamento",
    )
    nome_registrado = models.CharField(max_length=120)
    unidade_registrada = models.CharField(
        max_length=2,
        choices=UnidadeMedida.choices,
    )
    meta_anterior = models.DecimalField(max_digits=12, decimal_places=3)
    consumo_mensal = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )
    estoque_restante = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )
    validade_registrada = models.DateField(null=True, blank=True)
    houve_falta = models.BooleanField(default=False)
    estava_vencido = models.BooleanField(null=True, blank=True)
    estoque_aproveitavel = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )
    meta_resultante = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )
    quantidade_compra = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("nome_registrado",)
        constraints = (
            models.UniqueConstraint(
                fields=("fechamento", "ingrediente"),
                name="item_unico_por_fechamento",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(consumo_mensal__isnull=True)
                    | models.Q(consumo_mensal__gte=0)
                ),
                name="item_consumo_nao_negativo",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(estoque_restante__isnull=True)
                    | models.Q(estoque_restante__gte=0)
                ),
                name="item_estoque_nao_negativo",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(quantidade_compra__isnull=True)
                    | models.Q(quantidade_compra__gte=0)
                ),
                name="item_compra_nao_negativa",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(houve_falta=False)
                    | models.Q(estoque_restante=0)
                ),
                name="item_falta_exige_estoque_zero",
            ),
        )

    def __str__(self) -> str:
        return f"{self.nome_registrado} — {self.fechamento}"

    def clean(self) -> None:
        super().clean()
        self.nome_registrado = " ".join(self.nome_registrado.split())
        erros = {}

        if self.houve_falta and self.estoque_restante != Decimal("0"):
            erros["estoque_restante"] = (
                "O estoque deve ser zero quando houve falta antecipada."
            )

        if self.unidade_registrada == UnidadeMedida.UNIDADE:
            campos = {
                "meta_anterior": self.meta_anterior,
                "consumo_mensal": self.consumo_mensal,
                "estoque_restante": self.estoque_restante,
                "estoque_aproveitavel": self.estoque_aproveitavel,
                "meta_resultante": self.meta_resultante,
                "quantidade_compra": self.quantidade_compra,
            }
            for campo, valor in campos.items():
                if not _eh_inteiro(valor):
                    erros[campo] = "O valor deve ser inteiro para unidades."

        if self.estava_vencido and self.estoque_aproveitavel not in {
            None,
            Decimal("0"),
        }:
            erros["estoque_aproveitavel"] = (
                "O estoque aproveitável de um item vencido deve ser zero."
            )

        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs) -> None:
        self.nome_registrado = " ".join(self.nome_registrado.split())
        super().save(*args, **kwargs)
