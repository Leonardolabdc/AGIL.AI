# Arquivo: whisper_api.py
# Descrição: API Flask simples para Speech-to-Text (STT) usando o modelo Whisper.

import os
import uuid
from flask import Flask, request, jsonify
import whisper
import logging
import shutil
import time

# Configuração de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- INICIALIZAÇÃO DO MODELO WHISPER ---
try:
    logger.info("Carregando modelo Whisper 'tiny'...")
    # 'device="cpu"' força o uso da CPU, ideal para ambientes Docker sem GPU dedicada.
    # O modelo 'tiny' é o mais leve para processar áudios curtos (máx 5s) em testes.
    model = whisper.load_model("tiny", device="cpu") 
    logger.info("Modelo Whisper carregado com sucesso!")
except Exception as e:
    logger.error(f"ERRO CRÍTICO ao carregar o modelo Whisper: {e}")
    # Se o modelo não carregar, a API deve falhar para evitar execuções incompletas.
    raise

app = Flask(__name__)

@app.route('/transcribe', methods=['POST'])
def transcribe_audio():
    # 1. Verificar se o arquivo foi enviado corretamente (espera 'audio_file' no multipart form data)
    if 'audio_file' not in request.files:
        return jsonify({"error": "Nenhum arquivo 'audio_file' encontrado no payload"}), 400

    audio_file = request.files['audio_file']
    if audio_file.filename == '':
        return jsonify({"error": "Arquivo vazio"}), 400

    temp_path = None
    start_time = time.time()

    try:
        # 2. Salvar o arquivo temporariamente no disco do contêiner (/tmp)
        file_extension = os.path.splitext(audio_file.filename)[1]
        temp_path = f"/tmp/{uuid.uuid4()}{file_extension}"
        
        # Salva o arquivo de upload na pasta temporária
        audio_file.save(temp_path)
        logger.info(f"Arquivo temporário salvo em: {temp_path}")

        # 3. Processar a transcrição
        logger.info("Iniciando transcrição com Whisper...")
        
        # Chama a função de transcrição do Whisper. Usamos 'pt' para focar no português.
        result = model.transcribe(temp_path, language="pt") 
        
        transcribed_text = result["text"].strip()
        duration = time.time() - start_time
        logger.info(f"Transcrição concluída em {duration:.2f}s. Texto: {transcribed_text[:50]}...")

        # 4. Retornar a transcrição para o n8n
        return jsonify({
            "status": "success",
            "transcription": transcribed_text,
            "duration_s": duration,
            "language": result.get("language")
        })

    except Exception as e:
        logger.error(f"Erro durante a transcrição: {e}")
        return jsonify({"error": f"Erro interno na API de transcrição: {e}"}), 500

    finally:
        # 5. Limpeza Crítica: Remover o arquivo temporário
        # CRUCIAL para evitar que o disco do contêiner encha.
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"Arquivo temporário removido: {temp_path}")
            except Exception as clean_error:
                logger.error(f"Erro ao remover arquivo temporário: {clean_error}")

@app.route('/')
def health_check():
    # Endpoint de verificação de saúde para o Docker Compose e monitoramento.
    return jsonify({"message": "API Whisper STT está funcionando!", "status": "ok"})
