from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from estoque.models import (
    FechamentoMensal,
    Ingrediente,
    ItemFechamento,
    StatusFechamento,
    UnidadeMedida,
)
from estoque.services.fechamentos import ErroFechamento, criar_rascunho


class CriarRascunhoServiceTests(TestCase):
    def criar_ingrediente(self, nome="Farinha", ativo=True):
        return Ingrediente.objects.create(
            nome=nome,
            unidade=UnidadeMedida.QUILOGRAMA,
            meta_atual=Decimal("20"),
            estoque_atual=Decimal("6"),
            data_validade=date(2026, 10, 20),
            ativo=ativo,
        )

    def test_cria_retrato_apenas_dos_ingredientes_ativos(self):
        ativo = self.criar_ingrediente()
        self.criar_ingrediente(nome="Inativo", ativo=False)

        fechamento = criar_rascunho(date(2026, 9, 1))

        self.assertEqual(fechamento.status, StatusFechamento.RASCUNHO)
        self.assertEqual(fechamento.itens.count(), 1)
        item = fechamento.itens.get()
        self.assertEqual(item.ingrediente, ativo)
        self.assertEqual(item.nome_registrado, "Farinha")
        self.assertEqual(item.meta_anterior, Decimal("20"))
        self.assertEqual(item.validade_registrada, date(2026, 10, 20))

    def test_sem_ingrediente_ativo_nao_cria_fechamento(self):
        with self.assertRaisesMessage(
            ErroFechamento,
            "Cadastre pelo menos um ingrediente ativo antes do fechamento.",
        ):
            criar_rascunho(date(2026, 9, 1))

        self.assertFalse(FechamentoMensal.objects.exists())


class FechamentoRascunhoViewTests(TestCase):
    def setUp(self):
        self.ingrediente = Ingrediente.objects.create(
            nome="Farinha",
            unidade=UnidadeMedida.QUILOGRAMA,
            meta_atual=Decimal("20"),
            estoque_atual=Decimal("6"),
            data_validade=date(2026, 10, 20),
        )

    def test_pagina_de_novo_fechamento(self):
        resposta = self.client.get(reverse("estoque:fechamento_novo"))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Novo fechamento")
        self.assertContains(resposta, 'type="month"')

    def test_cria_fechamento_e_redireciona_para_edicao(self):
        resposta = self.client.post(
            reverse("estoque:fechamento_novo"),
            {"referencia": "2026-09"},
        )

        fechamento = FechamentoMensal.objects.get()
        self.assertRedirects(
            resposta,
            reverse("estoque:fechamento_editar", args=(fechamento.pk,)),
        )
        self.assertEqual(fechamento.itens.count(), 1)

    def test_inicio_continua_rascunho_existente(self):
        fechamento = criar_rascunho(date(2026, 9, 1))

        resposta = self.client.get(reverse("estoque:fechamento_inicio"))

        self.assertRedirects(
            resposta,
            reverse("estoque:fechamento_editar", args=(fechamento.pk,)),
        )

    def test_novo_fechamento_recusa_mes_duplicado(self):
        criar_rascunho(date(2026, 9, 1))

        resposta = self.client.post(
            reverse("estoque:fechamento_novo"),
            {"referencia": "2026-09"},
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Já existe um fechamento para este mês.")
        self.assertEqual(FechamentoMensal.objects.count(), 1)

    def test_edicao_exibe_todos_os_itens(self):
        fechamento = criar_rascunho(date(2026, 9, 1))

        resposta = self.client.get(
            reverse("estoque:fechamento_editar", args=(fechamento.pk,))
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Farinha")
        self.assertContains(resposta, "Salvar rascunho")

    def test_salva_rascunho_completo_sem_atualizar_meta(self):
        fechamento = criar_rascunho(date(2026, 9, 1))
        item = fechamento.itens.get()
        dados = {
            "itens-TOTAL_FORMS": "1",
            "itens-INITIAL_FORMS": "1",
            "itens-MIN_NUM_FORMS": "0",
            "itens-MAX_NUM_FORMS": "1000",
            "itens-0-id": str(item.pk),
            "itens-0-consumo_mensal": "14",
            "itens-0-estoque_restante": "6",
            "itens-0-validade_registrada": "2026-10-20",
        }

        resposta = self.client.post(
            reverse("estoque:fechamento_editar", args=(fechamento.pk,)),
            dados,
        )

        item.refresh_from_db()
        self.ingrediente.refresh_from_db()
        self.assertEqual(item.consumo_mensal, Decimal("14"))
        self.assertEqual(item.estoque_restante, Decimal("6"))
        self.assertEqual(self.ingrediente.meta_atual, Decimal("20"))
        self.assertRedirects(
            resposta,
            reverse("estoque:fechamento_editar", args=(fechamento.pk,)),
        )

    def test_salva_rascunho_parcial(self):
        fechamento = criar_rascunho(date(2026, 9, 1))
        item = fechamento.itens.get()
        dados = {
            "itens-TOTAL_FORMS": "1",
            "itens-INITIAL_FORMS": "1",
            "itens-MIN_NUM_FORMS": "0",
            "itens-MAX_NUM_FORMS": "1000",
            "itens-0-id": str(item.pk),
            "itens-0-consumo_mensal": "14",
            "itens-0-estoque_restante": "",
            "itens-0-validade_registrada": "",
        }

        resposta = self.client.post(
            reverse("estoque:fechamento_editar", args=(fechamento.pk,)),
            dados,
        )

        item.refresh_from_db()
        self.assertEqual(item.consumo_mensal, Decimal("14"))
        self.assertIsNone(item.estoque_restante)
        self.assertIsNone(item.validade_registrada)
        self.assertEqual(resposta.status_code, 302)

    def test_edicao_de_finalizado_e_bloqueada(self):
        fechamento = criar_rascunho(date(2026, 9, 1))
        fechamento.status = StatusFechamento.FINALIZADO
        fechamento.finalizado_em = timezone.now()
        fechamento.save()

        resposta = self.client.get(
            reverse("estoque:fechamento_editar", args=(fechamento.pk,))
        )

        self.assertEqual(resposta.status_code, 403)

    def test_post_sem_ingredientes_exibe_erro(self):
        self.ingrediente.ativo = False
        self.ingrediente.save()

        resposta = self.client.post(
            reverse("estoque:fechamento_novo"),
            {"referencia": "2026-09"},
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(
            resposta,
            "Cadastre pelo menos um ingrediente ativo antes do fechamento.",
        )
        self.assertFalse(FechamentoMensal.objects.exists())
