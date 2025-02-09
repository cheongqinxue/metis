from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langgraph.managed.is_last_step import RemainingSteps
from langgraph.types import Command
from typing import Any, List, Dict, Annotated, Literal, Sequence, TypedDict
from textwrap import dedent
from tools import search_the_internet, post_tweet
import httpx
from utils.context_window_manager import ContextWindowManager
from functools import partial

httpx_asyncclient = httpx.AsyncClient(
    limits = httpx.Limits(max_keepalive_connections=10, max_connections=10),
)

contextwindowmanager = ContextWindowManager(
    max_context_length=4000,
    llm=ChatOpenAI(model_name="gpt-4o-mini")
)

members = ["researcher", "editor", "writer"]
options = [*members, "FINISH"]

class Router(TypedDict):
    """Worker to route to next. If no workers needed, route to FINISH."""
    next: Literal[*options]

# Workflow State Definition
class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    past_tweets: Annotated[Sequence[str], add_messages]
    remaining_steps: RemainingSteps
    next: str


####################################################################################################
# Agent Nodes
####################################################################################################

async def supervisor_node(
    state: State
) -> Command[Literal[*members, "__end__"]]:
    system_prompt = dedent(
        """You are a supervisor tasked with managing conversation between the following workers: {members}. \
        Given the following user request, respond with the worker to act next. \
        Each worker will perform a task and respond with their results and status. \
        When finished, respond with FINISH.
        """)
    messages = [
        {"role": "system", "content": system_prompt},
    ] + state["messages"]
    llm = ChatOpenAI(
        model_name="gpt-4o-mini",
        temperature=0,
        http_async_client=httpx_asyncclient,
    )
    response = await llm.with_structured_output(Router).ainvoke(messages)
    goto = response["next"]
    if goto == "FINISH":
        goto = END

    return Command(goto=goto, update={"next": goto})


async def research_node(state: State) -> Command[Literal["supervisor"]]:
    
    research_agent = create_react_agent(
        tools=[search_the_internet],
        model=ChatOpenAI(
            model_name="gpt-4o-mini", 
            temperature=0,
            http_async_client=httpx_asyncclient,
        ),
        prompt = "You are a researcher. Your job is to perform research on the internet and report your findings. Do not write tweets or perform any other actions.",
    )

    result = await research_agent.ainvoke(state)
    return Command(
        update={
            "messages": [
                HumanMessage(content=result["messages"][-1].content, name="researcher")
            ]
        },
        goto="supervisor",
    )


async def editor_node(
        state: State,
        config: RunnableConfig,
    ) -> Command[Literal["supervisor"]]:

    character_name = config["configurable"]["character_name"]
    
    editor_agent = create_react_agent(
        tools=[post_tweet],
        model=ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0,
            http_async_client=httpx_asyncclient,
        ),
        prompt = dedent(
            f"""You are an editor. Your job is to scrutinize the writer's output and \
            ensure that it meets the requirements of {character_name}'s character description. \
            You will critique the output and ask the writer to revise the output if necessary. \
            Remember that the tweet must sound original and different than the past tweets. \
            If the output is satisfactory, you will post it to twitter. \
            
            ## Sidenote:
            There are {state['remaining_steps']} hours left to your publish deadline. \
            If there are less than 2 hours left, you must post the tweet immediately. 
            """),
    )

    result = await editor_agent.ainvoke(state)
    return Command(
        update={
            "messages": [
                HumanMessage(content=result["messages"][-1].content, name="editor")
            ]
        },
        goto="supervisor",
    )


async def writer_node(
        state: State,
        config: RunnableConfig,
    ) -> Command[Literal["editor"]]:
    writer_agent = create_react_agent(
        tools=[],
        model=ChatOpenAI(
            model_name="gpt-4o-mini",
            temperature=0,
            http_async_client=httpx_asyncclient,
        ),
        prompt = dedent(
            """You are a writer. \
            Your job is to write a tweet that matches the style of the character description. \
            You will write the tweet and send it to the editor for review.
            """),
    )
    result = await writer_agent.ainvoke(state)
    return Command(
        update={
            "messages": [
                HumanMessage(content=result["messages"][-1].content, name="writer")
            ]
        },
        goto="editor",
    )



def make_agent():
    builder = StateGraph(State)
    builder.add_edge(START, "supervisor")
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("researcher", research_node)
    builder.add_node("editor", editor_node)
    builder.add_node("writer", writer_node)
    graph = builder.compile()
    return graph

if __name__ == "__main__":
    pass