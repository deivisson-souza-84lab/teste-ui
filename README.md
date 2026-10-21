# testes-ui

Executa roteiros de teste de navegação em qualquer aplicação web. Um roteiro é um arquivo YAML: o programa abre o navegador, faz login se for preciso, executa ações e confirma o que aparece na tela.

Não depende de nenhum repositório. O roteiro traz o host, e o login e a senha são pedidos na própria execução.

Ciclo de cada caso: **login (se houver) → acessar (se houver) → testar → validar → registrar**.

Para aprender a escrever roteiros, leia o [TUTORIAL.md](TUTORIAL.md). Se for usar uma IA para escrevê-los, ela deve começar pelo [AGENTS.md](AGENTS.md).

## Comandos

| Comando | O que faz | Pede algo ao humano? |
|---|---|---|
| `python -m testes_ui ajuda` | imprime o formato dos roteiros em JSON, a partir do código | não |
| `python -m testes_ui checar CAMINHO` | valida roteiros sem abrir o navegador | não |
| `python -m testes_ui inspecionar ARQUIVO [--seletor CSS]` | lê a tela do roteiro e salva papéis e nomes dos elementos em `saidas/inspecoes/`, para escolher alvos | confirmação, login e senha |
| `python -m testes_ui rodar CAMINHO [opções]` | executa os roteiros | confirmação, login e senha |

`inspecionar` não clica nem grava nada. Seu arquivo de saída pode conter dados da tela, então revise antes de enviá-lo a outra pessoa ou a uma IA.

As evidências de `rodar` e as leituras de `inspecionar` vão para `saidas/`, dentro do projeto e ignorada pelo Git. Para guardá-las fora do projeto, use `--saida CAMINHO` ou defina a variável de ambiente `TESTES_UI_SAIDA`.

## Instalação

```
python3 -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Primeiro teste: o site de exemplo

O projeto traz um site estático em `exemplos/site/` para testar o próprio programa. Ele tem uma tela de login, um painel com uma tabela e uma página de cadastro.

Em um terminal, suba o site:

```
python -m http.server 8765 --bind 127.0.0.1 --directory exemplos/site
```

Em outro terminal, rode os exemplos:

```
python -m testes_ui rodar exemplos/
```

Quando pedido, digite `CONFIRMO`, depois `tester` como login e `tester123` como senha. A saída esperada:

```
EX-001  aprovado  (6 passos)
EX-003  erro  (3 passos)
EX-002  invalidado  (3 passos)
EX-004  aprovado  (4 passos)
Resultado: 2 aprovado(s), 1 invalidado(s), 1 com erro. Evidências: saidas/<data-hora>
```

`EX-002` é invalidado de propósito: valida um texto que não existe. `EX-003` é erro de propósito: clica num botão que não existe.

## Execução

Coloque os roteiros do seu sistema na pasta `casos/`.

```
python -m testes_ui rodar casos/arquivo.yaml                       # um roteiro
python -m testes_ui rodar casos/                                   # todos os .yaml da pasta
python -m testes_ui rodar casos/ --visivel                         # mostra o navegador
python -m testes_ui rodar casos/ --screenshots all                 # print de todos os passos
python -m testes_ui rodar casos/ --screenshots all --banner all    # print de todos, com faixa e contorno
```

Antes de começar, o programa mostra os hosts e os casos e pede a confirmação `CONFIRMO`, porque o roteiro pode listar, gravar, atualizar e remover informações do banco. Sem a confirmação, nada é executado.

Depois da confirmação, pede o login e a senha. Eles ficam só na memória do processo: não são gravados em arquivo, JSON, log nem print.

## Roteiro (YAML)

O exemplo a seguir é `exemplos/aprovado.yaml`:

```yaml
id: EX-001
titulo: Login e painel exibem a tabela e aceitam o ano informado
host: http://127.0.0.1:8765
login:
  url: /login.html
  campo_usuario: username
  campo_senha: password
acessar: /painel.html
testar:
  - acao: preencher
    alvo: {rotulo: Ano}
    valor: 2026
validar:
  - tipo: texto_visivel
    valor: Lista de pedidos
  - tipo: minimo_linhas
    alvo: {css: "tbody tr"}
    minimo: 2
  - tipo: valor_campo
    alvo: {rotulo: Ano}
    valor: 2026
