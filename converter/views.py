from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import HttpResponse, JsonResponse
from .forms import PDFUploadForm
from .utils import extract_pdf_data, apply_bat_rules
from .models import MappingRule, ReportSchema, IA
import pandas as pd
from io import BytesIO

class HomeView(View):
    template_name = 'converter/index.html'

    def get(self, request):
        form = PDFUploadForm()
        ia_obj = IA.objects.first()
        ia_key = ia_obj.api_key if ia_obj else ''
        return render(request, self.template_name, {'form': form, 'ia': ia_key})

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

            use_ai = form.cleaned_data.get('use_ai')
            gemini_api_key = form.cleaned_data.get('gemini_api_key')

            # Process PDF
            try:
                if use_ai and gemini_api_key:
                    from .ai_extraction import extract_pdf_with_ai
                    from .models import IA
                    ia = IA.objects.filter(api_key=gemini_api_key).first()
                    if not ia:
                        ia = IA.objects.create(api_key=gemini_api_key)
                    else:
                        ia.api_key = gemini_api_key
                        ia.save()
                    print(f"Gemini API Key: {gemini_api_key}")


                    df = extract_pdf_with_ai(pdf_file, report_type, gemini_api_key)
                elif use_ai and not gemini_api_key:
                    raise Exception("A extração inteligente requer a inserção da Chave de API do Gemini.")
                else:
                    df = extract_pdf_data(pdf_file, report_type, magic_keywords, ignore_patterns)
                
                if df.empty:
                    return render(request, self.template_name, {
                        'form': form,
                        'error': 'Nenhuma tabela ou bloco válido encontrado no PDF.'
                    })

                # Apply BAT rules
                df = apply_bat_rules(df, report_type)

                # Prepare CSV response
                buffer = BytesIO()
                
                if len(delimiter) == 1:
                    df.to_csv(buffer, index=False, sep=delimiter, encoding=encoding)
                else:
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

        return render(request, self.template_name, {'form': form, 'ia': IA.objects.filter().first().api_key if IA.objects.filter().first() else ''})

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

class CompareView(View):
    template_name = 'converter/compare.html'

    def get(self, request):
        ia_obj = IA.objects.first()
        ia_key = ia_obj.api_key if ia_obj else ''
        return render(request, self.template_name, {'ia': ia_key})

    def post(self, request):
        pdf_file = request.FILES.get('pdf_file')
        csv_file = request.FILES.get('csv_file')
        use_ai = request.POST.get('use_ai')
        gemini_api_key = request.POST.get('gemini_api_key')
        
        if use_ai == 'on' and gemini_api_key:
            ia = IA.objects.filter(api_key=gemini_api_key).first()
            if not ia:
                IA.objects.create(api_key=gemini_api_key)
            else:
                ia.api_key = gemini_api_key
                ia.save()
            
            try:
                from .ai_extraction import audit_csv_with_ai
                result = audit_csv_with_ai(pdf_file, csv_file, gemini_api_key)
            except Exception as e:
                return render(request, self.template_name, {'error': f'Erro na Auditoria IA: {str(e)}', 'ia': gemini_api_key})
        elif use_ai == 'on' and not gemini_api_key:
            return render(request, self.template_name, {'error': 'O serviço requer sua chave da API!'})
        else:
            try:
                from .utils import audit_csv_classic
                result = audit_csv_classic(pdf_file, csv_file)
            except Exception as e:
                return render(request, self.template_name, {'error': f'Erro na validação clássica: {str(e)}'})

        if isinstance(result, dict) and result.get('status') == 'perfect':
            return JsonResponse({"status": "perfect"})
            
        elif isinstance(result, pd.DataFrame):
            buffer = BytesIO()
            result.to_csv(buffer, index=False, sep=';', encoding='utf-8')
            buffer.seek(0)
            response = HttpResponse(buffer.getvalue(), content_type='text/csv')
            filename = "auditoria_corrigida.csv"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        return JsonResponse({"status": "error", "message": "Falha geral."})
