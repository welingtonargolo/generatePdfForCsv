import os
import sys
import django

# Set up Django environment
sys.path.append('/root/generatePdfForCsv')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from converter.models import MappingRule, ReportSchema

def seed():
    # Default Mapping Rules
    rules = {
        'COD INTERNO': 'CODIGO',
        'CODIGO': 'CODIGO',
        'REF': 'CODIGO',
        'REFERENCIA': 'CODIGO',
        'DESCRICAO': 'DESCRICAO',
        'NOME': 'DESCRICAO',
        'PRODUTO': 'DESCRICAO',
        'NCM': 'NCM',
        'CFOP': 'CFOP',
        'CST': 'CST',
        'UNID': 'UNIDADE',
        'UNIDADE': 'UNIDADE',
        'QTD ESTOQUE': 'ESTOQUE',
        'QTD': 'ESTOQUE',
        'ESTOQUE': 'ESTOQUE',
        'VLR CUSTO': 'PRECO_CUSTO',
        'CUSTO': 'PRECO_CUSTO',
        'PRECO CUSTO': 'PRECO_CUSTO',
        'VLR VENDA': 'PRECO_VENDA',
        'PRECO': 'PRECO_VENDA',
        'PRECO VENDA': 'PRECO_VENDA',
        'VALOR': 'PRECO_VENDA',
        'ALIQ ICMS': 'ICMS',
        'ALIQ IPI': 'IPI',
        'CPF': 'CPF_CNPJ',
        'CNPJ': 'CPF_CNPJ',
    }
    
    for src, target in rules.items():
        MappingRule.objects.get_or_create(source_key=src, defaults={'target_key': target})
    
    # Default Report Schemas
    schemas = {
        'produtos': 'CODIGO, DESCRICAO, UNIDADE, ESTOQUE, PRECO_CUSTO, PRECO_VENDA, NCM, CFOP, CST, ICMS, IPI',
        'clientes': 'CODIGO, DESCRICAO, CPF_CNPJ, ENDERECO, CIDADE, UF, TELEFONE, EMAIL',
        'fornecedores': 'CODIGO, DESCRICAO, CPF_CNPJ, ENDERECO, TELEFONE',
    }
    
    for r_type, cols in schemas.items():
        ReportSchema.objects.get_or_create(report_type=r_type, defaults={'columns': cols})

    print("Seed complete.")

if __name__ == '__main__':
    seed()
