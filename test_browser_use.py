from langchain_openai import ChatOpenAI
from browser_use import Agent, Browser, BrowserConfig
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()  # Завантаження змінних середовища з .env файлу

async def main():
    # Перевірка наявності ключа API
    if not os.environ.get("OPENAI_API_KEY"):
        print("Помилка: OPENAI_API_KEY не знайдено в змінних середовища.")
        return
        
    # Створення браузера з бажаними налаштуваннями
    browser_config = BrowserConfig(headless=False)  # Видимий режим
    browser = Browser(config=browser_config)
    
    # Створення агента
    agent = Agent(
        task="Відкрити сторінку Google і ввести запит 'test browser-use'",
        llm=ChatOpenAI(model="gpt-4o"),
        browser=browser,
    )
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main()) 