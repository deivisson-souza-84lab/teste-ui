"""Executa um roteiro: login -> acessar -> testar -> validar. Cada passo é registrado ao terminar."""

from playwright.sync_api import Error as ErroPlaywright
from playwright.sync_api import expect

from testes_ui import acoes
from testes_ui.registro import Caso


def executar(navegador, roteiro, credenciais, pasta, screenshots, banner, segredos=None):
    caso = Caso(roteiro, pasta, screenshots, banner)
    tempo = roteiro["tempo_limite"] * 1000
    contexto = navegador.new_context(base_url=roteiro["host"])
    pagina = contexto.new_page()
    try:
        if "login" in roteiro:
            usuario, senha = credenciais
            etapa = _etapa(caso, pagina, "login", "Entrar no sistema", entrar, pagina, roteiro["login"], usuario, senha, tempo)
            if etapa != "ok":
                return caso

        inicio = roteiro.get("acessar")
        if inicio is None and "login" not in roteiro:
            inicio = "/"
        if inicio is not None and _etapa(caso, pagina, "acessar", f"Abrir {inicio}", pagina.goto, inicio) != "ok":
            return caso

        for passo in roteiro.get("testar") or []:
            descricao = f"{passo['acao']} em {_texto_alvo(passo['alvo'])}"
            passo_real = _com_segredos(passo, segredos or {})
            etapa = _etapa(caso, pagina, "testar", descricao, acoes.executar, pagina, passo_real, tempo, alvo=passo["alvo"])
            if etapa != "ok":
                return caso

        for item in roteiro.get("validar") or []:
            _etapa(caso, pagina, "validar", _descrever_validacao(item), acoes.validar, pagina, item, tempo, alvo=_alvo_marcado(item))
    finally:
        contexto.close()
    return caso


def _etapa(caso, pagina, etapa, descricao, funcao, *args, alvo=None):
    """Executa uma função, registra o resultado e devolve 'ok', 'invalidado' ou 'erro'."""
    try:
        funcao(*args)
    except acoes.Falha as falha:
        caso.passo(etapa, descricao, "invalidado", str(falha), pagina, alvo)
        return "invalidado"
    except (acoes.Erro, ErroPlaywright) as erro:
        caso.passo(etapa, descricao, "erro", str(erro), pagina, alvo)
        return "erro"
    caso.passo(etapa, descricao, "ok", pagina=pagina, alvo=alvo)
    return "ok"


def entrar(pagina, login, usuario, senha, tempo):
    """Preenche o formulário de login pelos nomes dos campos e envia com Enter."""
    pagina.goto(login["url"])
    pagina.locator(f'[name="{login["campo_usuario"]}"]').fill(usuario, timeout=tempo)
    campo_senha = pagina.locator(f'[name="{login["campo_senha"]}"]')
    campo_senha.fill(senha, timeout=tempo)
    campo_senha.press("Enter", timeout=tempo)
    try:
        expect(campo_senha).not_to_be_visible(timeout=tempo)
    except AssertionError:
        raise acoes.Erro("login não aceito: o campo de senha continua visível") from None
    pagina.wait_for_load_state(timeout=tempo)


def _descrever_validacao(item):
    alvo = item.get("alvo")
    complemento = _texto_alvo(alvo) if alvo else str(item.get("valor"))
    return f"{item['tipo']}: {complemento}"


def _alvo_marcado(item):
    """Elemento examinado pela validação, para marcá-lo no print."""
    if "alvo" in item:
        return item["alvo"]
    if item["tipo"] == "texto_visivel":
        return {"texto": str(item["valor"])}
    return None


def _com_segredos(passo, segredos):
    """Troca {segredo: nome} pelo valor digitado na execução. O valor não é guardado no roteiro nem no registro."""
    valor = passo.get("valor")
    if not isinstance(valor, dict):
        return passo
    return {**passo, "valor": segredos[valor["segredo"]]}


def _texto_alvo(alvo):
    return ", ".join(f"{chave} '{valor}'" for chave, valor in alvo.items())
