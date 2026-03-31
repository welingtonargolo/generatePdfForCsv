from django import forms
from .models import ReportSchema

ENCODING_CHOICES = [
    ('utf-8', 'UTF-8'),
    ('windows-1252', 'Windows-1252 (Latin-1)'),
]

class PDFUploadForm(forms.Form):
    pdf_file = forms.FileField(
        label='Selecione o PDF',
        help_text='O arquivo será processado em memória.',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'})
    )
    report_type = forms.ModelChoiceField(
        queryset=ReportSchema.objects.all(),
        empty_label="Selecione um Esquema",
        label='Esquema de Relatório (Alvo)',
        widget=forms.Select(attrs={'class': 'form-select bg-light border-0'})
    )
    encoding = forms.ChoiceField(
        choices=ENCODING_CHOICES,
        initial='utf-8',
        label='Encoding do CSV',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    delimiter = forms.CharField(
        initial=';',
        required=True,
        label='Delimitador CSV',
        help_text='Ex: ; ou , ou | ou qualquer sequ\u00eancia',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': ';'})
    )
    magic_keywords = forms.CharField(
        required=False,
        label='Separador de Registros (Opcional)',
        help_text='Palavras que iniciam um novo produto (ex: COD_INTERNO).',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: COD_INTERNO'})
    )
    ignore_patterns = forms.CharField(
        required=False,
        label='Ignorar Padr\u00f5es (Opcional)',
        help_text='Sequ\u00eancias a remover (ex: ---, ***). Separar por v\u00edrgula.',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: ---, RELATORIO'})
    )
    use_ai = forms.BooleanField(
        required=False,
        label='Extração Inteligente (IA)',
        help_text='Ative para usar o Google Gemini na extração.',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    gemini_api_key = forms.CharField(
        required=False,
        label='Chave da API do Gemini',
        help_text='Necessária se a Extração Inteligente estiver ativada.',
        widget=forms.PasswordInput(attrs={'class': 'form-control bg-light border-0', 'placeholder': 'AIzaSy...'})
    )
