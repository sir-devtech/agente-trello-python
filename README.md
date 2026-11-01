# Agente de tarefas no Trello

Montei um agente em Python que conversa comigo e joga as tarefas do dia num quadro do Trello. Usei o Agent Development Kit do Google com o Gemini. A ideia é essa: cada função do `agent.py` vira uma ferramenta, e o modelo escolhe qual chamar a partir do que eu escrevo.

O quadro se chama **DIO**. As listas são **A fazer**, **Em andamento** e **Concluído**.

## O que ele faz na conversa

Ele começa pedindo a data de agora, no fuso de Brasília, e pergunta o que eu tenho para fazer. Cada tarefa vira um card em **A fazer**, com nome, descrição e vencimento. Se eu pedir para ver o quadro, ele lista tudo ou só um status. Se eu contar que terminei alguma coisa, ele move o card. Dá para falar **concluído** com acento.

As ferramentas estão no `agenttaskmanager/agent.py`:

- `get_temporal_context` pega data e hora
- `adicionar_tarefa` cria o card
- `listar_tarefas` lê o quadro
- `mudar_status_tarefa` muda o card de lista

## O que eu ajustei

O código da aula mandava a data só como `AAAA-MM-DD`. O Trello entende isso como meia-noite em UTC. No Brasil, UTC-3, o card nascia no dia anterior. A função `_vencimento_com_fuso` manda a mesma data ao meio-dia, com o offset `-03:00`. No teste de 1 de novembro os dois cards ficaram em **1 de nov.**, que foi o dia que eu falei.

A outra quebra era o status. O original só aceitava `concluido`, sem acento. `concluído` voltava status inválido e a conversa em português travava na hora de mover. Agora a comparação tira o acento antes de achar a lista. Vale para listar e para mover.

A conexão com o `py-trello` estava repetida dentro de cada função. Deixei isso em `_conectar_trello`. As ferramentas também têm `try/except` e devolvem o erro em texto, então uma chave faltando ou um quadro com outro nome não derruba o `adk web`.

A instrução do agente, no material, prometia apagar tarefa. Essa função não existe. Tirei a frase. O texto que o Gemini lê agora só descreve criar, listar e mover.

O modelo do material era o `gemini-2.5-flash`. Na chave nova a API respondeu que ele não está mais disponível para conta nova. Troquei para `gemini-3.5-flash`, que foi o que respondeu no teste.

## Como eu subi

Python 3.13, com ambiente virtual.

No Trello criei o quadro **DIO** e um aplicativo em [trello.com/power-ups/admin](https://trello.com/power-ups/admin). Anotei a chave e o segredo, e gerei o token nesta URL, trocando `SUA_CHAVE`:

```
https://trello.com/1/authorize?expiration=never&name=AgenteTrelloDIO&scope=read,write&response_type=token&key=SUA_CHAVE
```

A chave do Gemini veio do [AI Studio](https://aistudio.google.com/apikey).

Copiei `agenttaskmanager/.env.exemplo` para `agenttaskmanager/.env` e preenchi. O `.env` está no `.gitignore`. No GitHub só entra o exemplo, com texto falso no lugar das chaves. Se o quadro tiver outro nome, muda `TRELLO_BOARD_NAME`.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
adk web
```

No navegador, o agente é o `agenttaskmanager`.

## O teste

No `adk web` eu falei a tarefa **estudar Python**, com a descrição de revisar as funções do agente, no dia 1 de novembro de 2026. O agente chamou `get_temporal_context` e `adicionar_tarefa`. Depois pedi a lista e mandei marcar como concluído. Ele chamou `mudar_status_tarefa` e `listar_tarefas`.

No quadro, **A fazer** e **Em andamento** ficaram vazias. **Concluído** ficou com **Comprar comida** e **estudar Python**, os dois em 1 de novembro.

![Conversa no adk web](evidencias/conversa-adk.png)

![Quadro DIO depois do teste](evidencias/quadro-trello.png)

O nome do card precisa ser o mesmo na hora de mover. Se eu falar um nome parecido, ele não acha. Também não apaga card. Isso eu deixei de fora de propósito, porque a ferramenta não existe.
