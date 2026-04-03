import asyncio
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from Agents.slack_agent.graph import build_graph

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


async def main():
    chatbot = await build_graph()

    thread_id = "chat-2"
    exit_words = {"bye", "exit", "quit"}

    while True:
        user_message = input("User: ").strip()
        if not user_message:
            continue

        if user_message.lower() in exit_words:
            print("Assistant: Bye!")
            break

        result = await chatbot.ainvoke(
            {"messages": [HumanMessage(content=user_message)]},
            config={"configurable": {"thread_id": thread_id}},
        )

        print("Assistant:", result["messages"][-1].text)


if __name__ == "__main__":
    asyncio.run(main())