from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import requests
import os
import io
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from PIL import Image
import tempfile

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "8514929224:AAEmcYywI2h6nwgrBbCIX26G8W1sgEf1fCM"

def extract_cover_from_mp3(mp3_data):
    """Извлекает обложку из MP3 файла"""
    try:
        # Создаём временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
            tmp.write(mp3_data)
            tmp_path = tmp.name
        
        # Читаем ID3 теги
        audio = MP3(tmp_path, ID3=ID3)
        
        if 'APIC:' in audio.tags:
            apic = audio.tags['APIC:']
            cover_data = apic.data
            
            # Сохраняем обложку в bytes
            img = Image.open(io.BytesIO(cover_data))
            
            # Конвертируем в JPEG и возвращаем
            output = io.BytesIO()
            img.convert('RGB').save(output, format='JPEG', quality=85)
            output.seek(0)
            
            os.unlink(tmp_path)  # Удаляем временный файл
            return output.getvalue()
        
        os.unlink(tmp_path)
        return None
    except Exception as e:
        print(f"Error extracting cover: {e}")
        return None

@app.route('/get_music', methods=['GET'])
def get_music():
    channel = request.args.get('channel')
    if not channel:
        return jsonify({"error": "Channel required"}), 400
    
    # Получаем последние сообщения из канала
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"chat_id": channel, "limit": 50}
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        tracks = []
        
        if data.get('ok'):
            for msg in data.get('result', []):
                message = msg.get('message', {})
                
                # Ищем аудио
                audio = message.get('audio')
                if audio:
                    # Получаем ссылку на аудио
                    file_info = requests.get(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={audio['file_id']}"
                    ).json()
                    
                    if file_info.get('ok'):
                        audio_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info['result']['file_path']}"
                        
                        # Скачиваем MP3 для извлечения обложки
                        mp3_response = requests.get(audio_url)
                        cover_data = extract_cover_from_mp3(mp3_response.content)
                        
                        # Если обложка извлечена, сохраняем её временно
                        cover_url = None
                        if cover_data:
                            # Сохраняем обложку в памяти (можно сохранить на диск)
                            # Для простоты вернём base64
                            import base64
                            cover_url = f"data:image/jpeg;base64,{base64.b64encode(cover_data).decode()}"
                        
                        tracks.append({
                            "id": message['message_id'],
                            "title": audio.get('title', audio.get('file_name', 'Без названия')),
                            "artist": audio.get('performer', 'Неизвестен'),
                            "url": audio_url,
                            "cover": cover_url,
                            "duration": audio.get('duration')
                        })
        
        return jsonify({"tracks": tracks})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "Music Player API with ID3 cover extraction!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)