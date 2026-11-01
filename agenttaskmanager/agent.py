from google.adk.agents.llm_agent import Agent
from trello import TrelloClient
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import os
import unicodedata

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

API_KEY = os.getenv("TRELLO_API_KEY")
API_SECRET = os.getenv("TRELLO_API_SECRET")
TOKEN = os.getenv("TRELLO_TOKEN")
BOARD_NAME = os.getenv("TRELLO_BOARD_NAME", "DIO")

FUSO_BRASIL = timezone(timedelta(hours=-3))

STATUS_CANONICO = {
    "a fazer": "A FAZER",
    "afazer": "A FAZER",
    "to do": "A FAZER",
    "todo": "A FAZER",
    "em andamento": "EM ANDAMENTO",
    "andamento": "EM ANDAMENTO",
    "doing": "EM ANDAMENTO",
    "fazendo": "EM ANDAMENTO",
    "concluido": "CONCLUIDO",
    "concluida": "CONCLUIDO",
    "done": "CONCLUIDO",
    "feito": "CONCLUIDO",
    "finalizado": "CONCLUIDO",
    "finalizada": "CONCLUIDO",
}

NOMES_DE_LISTA = {
    "A FAZER": ("a fazer", "to do", "todo"),
    "EM ANDAMENTO": ("em andamento", "doing"),
    "CONCLUIDO": ("concluido", "done"),
}


def _sem_acento(texto: str) -> str:
    normalizado = unicodedata.normalize("NFD", texto or "")
    sem_marca = "".join(
        caractere
        for caractere in normalizado
        if unicodedata.category(caractere) != "Mn"
    )
    return " ".join(sem_marca.strip().lower().split())


def _conectar_trello() -> TrelloClient:
    if not API_KEY or not TOKEN:
        raise ValueError("Credenciais do Trello ausentes no arquivo .env")
    return TrelloClient(api_key=API_KEY, api_secret=API_SECRET, token=TOKEN)


def _obter_quadro(client: TrelloClient):
    quadros = client.list_boards()
    for quadro in quadros:
        if quadro.name == BOARD_NAME:
            return quadro
    raise ValueError(f"Quadro '{BOARD_NAME}' não encontrado")


def _status_canonico(status: str) -> str | None:
    return STATUS_CANONICO.get(_sem_acento(status))


def _lista_do_status(listas, status_canonico: str):
    aceitos = set(NOMES_DE_LISTA[status_canonico])
    for lista in listas:
        if _sem_acento(lista.name) in aceitos:
            return lista
    return None


def _vencimento_com_fuso(due_date: str) -> str:
    """Meio-dia no fuso -03:00, para o Trello não gravar o dia anterior."""
    texto = (due_date or "").strip().replace("/", "-")
    if len(texto) >= 10 and texto[4] == "-" and texto[7] == "-":
        dia = texto[:10]
        return f"{dia}T12:00:00-03:00"
    agora = datetime.now(FUSO_BRASIL)
    return agora.strftime("%Y-%m-%dT12:00:00-03:00")


def get_temporal_context() -> str:
    """Devolve a data e a hora atuais no fuso de Brasília (UTC-3)."""
    agora = datetime.now(FUSO_BRASIL)
    return agora.strftime("%Y/%m/%d %H:%M:%S")


def adicionar_tarefa(nome_da_task: str, descricao_da_task: str, due_date: str) -> str:
    """Cria um card na lista A fazer do quadro.

    Args:
        nome_da_task: título curto da tarefa.
        descricao_da_task: o que precisa ser feito.
        due_date: vencimento no formato AAAA-MM-DD.
    """
    try:
        client = _conectar_trello()
        quadro = _obter_quadro(client)
        listas = quadro.list_lists()
        lista_destino = _lista_do_status(listas, "A FAZER")
        if lista_destino is None:
            return "Lista 'A fazer' não encontrada no quadro"
        vencimento = _vencimento_com_fuso(due_date)
        card = lista_destino.add_card(
            name=nome_da_task,
            desc=descricao_da_task,
            due=vencimento,
        )
        return (
            f"Tarefa '{card.name}' criada em '{lista_destino.name}' "
            f"com vencimento {vencimento}"
        )
    except Exception as erro:
        return f"Erro ao adicionar tarefa: {erro}"


