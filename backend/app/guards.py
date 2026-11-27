"""Travas de seguranca do prototipo. Tudo aqui bloqueia por padrao.

- exigir_admin: rotas de manutencao (alteram ou devolvem inscricoes de terceiros)
  exigem o header X-Admin-Key igual a ADMIN_API_KEY. Sem a variavel, ninguem passa.
- exigir_inscricoes_abertas: nenhuma rota que cria inscricao funciona a menos que
  ACCEPT_REGISTRATIONS=true. O deploy publico deve ficar sem essa variavel.
"""

import hashlib
import hmac
import secrets

from fastapi import Header, HTTPException, Request

from app import config


def exigir_admin(x_admin_key: str | None = Header(default=None)) -> None:
    chave = config.ADMIN_API_KEY
    if not chave or not x_admin_key or not secrets.compare_digest(x_admin_key.encode(), chave.encode()):
        raise HTTPException(403, "Rota restrita")


def exigir_inscricoes_abertas() -> None:
    if not config.ACCEPT_REGISTRATIONS:
        raise HTTPException(403, "Prototipo de demonstracao: novas inscricoes estao desativadas")


def exigir_dados_individuais() -> None:
    if not config.EXPOSE_CHILD_RECORDS:
        raise HTTPException(403, "Prototipo de demonstracao: registros por crianca estao desativados")


async def exigir_assinatura_meta(
    request: Request, x_hub_signature_256: str | None = Header(default=None)
) -> None:
    """A Meta assina cada POST com HMAC-SHA256 do corpo, usando o segredo do app."""
    segredo = config.META_APP_SECRET
    if not segredo or not x_hub_signature_256:
        raise HTTPException(403, "Assinatura ausente ou webhook nao configurado")
    esperado = "sha256=" + hmac.new(segredo.encode(), await request.body(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(esperado.encode(), x_hub_signature_256.encode()):
        raise HTTPException(403, "Assinatura invalida")
