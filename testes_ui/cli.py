"""Ponto de entrada: ajuda, checagem, leitura de tela, execução dos roteiros e execução automática."""

import argparse
import getpass
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import yaml
from playwright.sync_api import Error as ErroPlaywright
from playwright.sync_api import sync_playwright

from testes_ui import acoes, ambiente, executor, registro, roteiro

RAIZ = Path(__file__).resolve().parent.parent
SAIDA_PADRAO = Path(os.environ.get("TESTES_UI_SAIDA", RAIZ / "saidas"))
CONFIRMACAO = "CONFIRMO"
STATUS = {
    "aprovado": "todos os passos foram confirmados",
    "invalidado": "uma validação não foi confirmada; a tela ou o valor esperado pode estar errado. Os passos seguintes continuam",
    "erro": "um passo não pôde ser executado (alvo não encontrado ou ambíguo, login recusado, tempo esgotado). O caso para ali",
}
COMANDOS = {
    "ajuda": "imprime o formato dos roteiros em JSON",
    "checar CAMINHO": "valida roteiros sem abrir o navegador e sem pedir confirmação ou login",
    "inspecionar ARQUIVO [--seletor CSS]": "lê a tela do roteiro e salva papéis e nomes dos elementos, para escolher alvos",
    "rodar CAMINHO [opções]": "executa os roteiros; pede confirmação, login e senha",
    "rodar-auto CAMINHO [opções]": "executa sem perguntar, para agentes; login e segredos vêm de variáveis de ambiente",
}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="testes_ui")
    comandos = parser.add_subparsers(dest="comando", required=True)

    rodar = comandos.add_parser("rodar", help="executa um roteiro ou todos os .yaml de uma pasta")
    _opcoes_execucao(rodar)

    automatico = comandos.add_parser(
        "rodar-auto", help="executa sem perguntar, para agentes; login e segredos vêm de variáveis de ambiente"
    )
    _opcoes_execucao(automatico)

    checar = comandos.add_parser("checar", help="valida o formato dos roteiros, sem abrir o navegador")
    checar.add_argument("caminho", type=Path)

    inspecionar = comandos.add_parser(
        "inspecionar", help="lê a tela do roteiro e salva papéis e nomes dos elementos, para escolher alvos"
    )
    inspecionar.add_argument("arquivo", type=Path)
    inspecionar.add_argument("--seletor", default="body", help="parte da tela a ler, em CSS (padrão: a página toda)")
    inspecionar.add_argument(
        "--saida",
        type=Path,
        default=SAIDA_PADRAO,
        help="pasta das leituras (padrão: saidas/ no projeto, ou o valor de TESTES_UI_SAIDA)",
    )

    comandos.add_parser("ajuda", help="imprime o formato dos roteiros em JSON")

    args = parser.parse_args(argv)
    if args.comando == "ajuda":
        return _ajuda()
    if args.comando == "checar":
        return _checar(args.caminho)
    if args.comando == "inspecionar":
        return _inspecionar(args.arquivo, args.seletor, args.saida)
    if args.comando == "rodar-auto":
        return _rodar_auto(args)
    return _rodar(args)


def _opcoes_execucao(parser):
    """Opções comuns a rodar e rodar-auto."""
    parser.add_argument("caminho", type=Path)
    parser.add_argument("--visivel", action="store_true", help="mostra o navegador durante a execução")
    parser.add_argument(
        "--saida",
        type=Path,
        default=SAIDA_PADRAO,
        help="pasta das evidências (padrão: saidas/ no projeto, ou o valor de TESTES_UI_SAIDA)",
    )
    parser.add_argument(
        "--screenshots",
        choices=("failures", "all"),
        default="failures",
        help="em quais passos tirar print: só nas falhas (padrão) ou em todos",
    )
    parser.add_argument(
        "--banner",
        choices=("failures", "all"),
        default="failures",
        help="em quais prints marcar o passo (faixa e contorno): só nas falhas (padrão) ou em todos",
    )


def montar_ajuda():
    """Formato dos roteiros, usado pelo comando ajuda e pelo servidor MCP."""
    especificacao = roteiro.especificacao()
    especificacao["status"] = STATUS
    especificacao["comandos"] = COMANDOS
    return especificacao


def _ajuda():
    print(json.dumps(montar_ajuda(), ensure_ascii=False, indent=2))
    return 0


def _checar(caminho):
    roteiros = _carregar(caminho)
    if roteiros is None:
        return 2
    print(f"OK: {len(roteiros)} roteiro(s) válido(s)")
    for dados in roteiros:
        print(f"  {dados['id']}  {dados['titulo']}")
    return 0


def _inspecionar(arquivo, seletor, saida):
    roteiros = _carregar(arquivo)
    if roteiros is None:
        return 2
    if len(roteiros) != 1:
        print("inspecionar aceita um único arquivo de roteiro.", file=sys.stderr)
        return 2
    dados = roteiros[0]

    print("ATENÇÃO")
    print(f"O testes-ui vai abrir a tela do host {dados['host']} e ler os elementos dela.")
    print("Não clica em nada e não grava dados.")
    if not _confirmar_texto(f"Para confirmar que você está ciente e de acordo, digite {CONFIRMACAO}: "):
        print("Leitura cancelada. Nada foi feito.")
        return 2

    credenciais = None
    if "login" in dados:
        credenciais = _pedir_credenciais()
        if credenciais is None:
            print("Login ou senha vazios. Leitura cancelada.")
            return 2

    try:
        conteudo = _ler_tela(dados, credenciais, seletor)
    except (acoes.Erro, ErroPlaywright) as erro:
        print(f"Não foi possível ler a tela: {erro}", file=sys.stderr)
        return 1

    pasta = saida / "inspecoes"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{dados['id']}-{datetime.now():%Y%m%d-%H%M%S}.txt"
    caminho.write_text(conteudo, encoding="utf-8")
    print(f"Elementos da tela salvos em: {caminho}")
    print("O arquivo pode conter dados da tela. Revise antes de enviá-lo a uma IA.")
    return 0


