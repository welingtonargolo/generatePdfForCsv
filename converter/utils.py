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
PRIMARY_KEYS = ['CODIGO', 'COD INTERNO', 'REF', 'REFERENCIA', 'CPF', 'CNPJ', 'NOME']

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
    
    # Merge custom separators with default primary keys
    separators = PRIMARY_KEYS + (custom_separators or [])
    separators = [normalize_text(s) for s in separators]
    
    mapping = get_dynamic_mapping()
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Extract KEY: VALUE pattern (only split on the FIRST colon)
        if ':' in line:
            parts = line.split(':', 1)
            raw_key = parts[0].strip()
            value = parts[1].strip()
            
            key_norm = normalize_text(raw_key)
            standard_key = mapping.get(key_norm, key_norm)

            # Record separation logic:
            # 1. Physical separator (dashes)
            # 2. Key is a primary key and is already present in the current_record
            if '---' in line or (key_norm in separators and standard_key in current_record):
                if current_record:
                    records.append(current_record)
                current_record = {}
                if '---' in line:
                    continue

            current_record[standard_key] = value
        else:
            # If it doesn't match KEY: VALUE, and we have an ongoing record, 
            # append to the last seen field (usually a wrap-around description)
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
        for page in pdf.pages:
            text_content += (page.extract_text() or "") + "\n"

    # PRIORITY: Clean text content from ignore patterns before parsing
    if ignore_patterns:
        for pattern in ignore_patterns:
            text_content = text_content.replace(pattern, "")

    # PRIORITIZE KV Parser if density is high
    if is_kv_format(text_content):
        kv_records = parse_key_value_text(text_content, magic_keywords)
        if kv_records:
            df = pd.DataFrame(kv_records)
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
        # Final resort Strategy 2: Text splitting by columns
        lines = [re.split(r'\s{2,}|\t', line.strip()) for line in text_content.split('\n') if line.strip()]
        if not lines:
            return pd.DataFrame()
        all_data = lines

    # Robust table cleaning and DataFrame creation
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
    
    # Create a new DF with the schema columns
    final_df = pd.DataFrame(columns=schema)
    mapping = get_dynamic_mapping()
    
    # Map existing columns to the schema
    for col in df.columns:
        norm_col = normalize_text(col)
        target_col = mapping.get(norm_col, norm_col)
        
        if target_col in schema:
            final_df[target_col] = df[col]
        else:
            # Add unmapped columns to the end
            final_df[col] = df[col]
            
    # Clean results
    final_df = final_df.fillna("")
    for col in final_df.columns:
        # Final cleanup: trim and remove artifacts
        final_df[col] = final_df[col].apply(lambda x: str(x).strip())
        
    return final_df

def apply_bat_rules(df, report_type):
    """
    Applies specific BAT formatting rules based on report type.
    """
    # Normalize all column names
    df.columns = [normalize_text(c) for c in df.columns]
    
    # Generic cleaning
    for col in df.columns:
        # Normalize text content
        df[col] = df[col].apply(normalize_text)
        
        # Identify masks (CPF/CNPJ-like)
        if any(keyword in col for keyword in ['CPF', 'CNPJ', 'DOCUMENTO']):
            df[col] = df[col].apply(clean_mask)
            
        # Identify currency
        if any(keyword in col for keyword in ['VALOR', 'PRECO', 'TOTAL', 'CUSTO']):
            df[col] = df[col].apply(format_currency)
            
        # Identify dates
        if any(keyword in col for keyword in ['DATA', 'VENCIMENTO', 'EMISSAO']):
            df[col] = df[col].apply(format_date)
            
    return df
