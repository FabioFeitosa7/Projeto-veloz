from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from estoque.models import Ingrediente


class AdicionarIngredientesExemploTests(TestCase):
    def test_adiciona_variedade_de_ingredientes_e_validades(self):
        call_command("adicionar_ingredientes_exemplo", stdout=StringIO())

        self.assertEqual(Ingrediente.objects.count(), 16)
        self.assertTrue(Ingrediente.objects.filter(nome="Leite condensado").exists())
        self.assertTrue(Ingrediente.objects.filter(nome="Farinha de trigo").exists())
        hoje = timezone.localdate()
        self.assertTrue(Ingrediente.objects.filter(data_validade__lt=hoje).exists())
        self.assertTrue(
            Ingrediente.objects.filter(
                data_validade__range=(hoje, hoje + timedelta(days=7))
            ).exists()
        )
        self.assertTrue(
            Ingrediente.objects.filter(
                data_validade__gt=hoje + timedelta(days=7)
            ).exists()
        )

    def test_segunda_execucao_nao_duplica_nem_altera(self):
        call_command("adicionar_ingredientes_exemplo", stdout=StringIO())
        acucar = Ingrediente.objects.get(nome="Açúcar")
        acucar.estoque_atual = 1
        acucar.save()

        saida = StringIO()
        call_command("adicionar_ingredientes_exemplo", stdout=saida)

        acucar.refresh_from_db()
        self.assertEqual(Ingrediente.objects.count(), 16)
        self.assertEqual(acucar.estoque_atual, 1)
        self.assertIn("16 já existiam", saida.getvalue())
