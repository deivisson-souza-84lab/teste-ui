"""Registra cada passo: status, prints, faixa de marcação, JSON por caso e resumo."""

import json
from datetime import datetime

from playwright.sync_api import Error as ErroPlaywright

from testes_ui import acoes

MARCAR_FAIXA = """({mensagem, cor}) => {
  const faixa = document.createElement('div');
  faixa.id = 'testes-ui-faixa';
  faixa.textContent = mensagem;
  faixa.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:2147483647;'
    + `background:${cor};color:#fff;font:16px sans-serif;padding:8px;`;
  document.body.appendChild(faixa);
}"""

MARCAR_ELEMENTO = """(elemento, cor) => {
  elemento.dataset.testesUiContorno = elemento.style.outline;
  elemento.style.outline = `4px solid ${cor}`;
}"""

OCULTAR = """(seletores) => {
  const estilo = document.createElement('style');
  estilo.id = 'testes-ui-ocultar';
  estilo.textContent = seletores.map((seletor) => `${seletor} { display: none !important; }`).join(' ');
  document.head.appendChild(estilo);
}"""

ANCORAR_FIXOS = """() => {
  const altura = document.documentElement.scrollHeight;
  document.querySelectorAll('*').forEach((elemento) => {
    if (getComputedStyle(elemento).position !== 'fixed') return;
    const retangulo = elemento.getBoundingClientRect();
    const tocaEmbaixo = retangulo.top > 0 && Math.abs(retangulo.bottom - window.innerHeight) < 1;
    if (!tocaEmbaixo) return;
    elemento.dataset.testesUiEstilo = elemento.getAttribute('style') ?? '';
    elemento.style.position = 'absolute';
    elemento.style.top = `${altura - retangulo.height}px`;
    elemento.style.bottom = 'auto';
  });
}"""

DESMARCAR = """() => {
  document.getElementById('testes-ui-faixa')?.remove();
  document.getElementById('testes-ui-ocultar')?.remove();
  document.querySelectorAll('[data-testes-ui-contorno]').forEach((elemento) => {
    elemento.style.outline = elemento.dataset.testesUiContorno;
    delete elemento.dataset.testesUiContorno;
  });
  document.querySelectorAll('[data-testes-ui-estilo]').forEach((elemento) => {
    elemento.setAttribute('style', elemento.dataset.testesUiEstilo);
    delete elemento.dataset.testesUiEstilo;
  });
}"""

CORES = {"ok": "#198754", "invalidado": "#c00", "erro": "#c00"}


class Caso:
    def __init__(self, roteiro, pasta, screenshots, banner):
        self.id = roteiro["id"]
        self.titulo = roteiro["titulo"]
        self.host = roteiro["host"]
        self.pasta = pasta
        self.screenshots = screenshots
        self.banner = banner
        self.ocultar = (roteiro.get("prints") or {}).get("ocultar") or []
        self.inicio = datetime.now().isoformat(timespec="seconds")
        self.passos = []

    def passo(self, etapa, descricao, status, detalhe="", pagina=None, alvo=None):
        ordem = len(self.passos) + 1
        registro = {
            "ordem": ordem,
            "etapa": etapa,
            "descricao": descricao,
            "status": status,
            "detalhe": detalhe,
            "print": None,
        }
        falhou = status != "ok"
        if pagina is not None and (falhou or self.screenshots == "all"):
            marcar = falhou or self.banner == "all"
            registro["print"] = self._capturar(pagina, status, descricao, detalhe, alvo, ordem, marcar)
        self.passos.append(registro)

    @property
    def status(self):
        estados = {passo["status"] for passo in self.passos}
        for estado in ("erro", "invalidado"):
            if estado in estados:
                return estado
        return "aprovado"

    def to_dict(self):
        return {
            "id": self.id,
            "titulo": self.titulo,
            "host": self.host,
            "inicio": self.inicio,
            "status": self.status,
            "passos": self.passos,
        }

    def _capturar(self, pagina, status, descricao, detalhe, alvo, ordem, marcar):
        arquivo = self.pasta / f"{self.id}-{ordem}.png"
        try:
            if self.ocultar:
                pagina.evaluate(OCULTAR, self.ocultar)
            pagina.evaluate(ANCORAR_FIXOS)
            if marcar:
                self._marcar(pagina, status, descricao, detalhe, alvo)
            pagina.screenshot(path=arquivo, full_page=True)
        except ErroPlaywright:
            return None
        finally:
            _desmarcar(pagina)
        return arquivo.name

    def _marcar(self, pagina, status, descricao, detalhe, alvo):
        if alvo:
            elemento = acoes.localizar(pagina, alvo)
            if elemento.count():
                elemento.first.evaluate(MARCAR_ELEMENTO, CORES[status])
        pagina.evaluate(MARCAR_FAIXA, {"mensagem": _mensagem(status, descricao, detalhe), "cor": CORES[status]})


def gravar(caso):
    caminho = caso.pasta / f"{caso.id}.json"
    caminho.write_text(json.dumps(caso.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def linha(caso):
    return f"{caso.id}  {caso.status}  ({len(caso.passos)} passos)"


def resumo(casos, pasta):
    contagem = {estado: sum(caso.status == estado for caso in casos) for estado in ("aprovado", "invalidado", "erro")}
    linhas = [
        f"Resultado: {contagem['aprovado']} aprovado(s), {contagem['invalidado']} invalidado(s), "
        f"{contagem['erro']} com erro. Evidências: {pasta}"
    ]
    for caso in casos:
        for passo in caso.passos:
            if passo["status"] != "ok":
                linhas.append(
                    f"  {caso.id} passo {passo['ordem']} ({passo['etapa']}) {passo['descricao']}: "
                    f"{_primeira_linha(passo['detalhe'])}"
                )
    return "\n".join(linhas)


def _desmarcar(pagina):
    """Remove faixa, contorno, elementos ocultos e fixações para que os passos seguintes não herdem nada."""
    try:
        pagina.evaluate(DESMARCAR)
    except ErroPlaywright:
        pass


def _mensagem(status, descricao, detalhe):
    if status == "ok":
        return f"OK - {descricao}"
    return f"{status.upper()} - {descricao}: {_primeira_linha(detalhe)}"


def _primeira_linha(texto):
    texto = (texto or "").strip()
    return texto.splitlines()[0] if texto else ""
