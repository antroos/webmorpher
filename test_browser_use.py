from langchain_openai import ChatOpenAI
from browser_use import Agent
import asyncio
from dotenv import load_dotenv

load_dotenv()  # Завантаження змінних середовища з .env файлу

async def main():
    agent = Agent(
        task="Відкрити сторінку Google і ввести запит 'test browser-use'",
        llm=ChatOpenAI(model="gpt-4o"),
    )
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main()) 