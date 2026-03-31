from django.db import models

class MappingRule(models.Model):
    source_key = models.CharField(max_length=100, unique=True, verbose_name="Chave no PDF")
    target_key = models.CharField(max_length=100, verbose_name="Coluna no BAT")
    
    class Meta:
        verbose_name = "Regra de Mapeamento"
        verbose_name_plural = "Regras de Mapeamento"
        ordering = ['source_key']

    def __str__(self):
        return f"{self.source_key} -> {self.target_key}"

class ReportSchema(models.Model):
    REPORT_TYPES = [
        ('produtos', 'Produtos'),
        ('clientes', 'Clientes'),
        ('fornecedores', 'Fornecedores'),
        ('vendas', 'Vendas'),
        ('generic', 'Gen\u00e9rico'),
    ]
    
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES, unique=True, verbose_name="Tipo de Relat\u00f3rio")
    columns = models.TextField(help_text="Lista de colunas separadas por v\u00edrgula na ordem correta.", verbose_name="Colunas BAT")

    class Meta:
        verbose_name = "Esquema de Relat\u00f3rio"
        verbose_name_plural = "Esquemas de Relat\u00f3rios"

    def __str__(self):
        return f"Esquema: {self.get_report_type_display()}"

    def get_column_list(self):
        return [c.strip() for c in self.columns.split(',') if c.strip()]

class IA(models.Model):
    api_key = models.CharField(max_length=100, verbose_name="Chave de API")
    
