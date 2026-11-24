"""Testes da execução automática (rodar-auto): ambiente, login e segredos. Não abrem navegador."""

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from testes_ui import ambiente, cli

RAIZ = Path(__file__).resolve().parent.parent
ROTEIRO_COM_LOGIN = RAIZ / "exemplos" / "aprovado.yaml"
VARIAVEIS = ("TESTES_UI_LOGIN", "TESTES_UI_SENHA", "TESTES_UI_SEGREDO_TECNICO_SENHA", "TESTES_UI_AMBIENTE")


class Isolado(unittest.TestCase):
    """Cada teste roda com as variáveis do testes-ui limpas e sem ler o arquivo de ambiente do usuário."""

    def setUp(self):
        self.pasta = Path(tempfile.mkdtemp())
        self.env = mock.patch.dict(os.environ, {k: v for k, v in os.environ.items() if k not in VARIAVEIS})
        self.env.start()
        os.environ["TESTES_UI_AMBIENTE"] = str(self.pasta / "ambiente-inexistente")

    def tearDown(self):
        self.env.stop()


class AmbienteTest(Isolado):
    def escrever(self, texto, modo=0o600):
        arquivo = self.pasta / "ambiente"
        arquivo.write_text(texto, encoding="utf-8")
        os.chmod(arquivo, modo)
        return arquivo

    def test_le_chave_valor_e_remove_aspas(self):
        arquivo = self.escrever("# comentário\nTESTES_UI_LOGIN=usuario-teste\nTESTES_UI_SENHA=\"abc 123\"\n")
        ambiente.carregar(arquivo)
        self.assertEqual(os.environ["TESTES_UI_LOGIN"], "usuario-teste")
        self.assertEqual(os.environ["TESTES_UI_SENHA"], "abc 123")

    def test_variavel_do_shell_tem_prioridade_sobre_o_arquivo(self):
        os.environ["TESTES_UI_LOGIN"] = "do-shell"
        ambiente.carregar(self.escrever("TESTES_UI_LOGIN=do-arquivo\n"))
        self.assertEqual(os.environ["TESTES_UI_LOGIN"], "do-shell")

    def test_recusa_arquivo_legivel_por_outros(self):
        arquivo = self.escrever("TESTES_UI_LOGIN=x\n", modo=0o644)
        with self.assertRaises(ambiente.AmbienteInvalido):
            ambiente.carregar(arquivo)

    def test_recusa_chave_fora_do_prefixo(self):
        arquivo = self.escrever("OUTRA=valor\n")
        with self.assertRaises(ambiente.AmbienteInvalido):
            ambiente.carregar(arquivo)

    def test_sem_arquivo_nao_faz_nada(self):
        self.assertIsNone(ambiente.carregar())

    def test_login_exige_usuario_e_senha(self):
        self.assertIsNone(ambiente.login())
        os.environ["TESTES_UI_LOGIN"] = "usuario-teste"
        self.assertIsNone(ambiente.login())
        os.environ["TESTES_UI_SENHA"] = "x"
        self.assertEqual(ambiente.login(), ("usuario-teste", "x"))

    def test_segredo_usa_nome_da_variavel_e_lista_faltantes_sem_valores(self):
        os.environ["TESTES_UI_SEGREDO_TECNICO_SENHA"] = "valor-secreto"
        valores, faltando = ambiente.segredos({"tecnico_senha": "Senha", "outro": "Outro"})
        self.assertEqual(valores, {"tecnico_senha": "valor-secreto"})
        self.assertEqual(faltando, ["TESTES_UI_SEGREDO_OUTRO"])
        self.assertNotIn("valor-secreto", ",".join(faltando))


class RodarAutoTest(Isolado):
    def executar(self, *argumentos):
        saida, erro = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erro):
            codigo = cli.main(list(argumentos))
        return codigo, saida.getvalue(), erro.getvalue()

    def test_recusa_sem_login_no_ambiente(self):
        codigo, _, erro = self.executar("rodar-auto", str(ROTEIRO_COM_LOGIN))
        self.assertEqual(codigo, 2)
        self.assertIn("TESTES_UI_LOGIN", erro)
        self.assertIn("TESTES_UI_SENHA", erro)

    def test_recusa_segredo_faltando_mostrando_so_o_nome_da_variavel(self):
        roteiro = self.pasta / "segredo.yaml"
        roteiro.write_text(
            "id: T-001\n"
            "titulo: caso de teste de segredo\n"
            "host: http://127.0.0.1:9\n"
            "segredos:\n"
            "  tecnico_senha: Senha do técnico\n",
            encoding="utf-8",
        )
        os.environ["TESTES_UI_LOGIN"] = "usuario-teste"
        os.environ["TESTES_UI_SENHA"] = "x"
        codigo, _, erro = self.executar("rodar-auto", str(roteiro))
        self.assertEqual(codigo, 2)
        self.assertIn("TESTES_UI_SEGREDO_TECNICO_SENHA", erro)

    def test_rodar_auto_nao_pede_autorizacao_nem_confirmacao(self):
        # Sem login no ambiente, a recusa é a da falta de login, não de autorização ou confirmação.
        codigo, _, erro = self.executar("rodar-auto", str(ROTEIRO_COM_LOGIN))
        self.assertEqual(codigo, 2)
        self.assertNotIn("autoriz", erro.lower())
        self.assertNotIn("CONFIRMO", erro)


if __name__ == "__main__":
    unittest.main()
