"""Login de familias por telefone + codigo enviado via WhatsApp.

Sem senha: quem prova que tem acesso ao numero de WhatsApp cadastrado numa
inscricao consegue entrar e ver/editar essa inscricao depois, de qualquer
aparelho. Reaproveita app/whatsapp.py:enviar_whatsapp para o envio do codigo.
"""

import datetime as dt
import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app import config, models
from app.database import get_db


def gerar_codigo() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


# Tentativas erradas de codigo por telefone. Fica em memoria: vale para uma
# instancia e zera quando o servidor reinicia.
_erros_de_codigo: dict[str, list[dt.datetime]] = {}


def _erros_recentes(telefone: str) -> list[dt.datetime]:
    limite = dt.datetime.utcnow() - dt.timedelta(minutes=config.LOGIN_JANELA_MINUTOS)
    recentes = [t for t in _erros_de_codigo.get(telefone, []) if t > limite]
    if recentes:
        _erros_de_codigo[telefone] = recentes
    else:
        _erros_de_codigo.pop(telefone, None)
    return recentes


def garantir_tentativas_disponiveis(telefone: str) -> None:
    if len(_erros_recentes(telefone)) >= config.LOGIN_MAX_ERROS:
        raise HTTPException(429, "Muitas tentativas. Aguarde alguns minutos.")


def registrar_erro_de_codigo(telefone: str) -> None:
    _erros_de_codigo[telefone] = _erros_recentes(telefone) + [dt.datetime.utcnow()]


def limpar_erros_de_codigo(telefone: str) -> None:
    _erros_de_codigo.pop(telefone, None)


def pode_pedir_codigo(db: Session, telefone: str) -> bool:
    limite = dt.datetime.utcnow() - dt.timedelta(minutes=config.LOGIN_JANELA_MINUTOS)
    pedidos = (
        db.query(models.CodigoLogin)
        .filter(models.CodigoLogin.telefone == telefone, models.CodigoLogin.created_at > limite)
        .count()
    )
    return pedidos < config.LOGIN_MAX_CODIGOS


def criar_sessao(db: Session, telefone: str) -> models.Sessao:
    sessao = models.Sessao(
        token=secrets.token_urlsafe(32),
        telefone=telefone,
        expira_em=dt.datetime.utcnow() + dt.timedelta(days=config.SESSAO_VALIDADE_DIAS),
    )
    db.add(sessao)
    db.commit()
    db.refresh(sessao)
    return sessao


def obter_telefone_autenticado(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> str:
    """Dependencia FastAPI: le o header 'Authorization: Bearer <token>' e
    devolve o telefone da sessao, ou 401 se ausente/invalido/expirado."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Nao autenticado")
    token = authorization.split(" ", 1)[1].strip()
    sessao = db.get(models.Sessao, token)
    if sessao is None or sessao.expira_em < dt.datetime.utcnow():
        raise HTTPException(401, "Sessao invalida ou expirada")
    return sessao.telefone


def garantir_dono(crianca: models.Crianca, telefone: str) -> None:
    if crianca.responsavel_telefone != telefone:
        raise HTTPException(403, "Essa inscricao nao pertence a este numero")