```

| Campo | Obrigatório | Função |
|---|---|---|
| `id`, `titulo`, `host` | sim | identificação do caso e endereço da aplicação |
| `login` | não | página de login e os nomes dos campos de usuário e senha |
| `acessar` | não | página aberta depois do login |
| `testar` | não | ações: `clicar`, `preencher`, `selecionar`, `pressionar` |
| `validar` | não | confirmações: `texto_visivel`, `url_contem`, `elemento_visivel`, `valor_campo`, `minimo_linhas` |
| `tempo_limite` | não | segundos que cada passo espera (padrão 10) |
| `prints` | não | seletores CSS que ficam ocultos nos prints |

Alvos: `{rotulo: ...}` (rótulo do campo), `{papel: ..., nome: ...}` (papel acessível e nome), `{texto: ...}` ou `{css: ...}`. O tutorial explica quando usar cada um.

Sem `login` e sem `acessar`, o caso começa na raiz do host.

### Navegação depois do login

O login pode levar a uma página inicial diferente em cada sistema. O roteiro não precisa saber o nome dessa página: basta clicar no menu. O exemplo a seguir é `exemplos/navegacao.yaml`:

```yaml
id: EX-004
titulo: Após o login, a partir da página inicial, o usuário chega ao Cadastro pelo menu
host: http://127.0.0.1:8765
login:
  url: /login.html
  campo_usuario: username
  campo_senha: password
testar:
  - acao: clicar
    alvo: {papel: link, nome: Cadastro}
validar:
  - tipo: url_contem
    valor: cadastro.html
  - tipo: texto_visivel
    valor: Cadastro de produtos
```

Se o destino estiver dentro de um submenu, clique primeiro no item pai e depois no filho, na ordem em que um usuário faria.

## Resultado

- **aprovado**: todos os passos confirmados.
- **invalidado**: uma validação não foi confirmada. A tela pode estar errada, ou o valor esperado pode estar errado. Os passos seguintes continuam.
- **erro**: um passo não pôde ser executado (elemento não encontrado, alvo ambíguo, login recusado, tempo esgotado). O caso para ali.

Cada execução grava em `saidas/<data-hora>/`:

- `<ID>.json`: passo a passo, com status, detalhe e o nome do print de cada passo.
- `<ID>-<ordem>.png`: prints.

Código de saída: `0` se tudo foi aprovado; `1` se houve caso invalidado ou com erro; `2` se o roteiro é inválido ou a execução foi cancelada.

### Prints e faixa

Por padrão, a captura acontece só nos passos que falham, com faixa vermelha e o elemento marcado quando ele é localizado. Duas opções controlam isso separadamente:

| Opção | Valores | Padrão | Efeito |
|---|---|---|---|
| `--screenshots` | `failures`, `all` | `failures` | `all` tira print de todos os passos, inclusive os que passam |
| `--banner` | `failures`, `all` | `failures` | `all` põe a faixa e o contorno em todos os prints. A faixa é vermelha nas falhas e verde nos passos que passam |

Com `--screenshots all` e sem `--banner all`, os prints dos passos que passam saem limpos.

Cada print mostra só a marcação do próprio passo: a faixa e o contorno são removidos logo depois da captura. Em validações de texto, o contorno vai para o texto encontrado, então passos de leitura também geram prints diferentes.

Rodapés fixos na parte de baixo da janela são levados para o fim da página no print, sem seletor específico. A captura de página inteira deixaria esses elementos na altura da janela original, no meio da imagem. Depois do print, a posição original é restaurada.

### Ocultar elementos nos prints

Menus laterais ou avisos fixos podem cobrir o conteúdo validado. O roteiro declara o que ocultar, só nos prints, sem alterar a tela durante o teste:

```yaml
prints:
  ocultar:
    - .menu-lateral        # seletores CSS; ficam invisíveis em todos os prints do roteiro
```

## Limites atuais

- O login é por formulário, com campos identificados pelo atributo `name` e envio por Enter.
- O navegador usado é o Chromium.
- Os roteiros não criam massa de dados: quem executa precisa garantir os dados que o caso espera.

## Servidor MCP (opcional)

Para clientes que suportam MCP, o `testes-ui` oferece um servidor com duas ferramentas: `ajuda`, que devolve o formato dos roteiros, e `checar_texto`, que valida um rascunho de YAML sem salvá-lo. O servidor não executa testes nem lê a tela. Essas ações continuam no terminal do humano.

```
pip install -r requirements-mcp.txt
```

Configure o cliente para iniciar o servidor com este comando, usando o Python do ambiente virtual do projeto:

```
/caminho/para/testes-ui/.venv/bin/python -m testes_ui.mcp_servidor
```

No Windows, o Python fica em `.venv\Scripts\python.exe`. O formato exato do arquivo de configuração depende do cliente. Um exemplo genérico:

```json
{
  "mcpServers": {
    "testes-ui": {
      "command": "/caminho/para/testes-ui/.venv/bin/python",
      "args": ["-m", "testes_ui.mcp_servidor"]
    }
  }
}
```

## Licença

Apache-2.0. Veja o arquivo [LICENSE](LICENSE).
