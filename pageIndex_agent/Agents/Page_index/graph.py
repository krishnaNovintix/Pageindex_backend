from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from Agents.Page_index.tools import index_pdf, retrieve_from_pdf

_agent = None


def get_agent():
    global _agent
    if _agent is None:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)
        _agent = create_react_agent(llm, [index_pdf, retrieve_from_pdf])
    return _agent
