from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import os
import tempfile
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
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
    
    try:
        # Получаем последние сообщения из канала через getUpdates
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        response = requests.get(url, timeout=30)
        data = response.json()
        
        tracks = []
        
        if data.get('ok'):
            logger.info(f"Got {len(data['result'])} updates")
            
            for update in data['result']:
                # Проверяем оба типа: channel_post и message
                message = update.get('channel_post') or update.get('message')
                
                if not message:
                    continue
                
                # Получаем информацию о чате
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
                    # Ищем аудио
                    audio = message.get('audio')
                    if audio:
                        logger.info(f"Found audio: {audio.get('title', 'Unknown')}")
                        
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
        
        logger.info(f"Total tracks found: {len(tracks)}")
        
        if len(tracks) == 0:
            return jsonify({
                "tracks": [], 
                "message": "No audio files found. Make sure:\n1. Bot is admin in channel\n2. Send NEW audio after adding bot\n3. Audio files are in MP3 format"
            })
        
        return jsonify({"tracks": tracks})
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/')
def index():
    return "Music Player API v2.0 - Ready to receive music from channel!"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
