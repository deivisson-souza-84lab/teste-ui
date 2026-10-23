"""Valores para a execução automática: login e segredos vêm de variáveis de ambiente.

As variáveis podem ser definidas no shell ou em um arquivo local CHAVE=VALOR, fora do repositório.
O arquivo padrão é ~/.config/testes-ui/ambiente; outro caminho pode ser dado em TESTES_UI_AMBIENTE.
Variável já definida no shell tem prioridade sobre o arquivo.
"""

import os
import re
import stat
from pathlib import Path

ARQUIVO_PADRAO = Path.home() / ".config" / "testes-ui" / "ambiente"
PREFIXO = "TESTES_UI_"
PREFIXO_SEGREDO = "TESTES_UI_SEGREDO_"
VARIAVEL_LOGIN = "TESTES_UI_LOGIN"
VARIAVEL_SENHA = "TESTES_UI_SENHA"


class AmbienteInvalido(Exception):
    pass


def caminho_arquivo():
    return Path(os.environ.get("TESTES_UI_AMBIENTE") or ARQUIVO_PADRAO)


def carregar(caminho=None):
    """Lê CHAVE=VALOR do arquivo e preenche só as variáveis que ainda não existem. Devolve o caminho lido, ou None."""
    caminho = Path(caminho) if caminho else caminho_arquivo()
    if not caminho.is_file():
        return None
    if stat.S_IMODE(caminho.stat().st_mode) & 0o077:
        raise AmbienteInvalido(f"{caminho} está legível por outros usuários. Rode: chmod 600 {caminho}")
    for numero, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), start=1):
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        if "=" not in linha:
            raise AmbienteInvalido(f"{caminho}, linha {numero}: esperado CHAVE=VALOR")
        chave, valor = (parte.strip() for parte in linha.split("=", 1))
        if not chave.startswith(PREFIXO):
            raise AmbienteInvalido(f"{caminho}, linha {numero}: a chave deve começar com {PREFIXO}")
        valor = valor[1:-1] if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'" else valor
        os.environ.setdefault(chave, valor)
    return caminho


def login():
    """Usuário e senha de TESTES_UI_LOGIN e TESTES_UI_SENHA. Devolve None se algum faltar."""
    usuario = os.environ.get(VARIAVEL_LOGIN, "").strip()
    senha = os.environ.get(VARIAVEL_SENHA, "")
    return (usuario, senha) if usuario and senha else None


def nome_variavel_segredo(nome):
    """Nome da variável de um segredo declarado no roteiro: segredo 'tecnico_senha' vira TESTES_UI_SEGREDO_TECNICO_SENHA."""
    return PREFIXO_SEGREDO + re.sub(r"\W", "_", nome).upper()


def segredos(declarados):
    """Valores dos segredos declarados no roteiro. Devolve (valores, variáveis que faltam). Nunca mostra os valores."""
    valores, faltando = {}, []
    for nome in declarados:
        variavel = nome_variavel_segredo(nome)
        valor = os.environ.get(variavel, "")
        if valor:
            valores[nome] = valor
        else:
            faltando.append(variavel)
    return valores, faltando
