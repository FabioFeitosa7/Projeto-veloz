from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from estoque.models import Ingrediente, UnidadeMedida


class Command(BaseCommand):
    help = "Adiciona ingredientes fictícios sem alterar cadastros existentes."

    @transaction.atomic
    def handle(self, *args, **options):
        hoje = timezone.localdate()
        exemplos = (
            ("Açúcar", UnidadeMedida.QUILOGRAMA, "18", "7.5", 90),
            ("Alho", UnidadeMedida.QUILOGRAMA, "4.5", "1.2", 15),
            ("Carne bovina", UnidadeMedida.QUILOGRAMA, "35", "8.5", 2),
            ("Cebola", UnidadeMedida.QUILOGRAMA, "16", "5.8", 8),
            ("Creme de leite", UnidadeMedida.UNIDADE, "24", "9", 7),
            ("Farinha de trigo", UnidadeMedida.QUILOGRAMA, "30", "10.5", 60),
            ("Filé de frango", UnidadeMedida.QUILOGRAMA, "28", "6", 4),
            ("Leite condensado", UnidadeMedida.UNIDADE, "36", "14", 120),
            ("Manteiga", UnidadeMedida.QUILOGRAMA, "8", "2.5", 0),
            ("Molho de tomate", UnidadeMedida.UNIDADE, "40", "18", 45),
            ("Óleo de cozinha", UnidadeMedida.LITRO, "25", "11", 180),
            ("Ovos", UnidadeMedida.UNIDADE, "120", "43", 6),
            ("Presunto", UnidadeMedida.QUILOGRAMA, "12", "3.5", -1),
            ("Queijo muçarela", UnidadeMedida.QUILOGRAMA, "18", "4.2", 3),
            ("Sal", UnidadeMedida.QUILOGRAMA, "10", "6.3", 365),
            ("Tomate", UnidadeMedida.QUILOGRAMA, "22", "7.8", -5),
        )

        criados = 0
        ignorados = 0
        for nome, unidade, meta, estoque, dias_validade in exemplos:
            _, criado = Ingrediente.objects.get_or_create(
                nome__iexact=nome,
                defaults={
                    "nome": nome,
                    "unidade": unidade,
                    "meta_atual": Decimal(meta),
                    "estoque_atual": Decimal(estoque),
                    "data_validade": hoje + timedelta(days=dias_validade),
                },
            )
            if criado:
                criados += 1
            else:
                ignorados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{criados} ingredientes adicionados; "
                f"{ignorados} já existiam e foram preservados."
            )
        )
