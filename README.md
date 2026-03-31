# 📄 Conversor Inteligente de PDF para CSV (com Integração Google Gemini)

Este é um sistema da web avançado criado em **Python (Django)** desenvolvido para solucionar um problema complexo: **a extração e estruturação de dados em relatórios PDF "caóticos" e despadronizados**. O objetivo da aplicação é ler PDFs impossíveis de serem copiados manualmente e convertê-los perfeitamente em planilhas CSV estruturadas, já mapeadas para a importação em sistemas corporativos (como o sistema BAT).

O projeto une o clássico parseamento baseado em expressões regulares (*Stream Block Parsing*) com o **estado da arte em Inteligência Artificial**, integrando diretamente a API do **Google Gemini** para ler relatórios complexos de "forma humana".

---

## 🎯 Principais Funcionalidades

1. **Extração de Texto Complexo (Block Parsing):** Quebra textos embaralhados, campos divididos em múltiplas linhas e ruídos, reconstruindo os dados através de *Fuzzy Matching* de Palavras-Chave.
2. **Extração Inteligente por IA (Google Gemini 2.5 Flash):** Quando a extração regular falha por conta do caos no PDF, o sistema envia o documento à IA, que analisa semanticamente o arquivo e devolve os dados perfeitamente em formato JSON estruturado, convertendo-o para CSV.
3. **Mapeamento de Regras Dinâmico:** Um painel de configurações (Settings) onde o usuário define que a coluna extraída como `"Documento"` no PDF deve se transformar em `"CPF_CNPJ"` no CSV final, adequando as saídas aos requisitos de outros softwares.
4. **Schemas de Relatório Rigorosos:** Aplicação de colunas obrigatórias com base no tipo de relatório (`Clientes`, `Vendas`, `Produtos`).

---

## 🛠️ Tecnologias e Dependências

O projeto utiliza bibliotecas consagradas para manipulação e visualização de dados:

