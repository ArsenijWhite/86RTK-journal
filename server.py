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

@app.route('/get_music', methods=['GET'])
def get_music():
    """Возвращает музыку из канала — запрашивает Telegram API напрямую"""
    channel = request.args.get('channel')
    if not channel:
        return jsonify({"error": "Channel required"}), 400
    
    logger.info(f"Fetching music from channel: {channel}")
    
    try:
        # Получаем последние сообщения из канала через Telegram API
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        response = requests.get(url, timeout=30)
        data = response.json()
        
        tracks = []
        
        if data.get('ok'):
            for update in data.get('result', []):
                message = update.get('channel_post') or update.get('message')
                if not message:
                    continue
                
                chat = message.get('chat', {})
                chat_id = str(chat.get('id', ''))
                chat_username = chat.get('username', '')
                
                is_our_channel = False
                if channel.startswith('@'):
                    is_our_channel = chat_username == channel[1:] or chat_username == channel
                else:
                    is_our_channel = chat_id == channel or str(chat_id) == channel
                
                if is_our_channel:
                    audio = message.get('audio')
                    if audio:
                        file_info = requests.get(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={audio['file_id']}",
                            timeout=30
                        ).json()
                        
                        if file_info.get('ok'):
                            audio_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info['result']['file_path']}"
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
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/')
def index():
    return "Music Player API v3.0 - No polling, just API!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
