"""Servidor MCP do testes-ui: expõe o formato dos roteiros e a checagem de rascunhos.

De propósito, não há ferramenta para executar testes nem para ler a tela. Essas ações ficam
no terminal do humano, conforme o AGENTS.md.
"""

import json

import yaml
from mcp.server.mcpserver import MCPServer

from testes_ui import cli, roteiro

servidor = MCPServer(
    name="testes-ui",
    instructions=(
        "Ajuda a escrever roteiros do testes-ui. Use 'ajuda' para conhecer o formato e 'checar_texto' para validar "
        "um rascunho de YAML antes de salvá-lo. Não há ferramenta para executar testes: a execução, a confirmação e o "
        "login são feitos pelo humano no terminal."
    ),
)


@servidor.tool()
def ajuda() -> str:
    """Formato atual dos roteiros: campos, ações, validações, alvos, status e comandos, em JSON."""
    return json.dumps(cli.montar_ajuda(), ensure_ascii=False, indent=2)


@servidor.tool()
def checar_texto(yaml_texto: str) -> str:
    """Valida um roteiro escrito em YAML, sem salvá-lo nem executá-lo. Devolve 'OK' ou o motivo do erro."""
    try:
        roteiro.checar_texto(yaml_texto)
    except yaml.YAMLError as erro:
        return f"YAML inválido: {erro}"
    except roteiro.RoteiroInvalido as erro:
        return f"Roteiro inválido: {erro}"
    return "OK"


def main():
    servidor.run()


if __name__ == "__main__":
    main()
