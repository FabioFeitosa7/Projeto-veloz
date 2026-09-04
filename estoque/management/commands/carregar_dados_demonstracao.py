from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from estoque.models import FechamentoMensal, Ingrediente, UnidadeMedida
from estoque.services.fechamentos import criar_rascunho, finalizar_fechamento


class Command(BaseCommand):
    help = "Cria ingredientes e um fechamento fictício em um banco vazio."

    @transaction.atomic
    def handle(self, *args, **options):
        if Ingrediente.objects.exists() or FechamentoMensal.objects.exists():
            raise CommandError(
                "Os dados de demonstração só podem ser criados em um banco vazio."
            )

        hoje = timezone.localdate()
        referencia = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)
        dados = (
            {
                "nome": "Arroz",
                "unidade": UnidadeMedida.QUILOGRAMA,
                "meta": "30",
                "estoque": "30",
                "validade": hoje + timedelta(days=45),
                "consumo": "25",
                "restante": "30",
                "falta": False,
            },
            {
                "nome": "Farinha",
                "unidade": UnidadeMedida.QUILOGRAMA,
                "meta": "20",
                "estoque": "6",
                "validade": hoje + timedelta(days=30),
                "consumo": "18",
                "restante": "6",
                "falta": False,
            },
            {
                "nome": "Leite",
                "unidade": UnidadeMedida.LITRO,
                "meta": "20",
                "estoque": "5",
                "validade": hoje - timedelta(days=1),
                "consumo": "15",
                "restante": "5",
                "falta": False,
            },
            {
                "nome": "Ovos",
                "unidade": UnidadeMedida.UNIDADE,
                "meta": "43",
                "estoque": "0",
                "validade": hoje + timedelta(days=6),
                "consumo": "43",
                "restante": "0",
                "falta": True,
            },
        )

        for dado in dados:
            Ingrediente.objects.create(
                nome=dado["nome"],
                unidade=dado["unidade"],
                meta_atual=Decimal(dado["meta"]),
                estoque_atual=Decimal(dado["estoque"]),
                data_validade=dado["validade"],
            )

        fechamento = criar_rascunho(referencia)
        por_nome = {dado["nome"]: dado for dado in dados}
        for item in fechamento.itens.all():
            dado = por_nome[item.nome_registrado]
            item.consumo_mensal = Decimal(dado["consumo"])
            item.estoque_restante = Decimal(dado["restante"])
            item.validade_registrada = dado["validade"]
            item.houve_falta = dado["falta"]
            item.save()

        finalizar_fechamento(fechamento.pk, data_apuracao=hoje)
        self.stdout.write(
            self.style.SUCCESS(
                "Dados fictícios criados. "
                f"Fechamento disponível em {referencia:%m/%Y}."
            )
        )
