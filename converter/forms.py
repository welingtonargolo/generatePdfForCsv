from django import forms

REPORT_TYPES = [
    ('produtos', 'Produtos'),
    ('clientes', 'Clientes'),
    ('fornecedores', 'Fornecedores'),
    ('vendas', 'Vendas'),
    ('generic', 'Relat\u00f3rio Gen\u00e9rico'),
]

ENCODING_CHOICES = [
    ('utf-8', 'UTF-8'),
    ('windows-1252', 'Windows-1252 (Latin-1)'),
]

class PDFUploadForm(forms.Form):
    pdf_file = forms.FileField(
        label='Selecione o PDF',
        help_text='O arquivo ser\u00e1 processado em mem\u00f3ria.',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'})
    )
    report_type = forms.ChoiceField(
        choices=REPORT_TYPES,
        initial='generic',
        label='Tipo de Relat\u00f3rio',
        widget=forms.Select(attrs={'class': 'form-select'})
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
