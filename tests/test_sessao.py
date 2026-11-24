"""Testes da sessão por rodada. Abrem o Chromium contra um servidor local com login por cookie,
que conta quantas vezes o formulário de login foi enviado."""

import http.server
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from urllib.parse import parse_qs

from playwright.sync_api import sync_playwright

from testes_ui import executor

USUARIO, SENHA = "usuario-teste", "senha-teste"

PAGINA_LOGADA = """<!doctype html><meta charset="utf-8"><title>Área</title>
<h1>Área logada</h1>
<p id="marca"></p>
<button onclick="localStorage.setItem('marca', 'sim'); location.reload()">Marcar</button>
<a href="/sair">Sair</a>
<script>document.getElementById('marca').textContent =
  localStorage.getItem('marca') ? 'Marcado' : 'Sem marca';</script>"""

PAGINA_LOGIN = """<!doctype html><meta charset="utf-8"><title>Login</title>
<form method="post" action="/login">
<label>Usuário <input name="username"></label>
<label>Senha <input name="password" type="password"></label>
<button>Entrar</button></form>"""


class Servidor(http.server.ThreadingHTTPServer):
    def __init__(self):
        super().__init__(("127.0.0.1", 0), Manipulador)
        self.logins = 0
        self.sessoes = set()


class Manipulador(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _sessao(self):
        for parte in (self.headers.get("Cookie") or "").split(";"):
            chave, _, valor = parte.strip().partition("=")
            if chave == "sid" and valor in self.server.sessoes:
                return valor
        return None

    def _redirecionar(self, destino, cookie=None):
        self.send_response(303)
        self.send_header("Location", destino)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def _html(self, corpo):
        dados = corpo.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        if self.path == "/login":
            return self._html(PAGINA_LOGIN)
        if self.path == "/sair":
            self.server.sessoes.discard(self._sessao())
            return self._redirecionar("/login")
        if self._sessao() is None:
            return self._redirecionar("/login")
        return self._html(PAGINA_LOGADA)

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length") or 0)
        campos = parse_qs(self.rfile.read(tamanho).decode())
        if campos.get("username") == [USUARIO] and campos.get("password") == [SENHA]:
            self.server.logins += 1
            sid = uuid.uuid4().hex
            self.server.sessoes.add(sid)
            return self._redirecionar("/inicio", f"sid={sid}; Path=/; HttpOnly")
        return self._html(PAGINA_LOGIN)


class SessaoPorRodadaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.navegador = cls.playwright.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.navegador.close()
        cls.playwright.stop()

    def setUp(self):
        self.servidor = Servidor()
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()
        self.host = f"http://127.0.0.1:{self.servidor.server_address[1]}"
        self.pasta = Path(tempfile.mkdtemp())

    def tearDown(self):
        self.servidor.shutdown()
        self.servidor.server_close()

    def roteiro(self, numero, acessar="/pagina", testar=None, validar=None):
        return {
            "id": f"SES-{numero:03d}",
            "titulo": "caso de teste da sessão",
            "host": self.host,
            "login": {"url": "/login", "campo_usuario": "username", "campo_senha": "password"},
            "acessar": acessar,
            "tempo_limite": 5,
            "testar": testar or [],
            "validar": validar or [{"tipo": "texto_visivel", "valor": "Área logada"}],
        }

    def rodar(self, roteiros, sessoes):
        return [
            executor.executar(self.navegador, r, (USUARIO, SENHA), self.pasta, "failures", "failures", {}, sessoes)
            for r in roteiros
        ]

    def test_um_login_vale_para_a_rodada_inteira(self):
        casos = self.rodar([self.roteiro(n) for n in (1, 2, 3)], executor.Sessoes())

        self.assertEqual([c.status for c in casos], ["aprovado"] * 3)
        self.assertEqual(self.servidor.logins, 1)
        self.assertEqual(casos[0].passos[0]["descricao"], "Entrar no sistema")
        self.assertEqual(casos[1].passos[0]["descricao"], "Entrar no sistema (sessão da rodada)")

    def test_sem_sessoes_cada_caso_faz_o_proprio_login(self):
        casos = self.rodar([self.roteiro(n) for n in (1, 2, 3)], None)

        self.assertEqual([c.status for c in casos], ["aprovado"] * 3)
        self.assertEqual(self.servidor.logins, 3)

    def test_sessao_encerrada_por_um_caso_faz_o_seguinte_entrar_de_novo(self):
        sair = [{"acao": "clicar", "alvo": {"papel": "link", "nome": "Sair"}}]
        roteiros = [
            self.roteiro(1, testar=sair, validar=[{"tipo": "url_contem", "valor": "/login"}]),
            self.roteiro(2),
            self.roteiro(3),
        ]

        casos = self.rodar(roteiros, executor.Sessoes())

        self.assertEqual([c.status for c in casos], ["aprovado"] * 3)
        self.assertEqual(self.servidor.logins, 2)

    def test_o_que_um_caso_muda_no_navegador_nao_passa_para_o_seguinte(self):
        marcar = [{"acao": "clicar", "alvo": {"papel": "button", "nome": "Marcar"}}]
        roteiros = [
            self.roteiro(1, testar=marcar, validar=[{"tipo": "texto_visivel", "valor": "Marcado"}]),
            self.roteiro(2, validar=[{"tipo": "texto_visivel", "valor": "Sem marca"}]),
        ]

        casos = self.rodar(roteiros, executor.Sessoes())

        self.assertEqual([c.status for c in casos], ["aprovado"] * 2)
        self.assertEqual(self.servidor.logins, 1)

    def test_caso_sem_acessar_continua_na_pagina_onde_o_login_terminou(self):
        casos = self.rodar([self.roteiro(1, acessar=None), self.roteiro(2, acessar=None)], executor.Sessoes())

        self.assertEqual([c.status for c in casos], ["aprovado"] * 2)
        self.assertEqual(self.servidor.logins, 1)


if __name__ == "__main__":
    unittest.main()
