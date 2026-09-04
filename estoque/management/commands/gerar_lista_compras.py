from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from estoque.models import FechamentoMensal, StatusFechamento
from estoque.services.exportacoes import obter_itens_compra


class Command(BaseCommand):
    help = "Imprime a lista de compras de um fechamento mensal finalizado."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mes",
            required=True,
            help="Mês de referência no formato AAAA-MM.",
        )

    def handle(self, *args, **options):
        try:
            referencia = datetime.strptime(options["mes"], "%Y-%m").date()
        except ValueError as erro:
            raise CommandError("Informe o mês no formato AAAA-MM.") from erro

        try:
            fechamento = FechamentoMensal.objects.get(referencia=referencia)
        except FechamentoMensal.DoesNotExist as erro:
            raise CommandError(
                f"Não existe fechamento para {referencia:%m/%Y}."
            ) from erro
        if fechamento.status != StatusFechamento.FINALIZADO:
            raise CommandError(
                f"O fechamento de {referencia:%m/%Y} ainda não foi finalizado."
            )

        itens = obter_itens_compra(fechamento)
        if not itens:
            self.stdout.write("Nenhum item precisa ser comprado")
            return
        for item in itens:
            self.stdout.write(item.linha)