def _ler_tela(dados, credenciais, seletor):
    tempo = dados["tempo_limite"] * 1000
    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch()
        try:
            contexto = navegador.new_context(base_url=dados["host"])
            pagina = contexto.new_page()
            if "login" in dados:
                usuario, senha = credenciais
                executor.entrar(pagina, dados["login"], usuario, senha, tempo)
            inicio = dados.get("acessar")
            if inicio is None and "login" not in dados:
                inicio = "/"
            if inicio is not None:
                pagina.goto(inicio)
            arvore = pagina.locator(seletor).aria_snapshot(timeout=tempo)
            return f"# Tela: {pagina.url}\n# Título: {pagina.title()}\n# Seletor: {seletor}\n\n{arvore}\n"
        finally:
            navegador.close()


def _rodar(args):
    roteiros = _carregar(args.caminho)
    if roteiros is None:
        return 2

    if not _confirmar(roteiros):
        print("Execução cancelada. Nada foi executado.")
        return 2

    credenciais = None
    if any("login" in dados for dados in roteiros):
        credenciais = _pedir_credenciais()
        if credenciais is None:
            print("Login ou senha vazios. Execução cancelada.")
            return 2

    segredos = []
    for dados in roteiros:
        valores = _pedir_segredos(dados.get("segredos") or {})
        if valores is None:
            print("Segredo vazio. Execução cancelada.")
            return 2
        segredos.append(valores)

    return _executar(roteiros, credenciais, segredos, args)


def _executar(roteiros, credenciais, segredos, args):
    """Roda os casos já confirmados e com login e segredos em mãos. Devolve o código de saída."""
    pasta = args.saida / datetime.now().strftime("%Y%m%d-%H%M%S")
    pasta.mkdir(parents=True)
    casos = []
    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch(headless=not args.visivel)
        try:
            for dados, valores in zip(roteiros, segredos):
                caso = executor.executar(navegador, dados, credenciais, pasta, args.screenshots, args.banner, valores)
                registro.gravar(caso)
                casos.append(caso)
                print(registro.linha(caso))
        finally:
            navegador.close()

    print(registro.resumo(casos, pasta))
    return 0 if all(caso.status == "aprovado" for caso in casos) else 1


def _rodar_auto(args):
    """Execução sem perguntas, feita por agente. Login e segredos vêm do ambiente; nunca são mostrados."""
    try:
        arquivo = ambiente.carregar()
    except ambiente.AmbienteInvalido as erro:
        print(f"Ambiente inválido: {erro}", file=sys.stderr)
        return 2

    roteiros = _carregar(args.caminho)
    if roteiros is None:
        return 2

    hosts = sorted({dados["host"] for dados in roteiros})
    credenciais = None
    if any("login" in dados for dados in roteiros):
        credenciais = ambiente.login()
        if credenciais is None:
            print(
                f"Faltam {ambiente.VARIAVEL_LOGIN} ou {ambiente.VARIAVEL_SENHA} no ambiente.",
                file=sys.stderr,
            )
            return 2

    segredos = []
    for dados in roteiros:
        valores, faltando = ambiente.segredos(dados.get("segredos") or {})
        if faltando:
            print(f"Caso {dados['id']}: faltam variáveis de segredo: {', '.join(faltando)}", file=sys.stderr)
            return 2
        segredos.append(valores)

    origem = f" (ambiente: {arquivo})" if arquivo else ""
    print(f"Execução automática de {len(roteiros)} caso(s) em {', '.join(hosts)}{origem}.")
    return _executar(roteiros, credenciais, segredos, args)


def _carregar(caminho):
    """Lê os roteiros ou imprime o motivo da falha. Devolve None quando não há roteiros válidos."""
    try:
        roteiros = roteiro.carregar(caminho)
    except (OSError, yaml.YAMLError, roteiro.RoteiroInvalido) as erro:
        print(f"Roteiro inválido: {erro}", file=sys.stderr)
        return None
    if not roteiros:
        print("Nenhum roteiro encontrado.", file=sys.stderr)
        return None
    return roteiros


def _confirmar(roteiros):
    print("ATENÇÃO")
    print("O testes-ui vai iniciar um roteiro de execuções nos hosts abaixo:")
    for host in sorted({dados["host"] for dados in roteiros}):
        print(f"  - {host}")
    print("Casos:")
    for dados in roteiros:
        print(f"  - {dados['id']} {dados['titulo']}")
    print("Esse roteiro pode listar, gravar, atualizar e remover informações do banco de dados, conforme o teste planejado.")
    return _confirmar_texto(f"Para confirmar que você está ciente e de acordo, digite {CONFIRMACAO}: ")


def _confirmar_texto(pergunta):
    return input(pergunta).strip() == CONFIRMACAO


def _pedir_credenciais():
    usuario = input("Login: ").strip()
    senha = getpass.getpass("Senha: ")
    return (usuario, senha) if usuario and senha else None


def _pedir_segredos(declarados):
    valores = {}
    for nome, pergunta in declarados.items():
        valor = getpass.getpass(f"{pergunta}: ")
        if not valor:
            return None
        valores[nome] = valor
    return valores
