"""Chamadas ao Claude com saída estruturada via ferramenta.

Alguns modelos recentes não aceitam `tool_choice` forçado (type "tool"/"any"). Por isso a ferramenta
é oferecida em modo automático e, se o modelo responder só com texto, pedimos de novo que a chame.
"""
import anthropic

from . import config

_client = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # usa ANTHROPIC_API_KEY
    return _client


def call_tool(system: str, content, tool_name: str, description: str, schema: dict,
              max_tokens: int = 4096, max_rounds: int = 3) -> dict:
    tools = [{"name": tool_name, "description": description, "input_schema": schema}]
    messages = [{"role": "user", "content": content}]
    for _ in range(max_rounds):
        resp = client().messages.create(
            model=config.CLAUDE_MODEL, max_tokens=max_tokens, system=system, tools=tools, messages=messages)
        for block in resp.content:
            if block.type == "tool_use" and block.name == tool_name:
                return block.input
        # Sem chamada de ferramenta: devolve a resposta e pede explicitamente o registro.
        messages = messages + [
            {"role": "assistant", "content": resp.content},
            {"role": "user", "content": f"Registre agora o resultado chamando a ferramenta `{tool_name}`. "
                                        "Não responda em texto."},
        ]
    raise RuntimeError(f"O modelo não chamou a ferramenta `{tool_name}` após {max_rounds} tentativas.")
