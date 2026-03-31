import pdfplumber
import pandas as pd
import json
import requests
from .utils import get_dynamic_schema, enforce_schema

def extract_pdf_with_ai(file_obj, report_type, api_key):
    """
    Extracts tabular data from a raw PDF using Google Gemini REST API directly.
    """
    # 2. Extract RAW text from PDF
    text_content = ""
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            text_content += (page.extract_text() or "") + "\n"
            
    # 3. Get expected Schema
    schema = get_dynamic_schema(report_type)
    
    if not schema:
        schema_instruction = "Extraia todas as entidades lógicas que encontrar e use chaves consistentes para todas as entidades."
    else:
        columns_str = ", ".join(schema)
        schema_instruction = f"Você DEVE usar as seguintes chaves no seu JSON: [{columns_str}]. Se a informação correspondente a chave não for encontrada para um registro específico, retorne string vazia. Não crie chaves novas!"

    # 4. Construir o Prompt
    prompt = f"""Você é um extrator de dados altamente preciso especializado em ler arquivos PDF caóticos e desestuturados e convertê-los em JSON estruturado perfeito. 
Aqui está o conteúdo bruto extraído do PDF:

=== INICIO DO CONTEUDO ===
{text_content}
=== FIM DO CONTEUDO ===

Instruções críticas:
1. Retorne EXATAMENTE UM ARRAY JSON contendo objetos (dicionários). O formato deve ser perfeitamente parseável por json.loads() do Python.
2. {schema_instruction}
3. Cada objeto no array representa uma linha do relatório/tabela original (ex: um cliente, um produto, uma venda).
4. NÃO inclua rodapés, paginações, ou frases de sistema. Extraia apenas as informações reais de negócios.
5. Remova máscaras de CPF/CNPJ (deixe apenas os números).
6. Seu output deve ser APENAS O ARRAY JSON puro. Não escreva '```json' ou qualquer outro texto explicativo! APENAS o array puro (iniciando com '[' e terminando com ']').

Retorne o seu JSON agora.
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0}
    }
    
    # 5. Chamar a API via requests
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        err_msg = response.json().get('error', {}).get('message', response.text)
        raise Exception(f"Erro na API do Gemini: {err_msg}")
        
    ai_response = response.json()
    try:
        raw_json = ai_response['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError):
        raise Exception("Resposta inválida ou vazia recebida do Gemini.")
    
    # Limpeza do markdown do JSON
    if raw_json.startswith('```json'):
        raw_json = raw_json[7:]
    elif raw_json.startswith('```'):
        raw_json = raw_json[3:]
        
    if raw_json.endswith('```'):
        raw_json = raw_json[:-3]
        
    raw_json = raw_json.strip()
    
    # 6. Transformar em DataFrame
    try:
        data = json.loads(raw_json)
        if not isinstance(data, list):
            data = [data]
            
        df = pd.DataFrame(data)
        return enforce_schema(df, report_type)
        
    except json.JSONDecodeError as e:
        raise Exception(f"Erro ao interpretar a resposta inteligente da IA. Formato recebido inválido: {e}\nRaw Output: {raw_json}")

def audit_csv_with_ai(pdf_file, csv_file, api_key):
    """
    Audits an extracted CSV file against the original PDF using Gemini 2.5 Flash.
    Returns:
       - dict: {"status": "perfect"} if perfectly aligned.
       - df: Dataframe with the corrected data if there are issues.
    """
    # 1. Obter textos
    pdf_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            pdf_text += (page.extract_text() or "") + "\n"
            
    csv_text = csv_file.read().decode('utf-8', errors='replace')
    csv_file.seek(0)
    pdf_file.seek(0)
    
    # 2. Construir Prompt de Auditoria Direcional
    prompt = f"""Você é um Auditor Sênior de Extração de Dados e Analista de Controle de Qualidade.
Sua função é inspecionar friamente um Arquivo CSV que foi gerado a partir de um PDF e checar a integridade absoluta.

=== DADOS GERAIS DO PDF ORIGINAL ===
{pdf_text}
=== FIM DOS DADOS DO PDF ===

=== ARQUIVO CSV A SER AUDITADO ===
{csv_text}
=== FIM DO ARQUIVO CSV ===

Suas Diretrizes Restritas:
1. Veja se todas as Entidades visíveis do PDF (Como clientes, códigos, produtos, informações, etc) estão presentes no CSV.
2. Descubra se as colunas estão no lugar certo ou se esmagaram e empurraram os valores pro lado.
3. Decisão 1: Se o CSV for **100% CORRETO, COMPLETO E ÍNTEGRO** comparado aos dados do PDF, VOCÊ DEVE RESPONDER exatamente com a palavra:
PERFECT
Nenhum caracter a mais. Nenhuma aspa. Nada.

4. Decisão 2: Se o CSV tiver **QUALQUER FALHA MÍNIMA** (Uma coluna faltando, dados esmagados no final, registros faltando ou omitidos, ou cabeçalhos desalinhados), VOCÊ IRÁ CORRIGIR e EXTRAIR TUDO DO ZERO.
Se for corrigir, DEVOLVA EXATAMENTE UM ARRAY JSON PURO E ESTRUTURADO com todas as linhas do documento limpas, e com chaves uniformes indicando o nome das colunas lógicas. 
Se for extrair do zero e corrigir, não escreva markdown nem nada. APENAS BOTE O [] JSON.

Tome a sua Decisão (PERFECT ou o Array JSON).
"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0}
    }
    
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        err_msg = response.json().get('error', {}).get('message', response.text)
        raise Exception(f"Erro na API do Gemini: {err_msg}")
        
    ai_response = response.json()
    try:
        raw_output = ai_response['candidates'][0]['content']['parts'][0]['text'].strip()
    except (KeyError, IndexError):
        raise Exception("Resposta inválida do Gemini durante a auditoria.")
        
    if raw_output.upper() == "PERFECT" or "PERFECT" in raw_output:
        return {"status": "perfect"}
        
    # Se a IA retornou os dados para correção, desempacotamos
    if raw_output.startswith('```json'):
        raw_output = raw_output[7:]
    elif raw_output.startswith('```'):
        raw_output = raw_output[3:]
    if raw_output.endswith('```'):
        raw_output = raw_output[:-3]
        
    raw_output = raw_output.strip()
    
    try:
        data = json.loads(raw_output)
        if not isinstance(data, list):
            data = [data]
        df = pd.DataFrame(data)
        
        # Como o esquema no modo de auditoria nem sempre foi preenchido, apenas padronizamos chaves
        df.columns = [c.upper().replace(' ', '_') for c in df.columns]
        return df
    except json.JSONDecodeError as e:
        raise Exception(f"Erro ao parsear correção JSON da IA. O arquivo estava tão corrompido que a IA não conseguiu gerar JSON válido. Output: {raw_output}")
