"""Carrega e valida os roteiros: documentos de teste em YAML."""

from pathlib import Path

import yaml

CAMPOS_OBRIGATORIOS = ("id", "titulo", "host")
CAMPOS_LOGIN = ("url", "campo_usuario", "campo_senha")
ACOES = {
    "clicar": ("alvo",),
    "preencher": ("alvo", "valor"),
    "selecionar": ("alvo", "valor"),
    "pressionar": ("alvo", "tecla"),
}
VALIDACOES = {
    "texto_visivel": ("valor",),
    "url_contem": ("valor",),
    "elemento_visivel": ("alvo",),
    "valor_campo": ("alvo", "valor"),
    "minimo_linhas": ("alvo", "minimo"),
}
TIPOS_ALVO = ("rotulo", "papel", "texto", "css")

DESCRICAO_CAMPOS = {
    "id": "identificador do caso; aparece nos arquivos de saída. Use prefixo por tela, como CAD-001",
    "titulo": "frase que descreve o comportamento verificado",
    "host": "endereço da aplicação, como http://127.0.0.1:8765",
    "login": "página de login e os nomes dos campos de usuário e senha; login e senha são pedidos na execução",
    "acessar": "caminho aberto depois do login; sem ele, o caso segue da página onde o login terminou",
    "testar": "ações executadas em ordem",
    "validar": "confirmações sobre a tela; todas são executadas",
    "tempo_limite": "segundos que cada passo espera (padrão 10)",
    "prints": "ocultar: seletores CSS que ficam invisíveis só nos prints",
}
DESCRICAO_ACOES = {
    "clicar": "clica no elemento",
    "preencher": "apaga o conteúdo do campo e digita o valor",
    "selecionar": "escolhe a opção de uma lista pelo valor ou pelo texto",
    "pressionar": "foca o elemento e pressiona a tecla",
}
DESCRICAO_VALIDACOES = {
    "texto_visivel": "um elemento visível com esse texto aparece na tela",
    "url_contem": "o endereço atual contém o trecho",
    "elemento_visivel": "o elemento aparece na tela; mais de um visível é erro do roteiro",
    "valor_campo": "o campo tem exatamente esse valor",
    "minimo_linhas": "existem pelo menos 'minimo' elementos do alvo e o último deles está visível",
}
DESCRICAO_ALVOS = {
    "rotulo": "texto do rótulo de um campo",
    "papel": "papel acessível do elemento: button, link, textbox, row etc. Combine com 'nome'",
    "nome": "nome acessível ou trecho dele; não diferencia maiúsculas. Usado junto com 'papel'",
    "texto": "elemento que contém esse texto",
    "css": "seletor CSS; último recurso",
}


class RoteiroInvalido(Exception):
    pass


def carregar(caminho):
    """Lê um roteiro ou todos os .yaml de uma pasta, em ordem alfabética."""
    arquivos = sorted(caminho.glob("*.yaml")) if caminho.is_dir() else [caminho]
    return [_ler(arquivo) for arquivo in arquivos]


def _ler(arquivo):
    dados = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
    try:
        _validar(dados)
    except RoteiroInvalido as erro:
        raise RoteiroInvalido(f"{arquivo.name}: {erro}") from None
    dados.setdefault("tempo_limite", 10)
    return dados


def checar_texto(texto):
    """Valida um roteiro recebido como texto YAML, sem salvar nem executar. Levanta RoteiroInvalido se houver erro."""
    dados = yaml.safe_load(texto)
    _validar(dados)
    return dados


def _validar(roteiro):
    if not isinstance(roteiro, dict):
        raise RoteiroInvalido("o documento precisa ser um mapa YAML")
    _exigir(roteiro, CAMPOS_OBRIGATORIOS, "roteiro")
    if "login" in roteiro:
        _exigir(roteiro["login"], CAMPOS_LOGIN, "login")
    if "prints" in roteiro:
        _validar_prints(roteiro["prints"])

    for n, passo in enumerate(roteiro.get("testar") or [], 1):
        onde = f"testar[{n}]"
        _exigir(passo, ("acao",), onde)
        if passo["acao"] not in ACOES:
            raise RoteiroInvalido(f"{onde}: ação desconhecida '{passo['acao']}'")
        _exigir(passo, ACOES[passo["acao"]], onde)
        _validar_alvo(passo["alvo"], onde)

    for n, item in enumerate(roteiro.get("validar") or [], 1):
        onde = f"validar[{n}]"
        _exigir(item, ("tipo",), onde)
        if item["tipo"] not in VALIDACOES:
            raise RoteiroInvalido(f"{onde}: validação desconhecida '{item['tipo']}'")
        _exigir(item, VALIDACOES[item["tipo"]], onde)
        if "alvo" in item:
            _validar_alvo(item["alvo"], onde)


def _exigir(item, campos, onde):
    if not isinstance(item, dict):
        raise RoteiroInvalido(f"{onde}: esperado um mapa")
    faltando = [campo for campo in campos if campo not in item]
    if faltando:
        raise RoteiroInvalido(f"{onde}: faltam {', '.join(faltando)}")


def _validar_prints(prints):
    if not isinstance(prints, dict):
        raise RoteiroInvalido("prints: esperado um mapa")
    ocultar = prints.get("ocultar", [])
    if not isinstance(ocultar, list) or not all(isinstance(seletor, str) for seletor in ocultar):
        raise RoteiroInvalido("prints.ocultar: esperada uma lista de seletores CSS")


def _validar_alvo(alvo, onde):
    if not isinstance(alvo, dict) or not any(tipo in alvo for tipo in TIPOS_ALVO):
        raise RoteiroInvalido(f"{onde}: alvo precisa de um destes campos: {', '.join(TIPOS_ALVO)}")


def especificacao():
    """Descreve o formato dos roteiros. Usa as mesmas constantes que a validação, então não se desatualiza."""
    return {
        "campos_obrigatorios": list(CAMPOS_OBRIGATORIOS),
        "campos": DESCRICAO_CAMPOS,
        "login_campos": list(CAMPOS_LOGIN),
        "acoes": {nome: {"campos": list(campos), "descricao": DESCRICAO_ACOES[nome]} for nome, campos in ACOES.items()},
        "validacoes": {
            nome: {"campos": list(campos), "descricao": DESCRICAO_VALIDACOES[nome]} for nome, campos in VALIDACOES.items()
        },
        "alvos": DESCRICAO_ALVOS,
        "exemplo": "exemplos/aprovado.yaml",
    }
