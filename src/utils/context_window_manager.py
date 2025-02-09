from typing import Sequence
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    BaseMessage, 
    filter_messages
)
from langchain_core.language_models.chat_models import BaseChatModel

class ContextWindowManager:

    def __init__(
            self, 
            max_context_length: int, 
            llm: BaseChatModel = None,
            ):
        self.max_context_length = max_context_length
        self.llm = llm

    def limit_messages(
        self,
        messages: Sequence[BaseMessage],
        llm: BaseChatModel = None,
    )-> Sequence[BaseMessage]:
        
        if llm is None:
            llm = self.llm

        if llm is None:
            raise ValueError("No LLM provided")
        
        system = filter_messages(messages, include_types=[SystemMessage])
        other_messages = filter_messages(messages, exclude_types=[SystemMessage])

        while llm.get_num_tokens_from_messages(system + other_messages) > self.max_context_length:

            other_messages = other_messages[1:]
        
        if len(other_messages) == 0:
            raise ValueError("No messages left after context window limit")
        
        return system + other_messages