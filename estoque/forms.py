from datetime import date
from decimal import Decimal

from django import forms

from estoque.models import FechamentoMensal, Ingrediente, ItemFechamento


class IngredienteForm(forms.ModelForm):
    meta_atual = forms.DecimalField(
        label="Meta mensal",
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0.001"),
        localize=True,
        widget=forms.TextInput(attrs={"inputmode": "decimal"}),
        error_messages={
            "required": "Informe a meta mensal.",
            "invalid": "Informe uma meta válida.",
            "min_value": "A meta deve ser maior que zero.",
        },
    )
    estoque_atual = forms.DecimalField(
        label="Último estoque informado",
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
        localize=True,
        widget=forms.TextInput(attrs={"inputmode": "decimal"}),
        error_messages={
            "required": "Informe o último estoque.",
            "invalid": "Informe um estoque válido.",
            "min_value": "O estoque não pode ser negativo.",
        },
    )

    class Meta:
        model = Ingrediente
        fields = (
            "nome",
            "unidade",
            "meta_atual",
            "estoque_atual",
            "data_validade",
        )
        labels = {
            "nome": "Nome do ingrediente",
            "unidade": "Unidade de medida",
            "data_validade": "Data de validade",
        }
        widgets = {
            "data_validade": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date"},
            ),
        }
        error_messages = {
            "nome": {"required": "Informe o nome do ingrediente."},
            "unidade": {"required": "Selecione a unidade de medida."},
            "data_validade": {"required": "Informe a data de validade."},
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.itens_fechamento.exists():
            self.fields["unidade"].disabled = True
            self.fields["unidade"].help_text = (
                "A unidade não pode ser alterada porque já existe histórico."
            )

    def clean_nome(self) -> str:
        nome = " ".join(self.cleaned_data["nome"].split())
        existentes = Ingrediente.objects.filter(nome__iexact=nome)
        if self.instance.pk:
            existentes = existentes.exclude(pk=self.instance.pk)
        if existentes.exists():
            raise forms.ValidationError("Já existe um ingrediente com este nome.")
        return nome


class FechamentoMensalForm(forms.ModelForm):
    referencia = forms.DateField(
        label="Mês de referência",
        input_formats=("%Y-%m",),
        widget=forms.DateInput(format="%Y-%m", attrs={"type": "month"}),
        error_messages={
            "required": "Informe o mês de referência.",
            "invalid": "Informe um mês de referência válido.",
        },
    )

    class Meta:
        model = FechamentoMensal
        fields = ("referencia",)

    def clean_referencia(self) -> date:
        referencia = self.cleaned_data["referencia"].replace(day=1)
        existentes = FechamentoMensal.objects.filter(referencia=referencia)
        if self.instance.pk:
            existentes = existentes.exclude(pk=self.instance.pk)
        if existentes.exists():
            raise forms.ValidationError("Já existe um fechamento para este mês.")
        return referencia


class ItemFechamentoForm(forms.ModelForm):
    consumo_mensal = forms.DecimalField(
        label="Consumo mensal",
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
        localize=True,
        widget=forms.TextInput(attrs={"inputmode": "decimal"}),
        error_messages={
            "required": "Informe o consumo mensal.",
            "invalid": "Informe um consumo válido.",
            "min_value": "O consumo não pode ser negativo.",
        },
    )
    estoque_restante = forms.DecimalField(
        label="Estoque restante",
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0"),
        localize=True,
        widget=forms.TextInput(attrs={"inputmode": "decimal"}),
        error_messages={
            "required": "Informe o estoque restante.",
            "invalid": "Informe um estoque válido.",
            "min_value": "O estoque não pode ser negativo.",
        },
    )
    validade_registrada = forms.DateField(
        label="Data de validade considerada",
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={"type": "date"},
        ),
        error_messages={
            "required": "Informe a data de validade.",
            "invalid": "Informe uma data de validade válida.",
        },
    )

    class Meta:
        model = ItemFechamento
        fields = (
            "consumo_mensal",
            "estoque_restante",
            "validade_registrada",
            "houve_falta",
        )
        labels = {
            "validade_registrada": "Data de validade considerada",
            "houve_falta": "Acabou antes do fim do mês?",
        }

    def __init__(self, *args, exigir_preenchimento=True, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if not exigir_preenchimento:
            for nome in (
                "consumo_mensal",
                "estoque_restante",
                "validade_registrada",
            ):
                self.fields[nome].required = False


class BaseItemFechamentoFormSet(forms.BaseModelFormSet):
    def clean(self) -> None:
        super().clean()
        if any(self.errors):
            return

        ingredientes = [
            form.instance.ingrediente_id
            for form in self.forms
            if form.instance.ingrediente_id
        ]
        if len(ingredientes) != len(set(ingredientes)):
            raise forms.ValidationError(
                "Um ingrediente não pode aparecer duas vezes no fechamento."
            )


ItemFechamentoFormSet = forms.modelformset_factory(
    ItemFechamento,
    form=ItemFechamentoForm,
    formset=BaseItemFechamentoFormSet,
    extra=0,
    can_delete=False,
)
