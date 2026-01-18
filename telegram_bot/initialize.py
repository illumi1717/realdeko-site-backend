import requests
import os
from dotenv import load_dotenv

load_dotenv()

def send_telegram_message(message):
    # Вставьте сюда ваш токен
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    # Вставьте ваш Chat ID (куда отправлять)
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    params = {
        'chat_id': os.getenv('ADMIN_CHAT_ID'),
        'text': message
    }
    
    response = requests.post(url, params=params)
    
    if response.status_code == 200:
        print("Сообщение успешно отправлено!")
    else:
        print("Ошибка:", response.text)