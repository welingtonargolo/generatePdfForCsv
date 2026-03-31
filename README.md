# 📄 Conversor Inteligente de PDF para CSV (com Integração Google Gemini)

Este é um ecossistema da web avançado criado em **Python (Django)** para solucionar um problema complexo corporativo: **a extração, estruturação e auditoria de dados em relatórios PDF despadronizados**. O objetivo da aplicação é ler PDFs complexos e convertê-los perfeitamente em planilhas CSV estruturadas e auditadas para importação.

O projeto une motores rigorosos de Expressões Regulares com o **estado da arte em Inteligência Artificial**, integrando diretamente a API do **Google Gemini 2.5 Flash** para ler e auditar documentos como um ser humano.

---

## 🎯 Principais Funcionalidades

1. **Gestão Dinâmica de Esquemas:** Crie relatórios personalizados ("Clientes", "Balancete", etc.) sem limites estruturais fixos.
2. **Injeção Rápida via CSV:** Para criar a estrutura de um esquema novo, basta fazer o upload de um CSV Vazio apenas com as colunas-alvo no cabeçalho; o sistema aprende e adapta o banco de dados instantaneamente.
3. **Mapeamento de Regras Aninhadas (De -> Para):** Para cada Esquema de relatório, crie Regras de Normalização isoladas para que o sistema saiba renomear instâncias (`"Documento" -> "CPF_CNPJ"`).
4. **Extração Inteligente por IA:** Envie PDFs massivamente destruídos à IA. Ela analisa as linhas semânticas do arquivo e devolve tudo higienizado no molde do seu Esquema.
5. **Auditor Semântico de CSV:** Um revolucionário validador. Envie o PDF Original e o CSV recém-extraído. O Gemini auditará ativamente para checar se houve omissão de clientes, esmagamento de colunas ou falhas estruturais. Caso encontre um erro, a IA gerará um novo CSV perfeito corrigido na hora!

---

## 🛠️ Tecnologias e Dependências

- **[Python](https://www.python.org/) 3.8+**: Linguagem base do sistema.
- **[Django](https://www.djangoproject.com/)**: Framework web robusto responsável pelas views, rotas e Modelos Dinâmicos.
- **[pdfplumber](https://github.com/jsvine/pdfplumber)**: Biblioteca poderosa voltada para a mineração minuciosa de textos de PDFs reais.
- **[pandas](https://pandas.pydata.org/)**: Motor oficial de manipulação e higienização das matrizes CSV exportadas.
- **[requests](https://pypi.org/project/requests/)**: Comunicação HTTPS direta e otimizada com a Cloud do Google Generative AI REST API.

---

## 💻 Instalação Passo a Passo

1. **Ambiente Virtual e Dependências:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # (Linux/Mac)
   venv\Scripts\activate     # (Windows)
   pip install -r requirements.txt
   ```
2. **Setup do Banco de Dados (Post-Refactor):**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
3. **Rodar o Servidor:**
   ```bash
   python manage.py runserver
   ```
   Acesse: `http://localhost:8000`

---

## 🚀 Fluxo Principal de Utilização

### Passo 1: Configurar a Estrutura (Aba Configurações)
- Acesse a Engrenagem no canto superior direito.
- Crie um **Novo Esquema** dando-lhe um nome customizado.
- Faça o upload de um modelo `.csv` que conteha no cabeçalho quais colunas o sistema deverá obedecer ao cuspir o resultado.
- Preencha as Sub-Regras (Dicionário de Transformação) apenas se necessitar padronizar nomenclaturas de forma estrita.

### Passo 2: O Conversor (Página Inicial)
- Escolha entre a abordagem "Palavra-Chave (Clássica)" ou ative o super-modo da IA.
- A IA extrairá e forçará o dado a engatar nas colunas do Esquema definido no Passo 1, gerando o download na tela via Fetch.

### Passo 3: O Auditor (Aba Auditor IA)
- Ferramenta de Controle de Qualidade fina.
- Faça o *Cross-Check* subindo o PDF com o Resultado convertido para garantir que não houve uma mínima quebra de dados no transporte.

---

## 📂 Arquitetura Descomplicada (Para Desenvolvedores)
- **`models.py / admin.py`**: Modelos Relacionais usando `ForeignKey` para isolar Regras (`MappingRule`) dentro de seus próprios Gabaritos (`ReportSchema`), eliminando o limitador de Hardcoded Enums.
- **`utils.py / ai_extraction.py`**: Encanamento de dados em memória. A Extração recebe o ID de esquema via FK Query e molda os DataFrames limitando-se aos Arrays injetados.
- **`views.py`**: Controladores de requisições AJAX com proteções severas aos Contextos Globais usando Fetch Headers Dinâmicos (`document.write` DOM Replacement).
