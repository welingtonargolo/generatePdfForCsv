from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import HttpResponse, JsonResponse
from .forms import PDFUploadForm
from .utils import extract_pdf_data, apply_bat_rules
from .models import MappingRule, ReportSchema
import pandas as pd
from io import BytesIO

class HomeView(View):
    template_name = 'converter/index.html'

    def get(self, request):
        form = PDFUploadForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = PDFUploadForm(request.POST, request.FILES)
        if form.is_valid():
            pdf_file = request.FILES['pdf_file']
            report_type = form.cleaned_data['report_type']
            encoding = form.cleaned_data['encoding']
            delimiter = form.cleaned_data['delimiter']
            magic_keywords_raw = form.cleaned_data['magic_keywords']
            magic_keywords = [k.strip() for k in magic_keywords_raw.split(',')] if magic_keywords_raw else None
            
            ignore_patterns_raw = form.cleaned_data['ignore_patterns']
            ignore_patterns = [p.strip() for p in ignore_patterns_raw.split(',')] if ignore_patterns_raw else []

            # Process PDF
            try:
                df = extract_pdf_data(pdf_file, report_type, magic_keywords, ignore_patterns)
                
                if df.empty:
                    return render(request, self.template_name, {
                        'form': form,
                        'error': 'Nenhuma tabela encontrada no PDF. Verifique se o arquivo possui texto selecion\u00e1vel.'
                    })

                # Apply BAT rules
                df = apply_bat_rules(df, report_type)

                # Prepare CSV response
                buffer = BytesIO()
                
                if len(delimiter) == 1:
                    df.to_csv(buffer, index=False, sep=delimiter, encoding=encoding)
                else:
                    # Manual CSV generation for multi-character delimiters
                    csv_text = delimiter.join(df.columns) + "\n"
                    for _, row in df.iterrows():
                        csv_text += delimiter.join([str(val) for val in row]) + "\n"
                    buffer.write(csv_text.encode(encoding))
                
                buffer.seek(0)

                response = HttpResponse(buffer.getvalue(), content_type='text/csv')
                filename = f"bat_import_{report_type}.csv"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                
                return response

            except Exception as e:
                return render(request, self.template_name, {
                    'form': form,
                    'error': f'Erro ao processar PDF: {str(e)}'
                })

        return render(request, self.template_name, {'form': form})

class SettingsView(View):
    template_name = 'converter/settings.html'

    def get(self, request):
        mappings = MappingRule.objects.all()
        schemas = ReportSchema.objects.all()
        return render(request, self.template_name, {
            'mappings': mappings,
            'schemas': schemas
        })

    def post(self, request):
        action = request.POST.get('action')
        
        if action == 'add_mapping':
            source = request.POST.get('source_key')
            target = request.POST.get('target_key')
            if source and target:
                MappingRule.objects.get_or_create(source_key=source, defaults={'target_key': target})
        
        elif action == 'delete_mapping':
            rule_id = request.POST.get('rule_id')
            MappingRule.objects.filter(id=rule_id).delete()
            
        elif action == 'update_schema':
            schema_id = request.POST.get('schema_id')
            columns = request.POST.get('columns')
            if schema_id and columns:
                schema = get_object_or_404(ReportSchema, id=schema_id)
                schema.columns = columns
                schema.save()
                
        return redirect('converter:settings')
