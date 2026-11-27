"""Travas de seguranca do prototipo. Tudo aqui bloqueia por padrao.

- exigir_admin: rotas de manutencao (alteram ou devolvem inscricoes de terceiros)
  exigem o header X-Admin-Key igual a ADMIN_API_KEY. Sem a variavel, ninguem passa.
- exigir_inscricoes_abertas: nenhuma rota que cria inscricao funciona a menos que
  ACCEPT_REGISTRATIONS=true. O deploy publico deve ficar sem essa variavel.
"""

import secrets

from fastapi import Header, HTTPException

from app import config


def exigir_admin(x_admin_key: str | None = Header(default=None)) -> None:
    chave = config.ADMIN_API_KEY
    if not chave or not x_admin_key or not secrets.compare_digest(x_admin_key.encode(), chave.encode()):
        raise HTTPException(403, "Rota restrita")


def exigir_inscricoes_abertas() -> None:
    if not config.ACCEPT_REGISTRATIONS:
        raise HTTPException(403, "Prototipo de demonstracao: novas inscricoes estao desativadas")
