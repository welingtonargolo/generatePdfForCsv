import pdfplumber
import pandas as pd
import re
import unicodedata
from io import BytesIO

from .models import MappingRule, ReportSchema

def get_dynamic_mapping(schema_id):
    """Fetches mapping rules from the database for a specific schema."""
    if not schema_id: return {}
    return {rule.source_key: rule.target_key for rule in MappingRule.objects.filter(schema_id=schema_id)}

def get_dynamic_schema(schema_id):
    """Fetches report schema from the database."""
    if not schema_id: return []
    schema_obj = ReportSchema.objects.filter(id=schema_id).first()
    return schema_obj.get_column_list() if schema_obj else []

# Keys that usually indicate a new record starts
PRIMARY_KEYS = ['CODIGO', 'COD INTERNO', 'REF', 'REFERENCIA', 'CPF', 'CNPJ', 'DOCUMENTO', 'NOME', 'CLIENTE']

def normalize_text(text):
    if not isinstance(text, str):
        return text
    text = text.upper()
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    return text.strip()

def clean_mask(text):
    if not isinstance(text, str):
        return text
    return re.sub(r'[\.\-\/]', '', text).strip()

def format_currency(text):
    if not isinstance(text, str):
        return text
    text = text.replace('R$', '').strip()
    text = text.replace('.', '').replace(',', '.')
    try:
        return float(text)
    except ValueError:
        return text

def format_date(text):
    if not isinstance(text, str):
        return text
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return pd.to_datetime(text, format=fmt).strftime('%Y-%m-%d')
        except:
            continue
    return text

def parse_multi_key_value_block(text, start_keyword, schema_id=None):
    """
    Parses messy text where multiple KEY: VALUE pairs might exist on the same line,
    records are broken by arbitrary newlines, padded with dots, or otherwise noisy.
    
    Implements a robust Continuous Stream approach:
    1. Fixes fragmentation in the start_keyword itself (e.g., "Clien \\n te:" to "Cliente:").
    2. Flattens the text into a single stream.
    3. Splits by start_keyword.
    4. Extracts all standard and dot-padded inline keys.
    """
    records = []
    
    kw_chars = [re.escape(c) for c in start_keyword if not c.isspace()]
    if not kw_chars:
        return records
        
    fuzzy_pattern = r'\s*'.join(kw_chars)
    standard_start = start_keyword.strip()
    
    try:
        text = re.sub(fuzzy_pattern, standard_start, text, flags=re.IGNORECASE)
    except Exception:
        pass

    # Flatten text stream to remove line breaks
    stream = text.replace('\n', ' ')
    
    # Split into blocks, case insensitive
    blocks = re.split(re.escape(standard_start), stream, flags=re.IGNORECASE)
    
    mapping = get_dynamic_mapping(schema_id)
    
    # Regex to handle padded keys like "Documento.........:"
    key_pattern = r'\b([A-Za-zÀ-ÿ0-9ºª°]+(?:\s*[/-]\s*[A-Za-zÀ-ÿ0-9ºª°]+)*)[\.\s]*:'
    
    for block in blocks[1:]: 
        block_text = f"{standard_start} {block}"
        
        matches = list(re.finditer(key_pattern, block_text))
        record = {}
        
        if not matches:
            continue
            
        for i, match in enumerate(matches):
            raw_key = match.group(1).strip()
            
            start_val = match.end()
            end_val = matches[i+1].start() if i + 1 < len(matches) else len(block_text)
            
            value = block_text[start_val:end_val].strip()
            if value.endswith('-'):
                value = value[:-1].strip()
                
            key_norm = normalize_text(raw_key)
            std_key = mapping.get(key_norm, key_norm)
            
            record[std_key] = value
            
        records.append(record)
        
    return records


