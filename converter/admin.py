from django.contrib import admin
from .models import MappingRule, ReportSchema, IA

@admin.register(MappingRule)
class MappingRuleAdmin(admin.ModelAdmin):
    list_display = ('source_key', 'target_key', 'schema')
    search_fields = ('source_key', 'target_key')
    list_filter = ('schema',)

@admin.register(ReportSchema)
class ReportSchemaAdmin(admin.ModelAdmin):
    list_display = ('name',)

@admin.register(IA)
class IAAdmin(admin.ModelAdmin):
    list_display = ('api_key',)
