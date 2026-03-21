from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import os
import tempfile
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from PIL import Image
import io
import base64
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "8514929224:AAEmcYywI2h6nwgrBbCIX26G8W1sgEf1fCM"

def extract_cover_from_mp3(mp3_data):
    """Извлекает обложку из MP3 файла"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
            tmp.write(mp3_data)
            tmp_path = tmp.name
        
        audio = MP3(tmp_path, ID3=ID3)
        
        if 'APIC:' in audio.tags:
            apic = audio.tags['APIC:']
            cover_data = apic.data
            cover_base64 = base64.b64encode(cover_data).decode('utf-8')
            os.unlink(tmp_path)
            return f"data:image/jpeg;base64,{cover_base64}"
        
        os.unlink(tmp_path)
        return None
    except Exception as e:
        logger.error(f"Error extracting cover: {e}")
        return None

@app.route('/get_music', methods=['GET'])
def get_music():
    channel = request.args.get('channel')
    if not channel:
        return jsonify({"error": "Channel required"}), 400
    
    logger.info(f"Fetching music from channel: {channel}")
    
    # Используем forwardMessage для получения сообщений из канала
    # Сначала проверяем, что бот имеет доступ к каналу
    try:
        # Получаем информацию о канале
        chat_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat"
        chat_response = requests.get(chat_url, params={"chat_id": channel}, timeout=30)
        chat_data = chat_response.json()
        
        if not chat_data.get('ok'):
            logger.error(f"Cannot access channel: {chat_data}")
            return jsonify({"error": "Cannot access channel. Make sure bot is admin."}), 400
        
        # Получаем последние сообщения через forward (альтернативный метод)
        # Для простоты используем getUpdates с правильным chat_id
        updates_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        updates_response = requests.get(updates_url, timeout=30)
        updates_data = updates_response.json()
        
        tracks = []
        
        if updates_data.get('ok'):
            for update in updates_data.get('result', []):
                message = update.get('channel_post', update.get('message', {}))
                
                # Проверяем, что сообщение из нашего канала
                chat = message.get('chat', {})
                chat_id = str(chat.get('id', ''))
                chat_username = chat.get('username', '')
                
                # Сравниваем с запрошенным каналом
                if channel == chat_username or channel == chat_id:
                    audio = message.get('audio')
                    if audio:
                        # Получаем ссылку на аудио
                        file_info = requests.get(
                            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={audio['file_id']}",
                            timeout=30
                        ).json()
                        
                        if file_info.get('ok'):
                            audio_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info['result']['file_path']}"
                            
                            # Скачиваем MP3 для извлечения обложки
                            mp3_response = requests.get(audio_url, timeout=30)
                            cover_data = extract_cover_from_mp3(mp3_response.content)
                            
                            tracks.append({
                                "id": message['message_id'],
                                "title": audio.get('title', audio.get('file_name', 'Без названия')),
                                "artist": audio.get('performer', 'Неизвестен'),
                                "url": audio_url,
                                "cover": cover_data,
                                "duration": audio.get('duration')
                            })
        
        logger.info(f"Found {len(tracks)} tracks")
        
        if len(tracks) == 0:
            return jsonify({"tracks": [], "message": "No audio files found. Send new audio to channel."})
        
        return jsonify({"tracks": tracks})
    
    except Exception as e:
        logger.error(f"Error in get_music: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/')
def index():
    return "Music Player API with ID3 cover extraction is running!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
