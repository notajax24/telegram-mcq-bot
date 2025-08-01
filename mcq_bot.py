import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import httpx
import logging

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
scheduler = AsyncIOScheduler()
logging.basicConfig(level=logging.INFO)

# Step 1: Generate MCQs
async def generate_mcqs():
    prompt = (
        "Generate 50 English multiple-choice questions (MCQs) for SSC CGL, IBPS PO, SBI PO, SO, Clerk. "
        "Each MCQ should include:\n"
        "- Question\n"
        "- 4 options\n"
        "- Correct answer (match one of the options)\n"
        "Return as a Python list of dictionaries:\n"
        "[{'question': '...', 'options': ['a', 'b', 'c', 'd'], 'answer': 'b'}, ...]"
    )

    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "pplx-7b-online",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post("https://api.perplexity.ai/chat/completions", json=payload, headers=headers)
            res.raise_for_status()
            content = res.json()["choices"][0]["message"]["content"]
            mcqs = eval(content.strip())
            return mcqs if isinstance(mcqs, list) else []
    except Exception as e:
        logging.error(f"Perplexity API Error: {e}")
        return []

# Step 2: Send MCQs
async def send_mcqs():
    mcqs = await generate_mcqs()
    if not mcqs:
        await bot.send_message(chat_id=GROUP_ID, text="❌ Failed to generate MCQs today.")
        return

    for i, mcq in enumerate(mcqs[:50]):
        try:
            question = mcq["question"]
            options = mcq["options"]
            correct_option = options.index(mcq["answer"]) if mcq["answer"] in options else 0

            await bot.send_poll(
                chat_id=GROUP_ID,
                question=f"📝 Q{i+1}. {question}",
                options=options,
                type='quiz',
                correct_option_id=correct_option,
                is_anonymous=False
            )
            await asyncio.sleep(40)
        except Exception as e:
            logging.error(f"Error sending MCQ {i+1}: {e}")
            continue

# Step 3: Start
async def main():
    scheduler.add_job(send_mcqs, 'cron', hour=12, minute=10)
    scheduler.start()
    logging.info("Bot started and scheduler set for 12:10 PM daily.")

    # Keeps the bot running
    while True:
        await asyncio.sleep(3600)

if __name__ == '__main__':
    asyncio.run(main())