def listar_tarefas(status: str = "todas") -> str | list:
    """Lista os cards do quadro, todos ou só os de um status.

    Args:
        status: todas, a fazer, em andamento ou concluído.
    """
    try:
        client = _conectar_trello()
        quadro = _obter_quadro(client)
        listas = quadro.list_lists()
        pedido = _sem_acento(status)
        if pedido in ("todas", "tudo", "all", ""):
            listas_filtradas = listas
        else:
            canonico = _status_canonico(status)
            if canonico is None:
                return (
                    "Status inválido. Use: 'a fazer', 'em andamento', "
                    "'concluído' ou 'todas'"
                )
            lista = _lista_do_status(listas, canonico)
            listas_filtradas = [lista] if lista is not None else []
        tarefas = []
        for lista in listas_filtradas:
            for card in lista.list_cards():
                tarefas.append(
                    {
                        "nome": card.name,
                        "descricao": card.desc,
                        "vencimento": str(card.due) if card.due else "",
                        "status": lista.name,
                        "id": card.id,
                    }
                )
        if not tarefas:
            return "Nenhuma tarefa encontrada"
        return tarefas
    except Exception as erro:
        return f"Erro ao listar tarefas: {erro}"


def mudar_status_tarefa(nome_da_task: str, novo_status: str) -> str:
    """Move um card entre A fazer, Em andamento e Concluído.

    Args:
        nome_da_task: nome exato do card.
        novo_status: a fazer, em andamento ou concluído. Aceita acento.
    """
    try:
        client = _conectar_trello()
        quadro = _obter_quadro(client)
        listas = quadro.list_lists()
        canonico = _status_canonico(novo_status)
        if canonico is None:
            return (
                "Status inválido. Use: 'a fazer', 'em andamento' ou 'concluído'"
            )
        lista_destino = _lista_do_status(listas, canonico)
        if lista_destino is None:
            return f"Lista '{canonico}' não encontrada no quadro"
        card_encontrado = None
        lista_origem = None
        for lista in listas:
            for card in lista.list_cards():
                if card.name.lower() == nome_da_task.lower():
                    card_encontrado = card
                    lista_origem = lista
                    break
            if card_encontrado is not None:
                break
        if card_encontrado is None:
            return f"Card '{nome_da_task}' não encontrado"
        card_encontrado.change_list(lista_destino.id)
        return f"'{nome_da_task}': {lista_origem.name} → {lista_destino.name}"
    except Exception as erro:
        return f"Erro ao mudar status: {erro}"


root_agent = Agent(
    model="gemini-3.5-flash",
    name="root_agent",
    description="Agente de organização de tarefas no Trello",
    instruction="""
Você é um agente de organização de tarefas no Trello.
Assim que a conversa começar, chame get_temporal_context e pergunte quais são as tarefas do dia, dizendo a data de hoje.
Para cada tarefa informada, chame adicionar_tarefa com nome, descrição e a data no formato AAAA-MM-DD.
Use a data de hoje, a menos que a pessoa diga outra.
Depois de criar, pergunte se há mais alguma tarefa, até a pessoa dizer que não.
Quando ela contar o que já fez ou o que está fazendo, chame mudar_status_tarefa.
Aceite concluído, concluida, done, em andamento e a fazer.
Para mostrar o quadro, chame listar_tarefas. O status pode ser todas, a fazer, em andamento ou concluído.
Você só cria, lista e move cards. Não apaga tarefa.
""",
    tools=[
        get_temporal_context,
        adicionar_tarefa,
        listar_tarefas,
        mudar_status_tarefa,
    ],
)
