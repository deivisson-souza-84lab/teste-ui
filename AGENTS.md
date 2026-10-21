# Guia para agentes de IA

Este arquivo é para uma IA que vai ajudar a escrever ou revisar roteiros do testes-ui. Leia-o inteiro antes de criar qualquer arquivo.

## O que é o testes-ui

Um programa que executa roteiros YAML no navegador: login, ações, validações e prints. Você não escreve código Python para testar. Escreve YAML.

- A fonte de verdade do formato é a saída de `python -m testes_ui ajuda`. Não invente campos, ações nem validações.
- O tutorial para humanos está em `TUTORIAL.md`. Exemplos prontos estão em `exemplos/`.

## Regras de segurança

1. **Nunca escreva, envie nem faça pipe de `CONFIRMO`.** A confirmação é do humano.
2. **Nunca peça, grave ou repita login e senha.** O humano digita as credenciais no próprio terminal. Credenciais não entram em roteiros, comentários, comandos nem arquivos.
3. **A IA não executa testes.** `rodar` e `inspecionar` só são executados pela IA se o humano pedir expressamente. Por padrão, a execução parte do terminal do humano: peça que ele rode o comando e informe o comando exato. `ajuda` e `checar` não executam testes nem pedem nada, então você pode usá-los.
4. **Não aponte roteiros para um host que o humano não indicou.**
5. **Casos que criam, alteram ou removem dados** precisam dizer isso no título e só devem rodar em host de teste. Confirme com o humano antes de criar um caso desses.
6. **Arquivos de `inspecionar` podem conter dados reais** (nomes, valores de campos, linhas de tabela). Use deles só papéis e nomes de controles. Nunca copie valores de dados para o roteiro.

## Fluxo de trabalho

1. Leia o formato atual: `python -m testes_ui ajuda`. Se o seu cliente tiver as ferramentas MCP do testes-ui, use `ajuda` e `checar_texto` no lugar dos comandos de terminal.
2. Pergunte ao humano só o necessário:
   - o host;
   - a página em que o caso começa, se houver;
   - se há login (pergunte o nome do usuário, nunca a senha);
   - o resultado esperado, em frases.
3. Crie um rascunho em `casos/` com `id`, `titulo`, `host`, `login` (se houver) e `acessar`. Ainda sem `testar` nem `validar`.
4. Peça ao humano que leia a tela no terminal dele:

   ```
   python -m testes_ui inspecionar casos/<arquivo>.yaml --seletor "<CSS da área>"
   ```

   Ele deve informar o caminho do arquivo gerado em `saidas/inspecoes/`. Use `--seletor` para a área do formulário ou do conteúdo. Uma listagem com 25 linhas gera mais de 400 linhas de árvore, e as linhas de dados não ajudam a escolher alvos.
5. Escolha os alvos a partir desse arquivo. Cada linha traz o papel e o nome:
   - `- textbox "Ano"` vira `{papel: textbox, nome: Ano}`;
   - `- link "Cadastro"` vira `{papel: link, nome: Cadastro}`;
   - `- heading "Lista de pedidos"` serve para `texto_visivel`.

   Não invente nomes que não aparecem no arquivo.
6. Escreva `testar` e `validar`. Cada validação deve falhar se a funcionalidade quebrar. Confirmar só que a página abriu é pouco; prefira confirmar um dado que o usuário veria.
7. Rode `python -m testes_ui checar casos/<arquivo>.yaml` e corrija até aparecer `OK`.
8. Peça ao humano que rode, no terminal dele:

   ```
   python -m testes_ui rodar casos/<arquivo>.yaml --screenshots all
   ```

   Ele deve digitar a confirmação, o login e a senha.
9. Leia `saidas/<data-hora>/<ID>.json` ou o resumo que o humano colar. Interprete o resultado (próxima seção), ajuste o roteiro e volte ao passo 7.

## Como interpretar o resultado

- **aprovado**: todos os passos foram confirmados.
- **invalidado**: uma validação não foi confirmada. A tela pode estar errada, ou o valor esperado pode estar errado. Veja o print antes de mudar qualquer coisa.
- **erro**: um passo não pôde ser executado. Na maioria das vezes o problema está no roteiro: alvo errado, alvo ambíguo, login recusado, tempo insuficiente. Não é prova de defeito no sistema.

Nunca enfraqueça uma validação para fazer um caso passar. Se um `invalidado` aparecer, descubra o motivo. Se o motivo for real, a validação está certa e o caso deve continuar falhando, para o humano decidir.

## Escolha de alvos

Ordem de preferência: `rotulo`, depois `papel` com `nome`, depois `texto`, e `css` só como último recurso.

Se a mensagem disser `o alvo encontrou N elementos visíveis`, troque o alvo por um que tenha nome mais específico, como o rótulo do campo ou o papel com o nome completo do controle. Não use `css` com classes de visual para resolver ambiguidade sem avisar o humano.

## Boas práticas

- Um caso por comportamento. O `id` tem prefixo da tela e número: `CAD-001`.
- Títulos descrevem o comportamento verificado, não o passo a passo.
- Nenhum caso depende de outro. Cada um faz o próprio login.
- Diga ao humano quais dados o caso espera (por exemplo, "precisa haver um pedido no ano 2026"). Quem executa garante esses dados.

## O que você não deve fazer

- Alterar o código do `testes_ui` para um teste passar.
- Remover ou enfraquecer validações para resolver um `invalidado`.
- Criar arquivos fora de `casos/` sem pedido, ou mexer em `saidas/`.
- Guardar prints, credenciais ou dados da tela em qualquer arquivo versionado.
