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
    for nome in ("EXPOSE_CHILD_RECORDS", "META_APP_SECRET", "CORS_ORIGINS"):
        monkeypatch.delenv(nome, raising=False)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    importlib.reload(config)
    assert config.ADMIN_API_KEY == ""
    assert config.ACCEPT_REGISTRATIONS is False
    assert config.EXPOSE_CHILD_RECORDS is False
    assert config.META_APP_SECRET == ""
    assert "*" not in config.CORS_ORIGINS


POR_CRIANCA = [
    ("get", "/motor/programa?programa=x%7Cy%7Cz"),
    ("get", "/motor/crianca/qualquer"),
    ("get", "/motor/criancas-exemplo"),
    ("post", "/motor/reclassificar/qualquer"),
    ("get", "/motor/notificacoes"),
]


def test_registros_por_crianca_bloqueados_por_padrao(client, monkeypatch):
    monkeypatch.setattr("app.config.EXPOSE_CHILD_RECORDS", False)
    for metodo, url in POR_CRIANCA:
        assert getattr(client, metodo)(url).status_code == 403, url


def test_registros_por_crianca_liberados_em_ambiente_local(client, monkeypatch):
    monkeypatch.setattr("app.config.EXPOSE_CHILD_RECORDS", True)
    for metodo, url in POR_CRIANCA:
        assert getattr(client, metodo)(url).status_code != 403, url


def _sessao(db_session, telefone):
    from app import auth
    return {"Authorization": f"Bearer {auth.criar_sessao(db_session, telefone).token}"}


def test_recomendacoes_exigem_sessao_do_responsavel(client, db_session, dados):
    url = "/classificacao/1/recomendacoes"
    assert client.get(url).status_code == 401
    assert client.get(url, headers=_sessao(db_session, "+5500000000001")).status_code == 403
    assert client.get(url, headers=_sessao(db_session, "+5500000000000")).status_code == 200


def _codigo(db_session, telefone):
    return (
        db_session.query(models.CodigoLogin)
        .filter(models.CodigoLogin.telefone == telefone)
        .order_by(models.CodigoLogin.created_at.desc())
        .first()
    )


def test_codigo_de_login_tem_limite_de_tentativas_e_de_pedidos(client, db_session, dados):
    telefone = "+5500000000000"
    for _ in range(10):
        assert client.post("/auth/solicitar-codigo", json={"telefone": telefone}).status_code == 200
    assert db_session.query(models.CodigoLogin).count() == 3  # mesma resposta, sem novos envios

    certo = _codigo(db_session, telefone).codigo
    errado = "000000" if certo != "000000" else "111111"
    for _ in range(5):
        resp = client.post("/auth/verificar-codigo", json={"telefone": telefone, "codigo": errado})
        assert resp.status_code == 400
    # depois de 5 erros, nem o codigo certo entra
    resp = client.post("/auth/verificar-codigo", json={"telefone": telefone, "codigo": certo})
    assert resp.status_code == 429


@pytest.mark.parametrize("segredo,assinatura", [
    ("segredo-de-app-somente-de-teste", None),
    ("segredo-de-app-somente-de-teste", "sha256=" + "0" * 64),
    ("", "sha256=" + "0" * 64),
])
def test_webhook_sem_assinatura_valida_nao_processa(client, db_session, dados, monkeypatch, segredo, assinatura):
    monkeypatch.setattr("app.config.META_APP_SECRET", segredo)
    antes = _estado(db_session)
    payload = {"entry": [{"changes": [{"value": {"messages": [
        {"from": "5500000000000", "text": {"body": "status"}}]}}]}]}
    headers = {"X-Hub-Signature-256": assinatura} if assinatura else None
    resp = client.post("/whatsapp/webhook", json=payload, headers=headers)
    assert resp.status_code == 403
    assert NOME not in resp.text
    assert _estado(db_session) == antes


def test_verificacao_do_webhook_exige_token_configurado(client, monkeypatch):
    monkeypatch.setattr("app.config.META_VERIFY_TOKEN", "")
    resp = client.get("/whatsapp/webhook?hub.mode=subscribe&hub.verify_token=&hub.challenge=1")
    assert resp.status_code == 403


def test_cors_so_libera_origens_conhecidas(client):
    def permitido(origem):
        return client.options("/health", headers={
            "Origin": origem, "Access-Control-Request-Method": "GET",
        }).headers.get("access-control-allow-origin")

    assert permitido("https://r15n-eng.github.io") == "https://r15n-eng.github.io"
    assert permitido("http://localhost:8080") == "http://localhost:8080"
    assert permitido("https://site-qualquer.example") is None
    assert permitido("http://localhost.example.com") is None