def is_kv_format(text):
    """
    Detects if the text has a high density of KEY: VALUE patterns.
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if not lines:
        return False
    
    kv_count = sum(1 for l in lines if ':' in l and 2 < l.find(':') < 30)
    ratio = kv_count / len(lines)
    return ratio > 0.4

def parse_key_value_text(text, custom_separators=None, schema_id=None):
    """
    Parses "ugly" text reports formatted as KEY: VALUE lists.
    Flattens fields into professional records.
    """
    records = []
    current_record = {}
    
    separators = PRIMARY_KEYS + (custom_separators or [])
    separators = [normalize_text(s) for s in separators]
    
    mapping = get_dynamic_mapping(schema_id)
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if ':' in line:
            parts = line.split(':', 1)
            raw_key = parts[0].strip()
            value = parts[1].strip()
            
            key_norm = normalize_text(raw_key)
            standard_key = mapping.get(key_norm, key_norm)

            if '---' in line or (key_norm in separators and standard_key in current_record):
                if current_record:
                    records.append(current_record)
                current_record = {}
                if '---' in line:
                    continue

            current_record[standard_key] = value
        else:
            if current_record:
                last_key = list(current_record.keys())[-1]
                current_record[last_key] += " " + line

    if current_record:
        records.append(current_record)
        
    return records

def extract_pdf_data(file_obj, schema_id=None, magic_keywords=None, ignore_patterns=None):
    """
    Extracts tabular data from a PDF file using multiple fallback strategies and robust alignment.
    """
    all_data = []
    text_content = ""
    
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            text_content += (page.extract_text() or "") + "\n"

    if ignore_patterns:
        for pattern in ignore_patterns:
            try:
                text_content = re.sub(pattern, "", text_content, flags=re.IGNORECASE)
            except Exception:
                text_content = text_content.replace(pattern, "")

    # PRIORITIZE Block Parser if user provided magic_keyword
    if magic_keywords and isinstance(magic_keywords, list) and len(magic_keywords) > 0:
        for start_kw in magic_keywords:
            if start_kw.strip():
                block_records = parse_multi_key_value_block(text_content, start_kw, schema_id=schema_id)
                if block_records:
                    df = pd.DataFrame(block_records)
                    return enforce_schema(df, schema_id)

    # PRIORITIZE KV Parser if density is high
    if is_kv_format(text_content):
        kv_records = parse_key_value_text(text_content, magic_keywords, schema_id=schema_id)
        if kv_records:
            df = pd.DataFrame(kv_records)
            return enforce_schema(df, schema_id)

    # STANDBY: Try Block parser
    for guess_kw in ['CLIENTE:', 'CLIENTE Nº', 'CODIGO:', 'NOME:']:
        block_records = parse_multi_key_value_block(text_content, guess_kw, schema_id=schema_id)
        if block_records and len(block_records) > 0 and len(block_records[0].keys()) > 1:
            df = pd.DataFrame(block_records)
            return enforce_schema(df, schema_id)

    # FALLBACK: Try Table Extraction
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table:
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "intersection_tolerance": 5
                })
                if tables:
                    table = tables[0]

            if table:
                if not all_data:
                    all_data.extend(table)
                else:
                    if table[0] == all_data[0]:
                        all_data.extend(table[1:])
                    else:
                        all_data.extend(table)

    if not all_data:
        lines = [re.split(r'\s{2,}|\t', line.strip()) for line in text_content.split('\n') if line.strip()]
        if not lines:
            return pd.DataFrame()
        all_data = lines

    all_data = [row for row in all_data if any(val is not None and str(val).strip() != "" for val in row)]
    if not all_data:
        return pd.DataFrame()

    max_cols = max(len(row) for row in all_data)
    normalized_data = []
    for row in all_data:
        padded_row = list(row) + [""] * (max_cols - len(row))
        normalized_data.append(padded_row)

    headers = []
    for i, h in enumerate(normalized_data[0]):
        h_str = str(h).strip()
        headers.append(h_str if h_str else f"COLUNA_{i+1}")

    df = pd.DataFrame(normalized_data[1:], columns=headers)
    return enforce_schema(df, schema_id)

def enforce_schema(df, schema_id=None):
    """
    Ensures the DataFrame follows the target BAT schema.
    """
    schema = get_dynamic_schema(schema_id)
    if not schema:
        # Return as is but cleaned
        for col in df.columns:
            df[col] = df[col].apply(lambda x: str(x).strip() if x is not None else "")
        return df
    
    final_df = pd.DataFrame(columns=schema)
    mapping = get_dynamic_mapping(schema_id)
    
    # Map existing columns to the schema
    for col in df.columns:
        norm_col = normalize_text(str(col))
        target_col = mapping.get(norm_col, norm_col)
        
        # Auto-Fuzzy Mapeamento Inteligente
        if target_col not in schema:
            clean_norm = re.sub(r'[^A-Z0-9]', '', norm_col)
            for s_col in schema:
                clean_s = re.sub(r'[^A-Z0-9]', '', normalize_text(s_col))
                if clean_s == clean_norm:
                    target_col = s_col
                    break
        
        # Se após tudo a coluna mapear para o Schema, injeta ela.
        if target_col in schema:
            if target_col in final_df and not final_df[target_col].isna().all() and not (final_df[target_col] == "").all():
                final_df[target_col] = final_df[target_col].astype(str).str.strip() + " " + df[col].astype(str).str.strip()
            else:
                final_df[target_col] = df[col]
            
    final_df = final_df.fillna("")
    for col in final_df.columns:
        final_df[col] = final_df[col].apply(lambda x: str(x).strip())
        
    return final_df

def apply_bat_rules(df, schema_id=None):
    """
    Applies specific BAT formatting rules based on report type.
    """
    df.columns = [normalize_text(c) for c in df.columns]
    
    for col in df.columns:
        df[col] = df[col].apply(normalize_text)
        
        if any(keyword in col for keyword in ['CPF', 'CNPJ', 'DOCUMENTO']):
            df[col] = df[col].apply(clean_mask)
            
        if any(keyword in col for keyword in ['VALOR', 'PRECO', 'TOTAL', 'CUSTO']):
            df[col] = df[col].apply(format_currency)
            
        if any(keyword in col for keyword in ['DATA', 'VENCIMENTO', 'EMISSAO']):
            df[col] = df[col].apply(format_date)
            
    return df

def audit_csv_classic(pdf_file, csv_file):
    """
    Classic rigid auditor that just tries to extract and shape-compare the dataframes.
    If the extracted rows don't match the CSV, it assumes error and throws the "re-extracted" pdf as fix.
    """
    pdf_file.seek(0)
    df_pdf = extract_pdf_data(pdf_file, schema_id=None)
    pdf_file.seek(0)
    
    csv_file.seek(0)
    try:
        # Detect delimiter simply
        head = csv_file.read(1024).decode('utf-8', errors='ignore')
        sep = ';' if ';' in head else ','
        csv_file.seek(0)
        df_csv = pd.read_csv(csv_file, sep=sep, encoding='utf-8')
    except Exception:
        df_csv = pd.DataFrame()
        
    csv_file.seek(0)
    
    if df_pdf.empty and df_csv.empty:
        return {"status": "perfect"}
        
    if df_csv.shape == df_pdf.shape:
        # It's identical in dimensions, we assume it's correct for classic standard.
        return {"status": "perfect"}
        
    # Erro! Retorna a extração corrigida.
    return df_pdf
