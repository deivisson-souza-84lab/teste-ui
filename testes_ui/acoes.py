"""Ações e validações genéricas de navegador. Não conhece nenhuma tela específica."""

import re

from playwright.sync_api import expect


class Falha(Exception):
    """A validação não foi confirmada: o caso fica invalidado."""


class Erro(Exception):
    """O passo não pôde ser executado: o caso fica com erro."""


def localizar(pagina, alvo):
    if "rotulo" in alvo:
        return pagina.get_by_label(alvo["rotulo"])
    if "papel" in alvo:
        return pagina.get_by_role(alvo["papel"], name=alvo.get("nome"))
    if "texto" in alvo:
        return pagina.get_by_text(alvo["texto"])
    return pagina.locator(alvo["css"])


def _visivel(pagina, alvo):
    """Localiza o alvo entre os elementos visíveis. Mais de um é erro do roteiro, não da tela."""
    elemento = localizar(pagina, alvo).filter(visible=True)
    quantidade = elemento.count()
    if quantidade > 1:
        raise Erro(f"o alvo encontrou {quantidade} elementos visíveis; torne-o mais específico")
    return elemento


def executar(pagina, passo, tempo):
    elemento = _visivel(pagina, passo["alvo"])
    acao = passo["acao"]
    if acao == "clicar":
        elemento.click(timeout=tempo)
    elif acao == "preencher":
        elemento.fill(str(passo["valor"]), timeout=tempo)
    elif acao == "selecionar":
        elemento.select_option(str(passo["valor"]), timeout=tempo)
    elif acao == "pressionar":
        elemento.press(passo["tecla"], timeout=tempo)


def validar(pagina, item, tempo):
    tipo = item["tipo"]
    try:
        if tipo == "texto_visivel":
            expect(pagina.get_by_text(str(item["valor"])).filter(visible=True).first).to_be_visible(timeout=tempo)
        elif tipo == "url_contem":
            expect(pagina).to_have_url(re.compile(re.escape(str(item["valor"]))), timeout=tempo)
        elif tipo == "elemento_visivel":
            expect(_visivel(pagina, item["alvo"])).to_be_visible(timeout=tempo)
        elif tipo == "valor_campo":
            expect(_visivel(pagina, item["alvo"])).to_have_value(str(item["valor"]), timeout=tempo)
        elif tipo == "minimo_linhas":
            minimo = int(item["minimo"])
            if minimo > 0:
                expect(localizar(pagina, item["alvo"]).nth(minimo - 1)).to_be_visible(timeout=tempo)
    except AssertionError as erro:
        raise Falha(str(erro)) from None
