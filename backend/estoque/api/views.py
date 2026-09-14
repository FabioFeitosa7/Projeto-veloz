from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from estoque.api.serializers import (
    DataApuracaoSerializer,
    FechamentoSerializer,
    IngredienteSerializer,
    ItemFechamentoSerializer,
)
from estoque.models import FechamentoMensal, Ingrediente, StatusFechamento
from estoque.services.calculos import SituacaoValidade, resumir_validade
from estoque.services.exportacoes import ErroExportacao, gerar_csv, gerar_txt
from estoque.services.fechamentos import (
    ErroFechamento,
    calcular_revisao,
    cancelar_fechamento,
    criar_rascunho,
    finalizar_fechamento,
)


class DashboardAPIView(APIView):
    def get(self, request):
        hoje = timezone.localdate()
        ingredientes = list(Ingrediente.objects.filter(ativo=True))
        dados = []
        proximos = 0
        vencidos = 0
        for ingrediente in ingredientes:
            resumo = resumir_validade(ingrediente.data_validade, hoje)
            if resumo.situacao in {
                SituacaoValidade.PROXIMO_DO_VENCIMENTO,
                SituacaoValidade.VENCE_HOJE,
            }:
                proximos += 1
            if resumo.situacao == SituacaoValidade.VENCIDO:
                vencidos += 1
            dados.append(IngredienteSerializer(ingrediente).data)
        return Response({
            "data": hoje,
            "totais": {
                "ingredientes": len(ingredientes),
                "proximos_do_vencimento": proximos,
                "vencidos": vencidos,
            },
            "ingredientes": dados,
        })


