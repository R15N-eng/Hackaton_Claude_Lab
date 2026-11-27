import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./creche.db")

# WhatsApp Cloud API (Meta) -- ver app/whatsapp.py para onde obter cada um.
META_WHATSAPP_TOKEN = os.getenv("META_WHATSAPP_TOKEN", "")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID", "")
META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "")

# Seguranca: as duas opcoes abaixo BLOQUEIAM por padrao (ver app/guards.py).
# Chave das rotas de manutencao. Vazia = rotas desativadas.
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")
# Aceitar novas inscricoes (site e webhook). Use apenas em ambiente local, com dados ficticios.
ACCEPT_REGISTRATIONS = os.getenv("ACCEPT_REGISTRATIONS", "false").lower() == "true"
# Rotas do motor que devolvem registros crianca a crianca da base anonimizada
# (telas Familia e SME). Ligue so em ambiente local.
EXPOSE_CHILD_RECORDS = os.getenv("EXPOSE_CHILD_RECORDS", "false").lower() == "true"
# Segredo do app na Meta, usado para conferir a assinatura do webhook. Vazio = webhook recusa tudo.
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
# Sites que podem chamar a API pelo navegador (localhost em qualquer porta e sempre permitido).
CORS_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "https://r15n-eng.github.io").split(",") if o.strip()
]

# Login: limite de codigos pedidos e de tentativas erradas por telefone, por janela.
LOGIN_JANELA_MINUTOS = 15
LOGIN_MAX_CODIGOS = 3
LOGIN_MAX_ERROS = 5

ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "false").lower() == "true"

# Janela em dias que o responsavel tem para trocar a unidade escolhida.
JANELA_TROCA_DIAS = int(os.getenv("JANELA_TROCA_DIAS", "7"))

# Intervalo do job de verificacao mensal de telefone (dias).
INTERVALO_VERIFICACAO_TELEFONE_DIAS = int(
    os.getenv("INTERVALO_VERIFICACAO_TELEFONE_DIAS", "30")
)

# Prazo (a partir da convocacao/escolha da unidade) para a familia comparecer
# e matricular a crianca presencialmente. Usado em GET /status-matricula.
PRAZO_MATRICULA_DIAS = int(os.getenv("PRAZO_MATRICULA_DIAS", "15"))

# Login da familia por telefone + codigo via WhatsApp (ver app/auth.py).
CODIGO_LOGIN_VALIDADE_MINUTOS = int(os.getenv("CODIGO_LOGIN_VALIDADE_MINUTOS", "10"))
SESSAO_VALIDADE_DIAS = int(os.getenv("SESSAO_VALIDADE_DIAS", "90"))
