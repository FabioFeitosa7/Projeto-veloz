from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from estoque.models import FechamentoMensal, Ingrediente, ItemFechamento
from estoque.services.calculos import formatar_item_compra, resumir_validade


class IngredienteSerializer(serializers.ModelSerializer):
    unidade_exibicao = serializers.CharField(
        source="get_unidade_display", read_only=True
    )
    validade = serializers.SerializerMethodField()

    class Meta:
        model = Ingrediente
        fields = (
            "id", "nome", "unidade", "unidade_exibicao", "meta_atual",
            "estoque_atual", "data_validade", "validade", "ativo",
            "criado_em", "atualizado_em",
        )
        read_only_fields = ("id", "ativo", "criado_em", "atualizado_em")

    def get_validade(self, obj):
        from django.utils import timezone

        resumo = resumir_validade(obj.data_validade, timezone.localdate())
        return {
            "situacao": resumo.situacao.value,
            "dias_restantes": resumo.dias_restantes,
            "descricao": resumo.descricao,
        }

    def validate_nome(self, value):
        nome = " ".join(value.split())
        consulta = Ingrediente.objects.filter(nome__iexact=nome)
        if self.instance:
            consulta = consulta.exclude(pk=self.instance.pk)
        if consulta.exists():
            raise serializers.ValidationError(
                "Já existe um ingrediente com este nome."
            )
        return nome

    def validate(self, attrs):
        instancia = self.instance or Ingrediente()
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        try:
            instancia.full_clean(exclude=("ativo",) if not self.instance else ())
        except DjangoValidationError as erro:
            raise serializers.ValidationError(erro.message_dict) from erro
        return attrs


class ItemFechamentoSerializer(serializers.ModelSerializer):
    unidade_exibicao = serializers.CharField(
        source="get_unidade_registrada_display", read_only=True
    )
    linha_compra = serializers.SerializerMethodField()

    class Meta:
        model = ItemFechamento
        fields = (
            "id", "ingrediente", "nome_registrado", "unidade_registrada",
            "unidade_exibicao", "meta_anterior", "consumo_mensal",
            "estoque_restante", "validade_registrada", "houve_falta",
            "estava_vencido", "estoque_aproveitavel", "meta_resultante",
            "quantidade_compra",
            "linha_compra",
        )
        read_only_fields = (
            "id", "ingrediente", "nome_registrado", "unidade_registrada",
            "meta_anterior", "estava_vencido", "estoque_aproveitavel",
            "meta_resultante", "quantidade_compra",
        )

    def get_linha_compra(self, obj):
        if obj.quantidade_compra is None:
            return None
        return formatar_item_compra(
            ingrediente=obj.nome_registrado,
            quantidade=obj.quantidade_compra,
            unidade=obj.unidade_registrada,
        )

    def validate(self, attrs):
        instancia = self.instance
        if instancia is None:
            raise serializers.ValidationError("O item deve pertencer a um fechamento.")
        for campo, valor in attrs.items():
            setattr(instancia, campo, valor)
        try:
            instancia.full_clean()
        except DjangoValidationError as erro:
            raise serializers.ValidationError(erro.message_dict) from erro
        return attrs


class FechamentoSerializer(serializers.ModelSerializer):
    itens = ItemFechamentoSerializer(many=True, read_only=True)
    total_itens = serializers.IntegerField(read_only=True)
    total_compras = serializers.IntegerField(read_only=True)

    class Meta:
        model = FechamentoMensal
        fields = (
            "id", "referencia", "status", "criado_em", "atualizado_em",
            "finalizado_em", "cancelado_em", "itens",
            "total_itens", "total_compras",
        )
        read_only_fields = (
            "id", "status", "criado_em", "atualizado_em", "finalizado_em",
            "cancelado_em",
            "itens",
        )

    def validate_referencia(self, value):
        referencia = value.replace(day=1)
        if FechamentoMensal.objects.filter(referencia=referencia).exclude(
            status="CANCELADO"
        ).exists():
            raise serializers.ValidationError(
                "Já existe um fechamento para este mês."
            )
        return referencia


class DataApuracaoSerializer(serializers.Serializer):
    data_apuracao = serializers.DateField(required=False)
