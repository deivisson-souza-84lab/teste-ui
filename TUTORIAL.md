# Como escrever roteiros de teste

Este tutorial ensina a escrever um roteiro do testes-ui. Você não escreve código Python: um roteiro é um arquivo YAML que descreve o que o programa faz no navegador e o que deve confirmar na tela.

Os exemplos usam o site de demonstração de `exemplos/site/`. Para subi-lo, veja o [README](README.md#primeiro-teste-o-site-de-exemplo).

## 1. Como um roteiro funciona

Cada roteiro executa, nesta ordem:

1. **login**: se houver o bloco `login`, pede o login e a senha na execução e entra no sistema.
2. **acessar**: se houver, abre uma página. Sem ela, o caso segue da página onde o login terminou.
3. **testar**: ações, em ordem: clicar, preencher, selecionar, pressionar.
4. **validar**: confirmações sobre a tela. Todas são executadas, mesmo que alguma falhe.

Cada passo termina com um resultado (ok, invalidado ou erro) e, se você pediu, um print.

**Regra de ouro:** `testar` muda a tela; `validar` só lê a tela. Uma validação nunca clica.

## 2. Passo a passo: um teste para o painel

Vamos escrever um teste para este comportamento: *depois do login, o painel mostra a tabela e aceita um ano.*

### Passo 1: escreva o resultado esperado

Antes de abrir o editor, liste o que deve ser verdade no fim:

- o painel tem o título "Lista de pedidos";
- a tabela tem pelo menos 2 linhas;
- o campo Ano aceita 2026.

Cada item vira uma validação. Se você não consegue escrever o resultado esperado em frases, ainda não está pronto para escrever o roteiro.

### Passo 2: crie o arquivo

Crie `casos/painel.yaml`. A extensão tem que ser `.yaml`, e o nome pode ser qualquer um.

### Passo 3: identificação

```yaml
id: PAINEL-001
titulo: Painel exibe a tabela e aceita o ano informado
host: http://127.0.0.1:8765
```

- `id` aparece nos arquivos de saída (`PAINEL-001.json`, `PAINEL-001-3.png`). Use um prefixo por tela e um número: `CAD-001`, `CAD-002`.
- `titulo` diz o que o caso verifica. Escreva o comportamento, não o procedimento.
- `host` é o endereço da aplicação. Quem executa recebe esse endereço do responsável pelo sistema.

### Passo 4: login

```yaml
login:
  url: /login.html
  campo_usuario: username
  campo_senha: password
```

- `url` é a página de login, relativa ao host.
- `campo_usuario` e `campo_senha` são o atributo `name` dos campos, não o rótulo. Para descobrir, abra a página de login e veja o HTML, ou use o inspetor do navegador (F12).

Você não coloca a senha no arquivo. Login e senha são pedidos na execução.

### Passo 5: página inicial

```yaml
acessar: /painel.html
```

Se você não souber a página de destino do login, omita `acessar` e use a navegação (seção 6).

### Passo 6: ação

```yaml
testar:
  - acao: preencher
    alvo: {rotulo: Ano}
    valor: 2026
```

`preencher` apaga o conteúdo do campo e digita o valor. O alvo `{rotulo: Ano}` acha o campo pelo texto do rótulo ao lado dele. A seção 4 explica como escolher alvos.

### Passo 7: validações

```yaml
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

Cada item é uma confirmação. A seção 5 lista todos os tipos.

### Passo 8: verifique o formato e rode

Para validar o arquivo sem abrir o navegador, rode o programa. Erro de formato aparece antes da confirmação, com o arquivo e o campo:

```
python -m testes_ui rodar casos/painel.yaml
```

Depois de digitar `CONFIRMO`, login e senha, o resultado esperado é:

```
PAINEL-001  aprovado  (6 passos)
```

Os 6 passos são: login, acessar, preencher, e as três validações. O arquivo completo deste passo a passo é equivalente a `exemplos/aprovado.yaml`.

## 3. Como ler o resultado

| Status | Significa | O que fazer |
|---|---|---|
| **aprovado** | todos os passos foram confirmados | nada |
| **invalidado** | uma validação não foi confirmada | veja o print. Pode ser a tela errada ou o valor esperado errado |
| **erro** | um passo não pôde ser executado | confira o roteiro e o ambiente: alvo, login, tempo, dados |

A diferença importa. `invalidado` é um resultado sobre o sistema: a tela não mostrou o que o teste esperava. `erro` é um problema de execução: o teste não chegou a verificar a regra. Um caso com erro não prova que a funcionalidade está quebrada, e também não prova que está correta.

Ações que falham geram `erro` e param o caso. Validações que falham geram `invalidado` e o caso continua, para que você veja todas as falhas de uma vez.

## 4. Como escolher o alvo

Um alvo diz ao programa qual elemento da tela usar. Prefira, nesta ordem:

1. **`{rotulo: Ano}`**: o texto do rótulo de um campo.
2. **`{papel: button, nome: Novo pedido}`**: o papel do elemento (`button`, `link`, `textbox`, `row` e outros) e o nome dele. O nome é comparado como trecho e não diferencia maiúsculas: `nome: Novo` também acha "Novo pedido".
3. **`{texto: ...}`**: qualquer elemento com aquele texto. Use quando não houver papel ou rótulo claro.
4. **`{css: ...}`**: seletor CSS. É o último recurso. Use para contar linhas de tabela (`{css: "tbody tr"}`) ou quando nada acima serve. Seletores ligados a classes de visual quebram quando a tela muda.

Para descobrir o alvo, abra a página e inspecione o elemento (F12). Se tiver o `playwright-cli` instalado, `playwright-cli snapshot` mostra os papéis e nomes da página.

### Alvo ambíguo

Se o alvo encontra mais de um elemento visível, o caso para com **erro**:

```
o alvo encontrou 2 elementos visíveis; torne-o mais específico
```

Torne o alvo mais específico: combine papel e nome, use um rótulo, ou um seletor CSS que aponte para um só elemento.

## 5. Ações (`testar`)

| Ação | Alvo | Valor | Efeito |
|---|---|---|---|
| `clicar` | sim | não | clica no elemento |
| `preencher` | sim | `valor` | apaga o conteúdo e digita o valor |
| `selecionar` | sim | `valor` | escolhe a opção de uma lista pelo valor ou pelo texto |
| `pressionar` | sim | `tecla` | foca o elemento e pressiona a tecla (`Enter`, `Tab` etc.) |

Valores numéricos são convertidos para texto. `valor: 2026` e `valor: "2026"` dão o mesmo resultado.

## 6. Validações (`validar`)

| Tipo | Campos | Confirma que... |
|---|---|---|
| `texto_visivel` | `valor` | um elemento visível com esse texto aparece na tela. Não precisa de alvo |
| `url_contem` | `valor` | o endereço atual contém o trecho. Útil para confirmar que chegou à tela certa |
| `elemento_visivel` | `alvo` | o elemento aparece na tela. Mais de um elemento visível é erro do roteiro |
| `valor_campo` | `alvo`, `valor` | o campo tem exatamente esse valor |
| `minimo_linhas` | `alvo`, `minimo` | existem pelo menos `minimo` elementos do alvo, e o último deles está visível. Use `{css: "tbody tr"}` para contar linhas |

Escreva validações que falhariam se a funcionalidade quebrasse. Confirmar que a página abriu (`url_contem`) é um começo. Confirmar um dado que o usuário precisa ver (`valor_campo`, `minimo_linhas`, um texto de resultado) é melhor.

## 7. Navegação depois do login

Nem sempre você sabe para onde o login leva. Se o caso não tem `acessar`, ele segue da página onde o login terminou, e os passos de `testar` caminham a partir dali. Para chegar a uma tela de cadastro pelo menu:

```yaml
id: CAD-001
titulo: Após o login, o usuário chega ao Cadastro pelo menu
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

Se o destino estiver dentro de um submenu, use uma ação `clicar` para o item pai e outra para o filho, na mesma ordem em que um usuário faria. Assim o roteiro não depende de qual é a página inicial.

## 8. Prints

Por padrão, só os passos que falham geram print, com faixa vermelha e o elemento marcado.

Para ver a tela em todos os passos, rode com:

```
python -m testes_ui rodar casos/ --screenshots all
```

Use `--banner all` para pôr a faixa e o contorno em todos os prints. Sem ele, os prints dos passos que passam saem limpos.

Se um menu ou aviso fixo cobrir o conteúdo que você valida, declare o seletor no roteiro. Ele fica oculto só nos prints, e a tela não é alterada durante o teste:

```yaml
prints:
  ocultar:
    - .menu-lateral
```

Rodapés fixos na parte de baixo da janela já são tratados pelo programa. Você não precisa declará-los.

## 9. Boas práticas

- **Um caso, um comportamento.** Se o título tem "e" no meio, talvez sejam dois casos.
- **Valide o efeito, não só o clique.** Um clique que não gera erro não prova nada. Confirme o texto, o valor ou o endereço que aparece depois.
- **Cada caso é independente.** Ele faz o próprio login e começa do zero. Não conte com um caso anterior ter deixado a tela em algum estado.
- **Diga os dados que o caso espera.** Se o caso precisa de um pedido existente, diga isso no título ou num comentário. Quem executa é quem garante esses dados.
- **Casos que gravam, alteram ou removem dados** devem dizer isso no título e rodar só em um host de teste. O programa mostra os casos antes de pedir a confirmação, mas o título é o que fica registrado.
- **Nunca coloque senha no arquivo.** Login e senha são pedidos na execução.
- **Prefira alvos semânticos** (`rotulo`, `papel` com `nome`). Eles sobrevivem a mudanças visuais. `css` com classes de estilo quebra com facilidade.
- **Aumente `tempo_limite` só quando a tela for lenta.** Um tempo alto faz o caso demorar para falhar, então não use como remédio para um alvo errado.

## 10. Erros comuns

| Mensagem | Status | Causa | O que fazer |
|---|---|---|---|
| `Roteiro inválido: X.yaml: validar[2]: faltam valor` | não roda | campo obrigatório ausente no item | acrescente o campo |
| `testar[1]: ação desconhecida 'clica'` | não roda | nome da ação errado | use `clicar`, `preencher`, `selecionar` ou `pressionar` |
| `validar[1]: validação desconhecida 'texto'` | não roda | tipo de validação errado | use um dos tipos da seção 6 |
| `alvo precisa de um destes campos: rotulo, papel, texto, css` | não roda | alvo sem chave válida | corrija o alvo |
| `login não aceito: o campo de senha continua visível` | erro | login ou senha errados, ou `campo_usuario`/`campo_senha` com nome errado | confira as credenciais e o atributo `name` dos campos |
| `o alvo encontrou 2 elementos visíveis; torne-o mais específico` | erro | alvo ambíguo | seção 4 |
| `Locator.click: Timeout 2000ms exceeded.` | erro | o elemento não apareceu no tempo | confira o alvo; aumente `tempo_limite` só se a tela for lenta |
| `Locator expected to be visible` | invalidado | a validação não encontrou o que esperava | confira o texto esperado e veja o print |

## 11. Checklist antes de salvar

- [ ] `id` com prefixo da tela e número único
- [ ] `titulo` descreve o comportamento verificado
- [ ] `host` correto, e nenhuma senha no arquivo
- [ ] alvos por rótulo ou por papel com nome; `css` só quando necessário
- [ ] validações confirmam o resultado, não só a navegação
- [ ] caso que grava dados está marcado no título e será rodado só em host de teste
- [ ] `python -m testes_ui rodar casos/seu-arquivo.yaml` passa da validação de formato sem "Roteiro inválido"

## Exemplos prontos

Em `exemplos/`, estes arquivos rodam contra o site de demonstração:

- `aprovado.yaml`: login, preenchimento de campo e três validações. Resultado: aprovado.
- `navegacao.yaml`: login seguido de clique no menu. Resultado: aprovado.
- `invalidado.yaml`: valida um texto que não existe. Resultado: invalidado.
- `erro.yaml`: clica num botão que não existe. Resultado: erro.
