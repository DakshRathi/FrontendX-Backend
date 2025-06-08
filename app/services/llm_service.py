# app/services/llm_service.py
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from app.core.config import settings

# Initialize the Groq Chat model
llm = ChatGroq(
    model_name="llama3-70b-8192",
    groq_api_key=settings.GROQ_API_KEY
)

# System prompt to define the LLM's role and context
SYSTEM_PROMPT_TEMPLATE = """
You are an expert frontend performance analyst. Your name is "Pulse".
Your task is to analyze the provided Lighthouse report summary and answer the user's questions strictly based on it.
You are not allowed to answer queries unrelated to the provided website report.

All responses must be formatted **strictly** in Markdown and enclosed **within triple backticks (```markdown)**. Do not include anything before or after the markdown block.

Here is the Lighthouse report summary for the website being discussed:
{report_summary}
"""

# Create a prompt template that includes the system message, chat history, and user input
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT_TEMPLATE),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{query}"),
    ]
)

# Create the LangChain chain
chain = prompt | llm | StrOutputParser()

async def get_initial_suggestion(report_summary: str) -> str:
    """
    Gets a single, non-streamed initial suggestion from the LLM.
    Uses .ainvoke() for a single, complete response.

    Args:
        report_summary: The Lighthouse report summary to base the suggestion on.

    Returns:
        A brief, high-level overview of the website's performance.
    """
    initial_prompt = (
        "Based on the Lighthouse report summary, provide a brief, high-level overview "
        "of the website's performance. Start with a friendly greeting and highlight "
        "key areas for improvement in a concise, encouraging tone. Keep the entire response to less than 10 sentences."
    )
    
    response = await chain.ainvoke({
        "history": [],  # No prior history for the initial suggestion
        "query": initial_prompt,
        "report_summary": report_summary
    })
    
    return response

async def get_llm_stream(history: list, query: str, report_summary: str):
    """
    Streams the LLM response.

    Args:
        history: The list of previous ChatMessage objects.
        query: The user's new query.
        report_summary: The Lighthouse report summary.

    Yields:
        Chunks of the response string from the LLM.
    """
    # Convert Pydantic models to LangChain message objects
    langchain_history = []
    for msg in history:
        if msg.role == "user":
            langchain_history.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            langchain_history.append(AIMessage(content=msg.content))
    
    # Stream the response
    async for chunk in chain.astream({
        "history": langchain_history,
        "query": query,
        "report_summary": report_summary
    }):
        yield chunk
