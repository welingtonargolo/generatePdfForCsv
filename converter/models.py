from django.db import models

class ReportSchema(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nome do Esquema")
    columns = models.TextField(help_text="Lista de colunas separadas por vírgula na ordem correta.", verbose_name="Colunas BAT")

    class Meta:
        verbose_name = "Esquema de Relatório"
        verbose_name_plural = "Esquemas de Relatórios"

    def __str__(self):
        return f"Esquema: {self.name}"

    def get_column_list(self):
        return [c.strip() for c in self.columns.split(',') if c.strip()]

class MappingRule(models.Model):
    schema = models.ForeignKey(ReportSchema, on_delete=models.CASCADE, related_name='rules', null=True, verbose_name="Esquema Vinculado")
    source_key = models.CharField(max_length=100, verbose_name="Chave no PDF")
    target_key = models.CharField(max_length=100, verbose_name="Coluna no BAT (Destino)")
    
    class Meta:
        verbose_name = "Regra de Mapeamento"
        verbose_name_plural = "Regras de Mapeamento"
        ordering = ['source_key']
        unique_together = ('schema', 'source_key')

    def __str__(self):
        return f"[{self.schema}] {self.source_key} -> {self.target_key}"

class IA(models.Model):
    api_key = models.CharField(max_length=100, verbose_name="Chave de API")
    