class IngredienteViewSet(viewsets.ModelViewSet):
    serializer_class = IngredienteSerializer
    http_method_names = ("get", "post", "patch", "head", "options")

    def get_queryset(self):
        consulta = Ingrediente.objects.all()
        if self.action != "list":
            return consulta
        situacao = self.request.query_params.get("situacao", "ativos")
        busca = self.request.query_params.get("q", "").strip()
        if situacao == "inativos":
            consulta = consulta.filter(ativo=False)
        elif situacao != "todos":
            consulta = consulta.filter(ativo=True)
        if busca:
            consulta = consulta.filter(nome__icontains=busca)
        return consulta

    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response(
                {"nome": ["Já existe um ingrediente com este nome."]},
                status=status.HTTP_409_CONFLICT,
            )

    def update(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                return super().update(request, *args, **kwargs)
        except IntegrityError:
            return Response(
                {"nome": ["Já existe um ingrediente com este nome."]},
                status=status.HTTP_409_CONFLICT,
            )

    @action(detail=True, methods=("post",))
    def desativar(self, request, pk=None):
        ingrediente = self.get_object()
        ingrediente.ativo = False
        ingrediente.save(update_fields=("ativo", "atualizado_em"))
        return Response(self.get_serializer(ingrediente).data)

    @action(detail=True, methods=("post",))
    def reativar(self, request, pk=None):
        ingrediente = self.get_object()
        ingrediente.ativo = True
        ingrediente.save(update_fields=("ativo", "atualizado_em"))
        return Response(self.get_serializer(ingrediente).data)


class FechamentoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FechamentoSerializer
    queryset = FechamentoMensal.objects.prefetch_related("itens").annotate(
        total_itens=Count("itens"),
        total_compras=Count("itens", filter=Q(itens__quantidade_compra__gt=0)),
    )

    def create(self, request):
        serializer = FechamentoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            fechamento = criar_rascunho(serializer.validated_data["referencia"])
        except (ErroFechamento, IntegrityError) as erro:
            mensagem = (
                str(erro)
                if isinstance(erro, ErroFechamento)
                else "Já existe um fechamento ativo para este mês."
            )
            return Response({"detail": mensagem}, status=status.HTTP_409_CONFLICT)
        fechamento = self.get_queryset().get(pk=fechamento.pk)
        return Response(
            self.get_serializer(fechamento).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=("patch",))
    def itens(self, request, pk=None):
        fechamento = self.get_object()
        if fechamento.status != StatusFechamento.RASCUNHO:
            return Response(
                {"detail": "Apenas um fechamento em rascunho pode ser editado."},
                status=status.HTTP_409_CONFLICT,
            )
        payload = request.data.get("itens")
        if not isinstance(payload, list):
            return Response(
                {"itens": ["Envie uma lista de itens."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ids = [item.get("id") for item in payload]
        if None in ids or len(ids) != len(set(ids)):
            return Response(
                {"itens": ["Cada item deve possuir um id único."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        existentes = {
            item.pk: item for item in fechamento.itens.filter(pk__in=ids)
        }
        if len(existentes) != len(ids):
            return Response(
                {"itens": ["Há um item que não pertence a este fechamento."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializers = []
        erros = {}
        for indice, dados in enumerate(payload):
            item_serializer = ItemFechamentoSerializer(
                existentes[dados["id"]], data=dados, partial=True
            )
            if not item_serializer.is_valid():
                erros[indice] = item_serializer.errors
            serializers.append(item_serializer)
        if erros:
            return Response({"itens": erros}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            for item_serializer in serializers:
                item_serializer.save()
        fechamento.refresh_from_db()
        return Response(self.get_serializer(fechamento).data)

    def _data_apuracao(self, request):
        serializer = DataApuracaoSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data.get("data_apuracao")

    @action(detail=True, methods=("get",))
    def revisao(self, request, pk=None):
        fechamento = self.get_object()
        try:
            revisao = calcular_revisao(
                fechamento, data_apuracao=self._data_apuracao(request)
            )
        except ErroFechamento as erro:
            return Response({"detail": str(erro)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "fechamento": fechamento.pk,
            "itens": [
                {
                    "id": item.item.pk,
                    "ingrediente": item.item.nome_registrado,
                    "unidade": item.item.unidade_registrada,
                    "unidade_exibicao": item.item.get_unidade_registrada_display(),
                    "meta_anterior": item.item.meta_anterior,
                    "situacao_validade": item.resultado.situacao_validade.value,
                    "motivo": item.resultado.motivo.value,
                    "estoque_aproveitavel": item.resultado.estoque_aproveitavel,
                    "meta_resultante": item.resultado.meta_resultante,
                    "quantidade_compra": item.resultado.quantidade_compra,
                    "explicacao": item.explicacao,
                    "linha_compra": item.linha_compra,
                }
                for item in revisao
            ],
        })

    @action(detail=True, methods=("post",))
    def finalizar(self, request, pk=None):
        try:
            fechamento = finalizar_fechamento(
                int(pk), data_apuracao=self._data_apuracao(request)
            )
        except ErroFechamento as erro:
            return Response({"detail": str(erro)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(fechamento).data)

    @action(detail=True, methods=("post",))
    def cancelar(self, request, pk=None):
        try:
            fechamento = cancelar_fechamento(int(pk))
        except FechamentoMensal.DoesNotExist:
            return Response(
                {"detail": "Fechamento não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ErroFechamento as erro:
            return Response({"detail": str(erro)}, status=status.HTTP_409_CONFLICT)
        return Response(self.get_serializer(fechamento).data)


class DownloadListaAPIView(APIView):
    formato = "txt"

    def get(self, request, pk):
        try:
            fechamento = FechamentoMensal.objects.get(pk=pk)
            conteudo = gerar_txt(fechamento) if self.formato == "txt" else gerar_csv(fechamento)
        except FechamentoMensal.DoesNotExist:
            return Response({"detail": "Fechamento não encontrado."}, status=404)
        except ErroExportacao as erro:
            return Response({"detail": str(erro)}, status=status.HTTP_409_CONFLICT)
        if self.formato == "csv":
            conteudo = "\ufeff" + conteudo
        resposta = HttpResponse(
            conteudo,
            content_type=(
                "text/plain; charset=utf-8"
                if self.formato == "txt"
                else "text/csv; charset=utf-8"
            ),
        )
        nome = f"lista-compras-{fechamento.referencia:%Y-%m}.{self.formato}"
        resposta["Content-Disposition"] = f'attachment; filename="{nome}"'
        return resposta


class DownloadListaTxtAPIView(DownloadListaAPIView):
    formato = "txt"


class DownloadListaCsvAPIView(DownloadListaAPIView):
    formato = "csv"