- **[Python](https://www.python.org/) 3.8+**: Linguagem base do sistema.
- **[Django](https://www.djangoproject.com/)**: Framework web robusto responsável pelas rotas, modelos de banco de dados (SQLite) e views.
- **[pdfplumber](https://github.com/jsvine/pdfplumber)**: Biblioteca poderosa voltada para a mineração minuciosa de textos e tabelas reais de arquivos PDF, preservando o layout.
- **[pandas](https://pandas.pydata.org/)**: A mais popular biblioteca de manipulação de dados em Python. Utilizada aqui para reconstruir tabelas, higienizar dados e gerenciar os DataFrames antes de exportar o arquivo CSV CSV.
- **[requests](https://pypi.org/project/requests/)**: Utilizada para comunicação com as APIs externas (Google Generative AI/Gemini REST API) através de requisições HTTP seguras.
- **[django-bootstrap5](https://pypi.org/project/django-bootstrap5/)**: Fornece componentes e integração direta entre Django Templates e o design responsivo do Bootstrap 5.

---

## 💻 Instalação Passo a Passo

O sistema é universal e funciona perfeitamente em sistemas baseados em Windows, macOS e Linux. Siga as instruções abaixo para a sua máquina.

### Pré-requisitos
- Ter o **Python** instalado (versão 3.8 ou superior).
- Acesso ao terminal / prompt de comando.

### 🐧 Instalação no Linux / macOS

1. **Abra o terminal e acesse a pasta do projeto:**
   ```bash
   cd /caminho/para/generatePdfForCsv
   ```
2. **Crie um Ambiente Virtual (Isolamento de dependências):**
   ```bash
   python3 -m venv venv
   ```
3. **Ative o Ambiente Virtual:**
   ```bash
   source venv/bin/activate
   ```
4. **Instale as Bibliotecas:**
   ```bash
   pip install -r requirements.txt
   ```
5. **Realize as migrações do Banco de Dados:**
   ```bash
   python3 manage.py migrate
   ```
6. **Crie um Usuário Administrador (Opcional, para acessar /admin):**
   ```bash
   python3 manage.py createsuperuser
   ```
7. **Rode o Servidor:**
   ```bash
   python3 manage.py runserver
   ```
   > Acesse: `http://localhost:8000` no seu navegador.

---

### 🪟 Instalação no Windows

1. **Abra o PowerShell ou Prompt de Comando e acesse a pasta:**
   ```cmd
   cd \caminho\para\generatePdfForCsv
   ```
2. **Crie o Ambiente Virtual:**
   ```cmd
   python -m venv venv
   ```
3. **Ative o Ambiente Virtual:**
   ```cmd
   venv\Scripts\activate
   ```
   *(Pode ser necessário executar `Set-ExecutionPolicy Unrestricted -Scope CurrentUser` caso o Windows bloqueie a ativação do ambiente virtual).*
4. **Instale as dependências requisitadas:**
   ```cmd
   pip install -r requirements.txt
   ```
5. **Aplique as Migrações da Base de Dados:**
   ```cmd
   python manage.py migrate
   ```
6. **Inicie a Aplicação:**
   ```cmd
   python manage.py runserver
   ```
   > Acesse: `http://localhost:8000` no seu navegador.

---

## 🚀 Como Usar o Sistema - Tutorial Completo

O fluxo de uso foi pensado para ser o mais intuitivo possível, concentrando-se em duas abordagens de conversão na tela principal.

### Método 1: Via Palavra-Chave (Extração Clássica)
Recomendado para relatórios visualmente de "blocos" contínuos em vez de tabelas (ex: Históricos onde cada cliente ocupa 3 linhas de texto).
1. Faça o **upload do arquivo PDF** pelo botão primário.
2. Selecione o **Tipo de Relatório** (ex: Clientes).
3. Na caixa **Palavra-Chave Manual**, digite o gatilho que repete antes de todo registro (Ex: `Cliente:` ou `Código:`).
4. *(Opcional)* Se o seu PDF tiver muita poluição (ex: "Página 1", "SISTEMA XPTO"), escreva esses padrões na caixa **"Ignorar (Opcional)"** (como: `Página, ---`).
5. Clique em **Converter PDF**. O resultado será um CSV formatado baixado automaticamente!

### Método 2: Extração Inteligente com a IA Gemini
Recomendado para PDFs *"caóticos"* com quebra de palavras, múltiplas colunas na mesma linha, e informações misturadas aleatoriamente.
1. No painel iluminado abaixo, ative o switch: **"Usar Extração Inteligente com a IA Gemini"**.
2. **Chave de API:** Se for seu primeiro acesso, cole sua Google API Key (Pode ser adquirida de graça no [Google AI Studio](https://aistudio.google.com/)). Nas próximas vezes, ela já estará gravada, graças ao nosso salvamento de backend!
   *(Observação: Ao ativar a IA, as opções de Palavra-Chave e Ignorar Padrões são desabilitadas, pois a inteligência não precisa de ajuda para entender qual informação importa e qual é ruído visual).*
3. Clique em **Converter PDF**. 
   - A interface mudará para um painel descritivo e *Real-time* guiando os estágios de raciocínio da IA (*Ex: "Lendo o PDF..." -> "Estruturando Colunas..."*).
4. O CSV perfeitamente inteligível e higienizado sairá magicamente, baixado de forma automática via requisições AJAX!

---

### ⚙️ Painel de Configurações (Settings)
Acessível pelo menu lateral no topo do site (se autenticado ou na rota `/settings/`).
Neste local, você pode predefinir **Regras de Encadeamento de Nomenclatura**.
- **Regras de Mapeamento**: Exemplo prático: Digamos que a IA encontra e extraia a coluna `"Telefone Celular"`, mas o programa BAT onde o CSV vai ser importado aceita apenas `"CELULAR"`. Vá em Regras de Mapeamento e defina: `Source KEY: Telefone Celular`, `Target KEY: CELULAR`. Da próxima vez, a tabela será higienizada automaticamente!
- **Schema de Relatórios**: Permite estabelecer explicitamente quais colunas "devem existir" numa conversão de Cliente, forçando dados faltantes a ficarem em branco e ordenando-os corretamente.

---

## 📂 Arquitetura Descomplicada (Para Desenvolvedores)
- **`utils.py`**: Motor de extração crua e expressões regulares de formatação customizada (`Continuous Stream Block Parsing`).
- **`ai_extraction.py`**: Pipeline integrado comunicante com o Google AI via HTTP POST. Responsável por aplicar *Prompt Engineering* nas extrações enviando o *database schema* associado e parseando o JSON devolvido.
- **`views.py`**: O Cérebro da Web. Trata requisições assíncronas AJAX do React/Vanilla JS do frontend, valida o forms, gerencia o BD e entrega o payload em memória (XHR Blob / CSV) via Python `BytesIO` - sem gravar cópias no disco, garantindo performance total.
- **`models.py / admin.py`**: Relacionamento das Entidades, salvamento de Chaves de API de sessões e administração do Django.
