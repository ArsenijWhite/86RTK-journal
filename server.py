from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "8514929224:AAEmcYywI2h6nwgrBbCIX26G8W1sgEf1fCM"

# Хранилище последних обновлений
last_updates = []

def get_cover_url(audio_data):
    """Получает URL обложки из thumbnail"""
    try:
        thumbnail = audio_data.get('thumbnail') or audio_data.get('thumb')
        if thumbnail:
            file_id = thumbnail['file_id']
            file_info = requests.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}",
                timeout=30
            ).json()
            
            if file_info.get('ok'):
                file_path = file_info['result']['file_path']
                return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    except Exception as e:
        logger.error(f"Error getting cover: {e}")
    return None

def poll_updates():
    """Постоянно получает обновления от Telegram"""
    global last_updates
    offset = 0
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            params = {"offset": offset, "timeout": 30}
            
            response = requests.get(url, params=params, timeout=35)
            data = response.json()
            
            if data.get('ok') and data.get('result'):
                for update in data['result']:
                    update_id = update.get('update_id')
                    if update_id:
                        offset = update_id + 1
                        last_updates.append(update)
                        if len(last_updates) > 100:
                            last_updates = last_updates[-100:]
                        
                        # Логируем
                        msg = update.get('message') or update.get('channel_post')
                        if msg and msg.get('audio'):
                            logger.info(f"🎵 New audio: {msg['audio'].get('title', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"Polling error: {e}")
        
        import time
        time.sleep(1)

@app.route('/get_music', methods=['GET'])
def get_music():
    """Возвращает музыку из канала"""
    channel = request.args.get('channel')
    if not channel:
        return jsonify({"error": "Channel required"}), 400
    
    logger.info(f"Fetching music from channel: {channel}")
    
    tracks = []
    
    for update in last_updates:
        message = update.get('channel_post') or update.get('message')
        if not message:
            continue
        
        chat = message.get('chat', {})
        chat_id = str(chat.get('id', ''))
        chat_username = chat.get('username', '')
        
        # Проверяем, что сообщение из нашего канала
        is_our_channel = False
        if channel.startswith('@'):
            is_our_channel = chat_username == channel[1:] or chat_username == channel
        else:
            is_our_channel = chat_id == channel or str(chat_id) == channel
        
        if is_our_channel:
            audio = message.get('audio')
            if audio:
                # Получаем ссылку на аудио
                file_info = requests.get(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={audio['file_id']}",
                    timeout=30
                ).json()
                
                if file_info.get('ok'):
                    audio_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info['result']['file_path']}"
                    
                    # Получаем обложку из thumbnail
                    cover_url = get_cover_url(audio)
                    
                    tracks.append({
                        "id": message['message_id'],
                        "title": audio.get('title', audio.get('file_name', 'Без названия')),
                        "artist": audio.get('performer', 'Неизвестен'),
                        "url": audio_url,
                        "cover": cover_url,
                        "duration": audio.get('duration')
                    })
    
    logger.info(f"Found {len(tracks)} tracks")
    return jsonify({"tracks": tracks})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "updates_count": len(last_updates)}), 200

@app.route('/')
def index():
    return "Music Player API v3.0 - Working with thumbnails!"

# Запускаем polling
import threading
polling_thread = threading.Thread(target=poll_updates, daemon=True)
polling_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info("Starting server...")
    app.run(host='0.0.0.0', port=port)
