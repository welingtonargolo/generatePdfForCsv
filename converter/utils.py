import pdfplumber
import pandas as pd
import re
import unicodedata
from io import BytesIO

from .models import MappingRule, ReportSchema

def get_dynamic_mapping():
    """Fetches mapping rules from the database."""
    return {rule.source_key: rule.target_key for rule in MappingRule.objects.all()}

def get_dynamic_schema(report_type):
    """Fetches report schema from the database."""
    schema_obj = ReportSchema.objects.filter(report_type=report_type).first()
    return schema_obj.get_column_list() if schema_obj else []

# Keys that usually indicate a new record starts
PRIMARY_KEYS = ['CODIGO', 'COD INTERNO', 'REF', 'REFERENCIA', 'CPF', 'CNPJ', 'DOCUMENTO', 'NOME', 'CLIENTE']

def normalize_text(text):
    if not isinstance(text, str):
        return text
    # Uppercase
    text = text.upper()
    # Remove accents
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    return text.strip()

def clean_mask(text):
    if not isinstance(text, str):
        return text
    # Remove dots, dashes, slashes (CPF/CNPJ)
    return re.sub(r'[\.\-\/]', '', text).strip()

def format_currency(text):
    if not isinstance(text, str):
        return text
    # Remove R$ and white space
    text = text.replace('R$', '').strip()
    # Replace dots (thousands) with empty and comma (decimal) with dots
    # Example: 1.234,56 -> 1234.56
    text = text.replace('.', '').replace(',', '.')
    try:
        return float(text)
    except ValueError:
        return text

def format_date(text):
    if not isinstance(text, str):
        return text
    # Try common formats and return YYYY-MM-DD for BAT
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return pd.to_datetime(text, format=fmt).strftime('%Y-%m-%d')
        except:
            continue
    return text

def parse_multi_key_value_block(text, start_keyword):
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
    
    mapping = get_dynamic_mapping()
    
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

def parse_key_value_text(text, custom_separators=None):
    """
    Parses "ugly" text reports formatted as KEY: VALUE lists.
    Flattens fields into professional records.
    """
    records = []
    current_record = {}
    
    separators = PRIMARY_KEYS + (custom_separators or [])
    separators = [normalize_text(s) for s in separators]
    
    mapping = get_dynamic_mapping()
    
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

def extract_pdf_data(file_obj, report_type='generic', magic_keywords=None, ignore_patterns=None):
    """
    Extracts tabular data from a PDF file using multiple fallback strategies and robust alignment.
    """
    all_data = []
    text_content = ""
    
    with pdfplumber.open(file_obj) as pdf:
        # Some broken textual pages might not return anything with default parameters
        # However, for pure text layout preserving, extract_text usually handles properly
        for page in pdf.pages:
            text_content += (page.extract_text() or "") + "\n"

    if ignore_patterns:
        for pattern in ignore_patterns:
            # Pattern regex replace or static replace
            try:
                # If pattern represents regex (like 'Pagina \d')
                text_content = re.sub(pattern, "", text_content, flags=re.IGNORECASE)
            except Exception:
                text_content = text_content.replace(pattern, "")

    # PRIORITIZE Block Parser if user provided magic_keyword
    if magic_keywords and isinstance(magic_keywords, list) and len(magic_keywords) > 0:
        for start_kw in magic_keywords:
            if start_kw.strip():
                block_records = parse_multi_key_value_block(text_content, start_kw)
                if block_records:
                    df = pd.DataFrame(block_records)
                    return enforce_schema(df, report_type)

    # PRIORITIZE KV Parser if density is high
    if is_kv_format(text_content):
        kv_records = parse_key_value_text(text_content, magic_keywords)
        if kv_records:
            df = pd.DataFrame(kv_records)
            return enforce_schema(df, report_type)

    # STANDBY: Try Block parser with default 'CLIENTE', 'CODIGO', 'NOME'
    for guess_kw in ['CLIENTE:', 'CLIENTE Nº', 'CODIGO:', 'NOME:']:
        block_records = parse_multi_key_value_block(text_content, guess_kw)
        if block_records and len(block_records) > 0 and len(block_records[0].keys()) > 1:
            df = pd.DataFrame(block_records)
            return enforce_schema(df, report_type)

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
    return enforce_schema(df, report_type)

def enforce_schema(df, report_type):
    """
    Ensures the DataFrame follows the standard BAT schema for the report type.
    """
    schema = get_dynamic_schema(report_type)
    if not schema:
        # Return as is but cleaned
        for col in df.columns:
            df[col] = df[col].apply(lambda x: str(x).strip() if x is not None else "")
        return df
    
    final_df = pd.DataFrame(columns=schema)
    mapping = get_dynamic_mapping()
    
    # Map existing columns to the schema
    for col in df.columns:
        norm_col = normalize_text(str(col))
        target_col = mapping.get(norm_col, norm_col)
        
        # Auto-Fuzzy Mapeamento Inteligente
        # Se não mapeou direto, tentamos remover caracteres especiais (ex: "CPF / CNPJ" -> "CPFCNPJ" -> "CPF_CNPJ")
        if target_col not in schema:
            clean_norm = re.sub(r'[^A-Z0-9]', '', norm_col)
            for s_col in schema:
                clean_s = re.sub(r'[^A-Z0-9]', '', normalize_text(s_col))
                if clean_s == clean_norm:
                    target_col = s_col
                    break
        
        # Se após tudo a coluna mapear para o Schema, injeta ela. Senão, DROPA o "lixo".
        if target_col in schema:
            # Se já existir algo preenchido nessa coluna, junta com espaço para não sobreescrever
            if target_col in final_df and not final_df[target_col].isna().all() and not (final_df[target_col] == "").all():
                final_df[target_col] = final_df[target_col].astype(str).str.strip() + " " + df[col].astype(str).str.strip()
            else:
                final_df[target_col] = df[col]
            
    final_df = final_df.fillna("")
    for col in final_df.columns:
        final_df[col] = final_df[col].apply(lambda x: str(x).strip())
        
    return final_df

def apply_bat_rules(df, report_type):
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
