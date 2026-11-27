"""As travas precisam bloquear por padrao. Aqui voltamos para a configuracao
padrao (sem ADMIN_API_KEY e com inscricoes fechadas) e conferimos cada rota."""

import pytest

from app import models

ADMIN = [
    ("post", "/programas", {"nome": "Creche X", "bairro": "Bangu", "capacidade": 1}),
    ("delete", "/inscricao/1", None),
    ("delete", "/inscricao/1?confirmar=true", None),
    ("post", "/avancar_processo", {"crianca_id": 1, "novo_status": "cancelado"}),
    ("post", "/whatsapp/enviar_convocacao/1", None),
    ("post", "/jobs/verificar_telefones", None),
]
REGISTRATION = [
    ("post", "/inscricao", {}),
    ("post", "/whatsapp/webhook", {"entry": []}),
]
NOME = "Crianca Ficticia"


@pytest.fixture()
def dados(db_session):
    db_session.add(models.Programa(nome="Creche A", bairro="Bangu", capacidade=1))
    db_session.add(models.Crianca(
        nome=NOME, data_nascimento="2024-01-01", responsavel_nome="Responsavel Ficticio",
        responsavel_telefone="+5500000000000", bairro="Bangu",
    ))
    db_session.commit()


def _estado(db_session):
    db_session.expire_all()
    return (
        db_session.query(models.Programa).count(),
        [(c.id, c.status) for c in db_session.query(models.Crianca).all()],
        db_session.query(models.Notificacao).count(),
    )


def _chamar(client, metodo, url, corpo, headers=None):
    kwargs = {"headers": headers} if headers else {}
    if corpo is not None:
        kwargs["json"] = corpo
    return getattr(client, metodo)(url, **kwargs)


@pytest.mark.parametrize("chave_configurada,chave_enviada", [
    ("", None),                       # padrao: sem chave no servidor
    ("", ""),                         # chave vazia nunca libera
    ("", "qualquer"),
    ("chave-do-servidor", None),
    ("chave-do-servidor", "errada"),
])
def test_rotas_de_manutencao_bloqueadas(client, db_session, dados, monkeypatch, chave_configurada, chave_enviada):
    monkeypatch.setattr("app.config.ADMIN_API_KEY", chave_configurada)
    client.headers.pop("X-Admin-Key")
    antes = _estado(db_session)
    for metodo, url, corpo in ADMIN:
        headers = {"X-Admin-Key": chave_enviada} if chave_enviada is not None else None
        resp = _chamar(client, metodo, url, corpo, headers)
        assert resp.status_code == 403, url
        assert NOME not in resp.text, url
    assert _estado(db_session) == antes


def test_inscricoes_fechadas_por_padrao(client, db_session, dados, monkeypatch):
    monkeypatch.setattr("app.config.ACCEPT_REGISTRATIONS", False)
    antes = _estado(db_session)
    for metodo, url, corpo in REGISTRATION:
        assert _chamar(client, metodo, url, corpo).status_code == 403, url
    assert _estado(db_session) == antes


def test_padrao_do_codigo_e_bloquear(monkeypatch):
    import importlib
    import dotenv
    from app import config

    monkeypatch.delenv("ADMIN_API_KEY", raising=False)
    monkeypatch.delenv("ACCEPT_REGISTRATIONS", raising=False)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    importlib.reload(config)
    assert config.ADMIN_API_KEY == ""
    assert config.ACCEPT_REGISTRATIONS is False
