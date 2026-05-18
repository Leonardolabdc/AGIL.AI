# Arquivo: kokoro_api.py
# Descrição: API para Text-to-Speech (TTS) usando Kokoro.

import os
import re
import uuid
import soundfile as sf
from pydub import AudioSegment
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from kokoro_onnx import Kokoro 

print("=== INICIANDO API TTS - KOKORO ===")

app = FastAPI()

# --- Inicialização do motor Kokoro ---
try:
    print("Inicializando Kokoro...")
    # Os arquivos de modelo são carregados do WORKDIR do contêiner
    kokoro = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
    print("Kokoro inicializado com sucesso!")
except Exception as e:
    print(f"ERRO ao inicializar Kokoro: {e}")
    raise RuntimeError(
        f"Erro ao inicializar o Kokoro. Verifique se os arquivos de modelo foram copiados corretamente. Erro: {e}"
    )

class TTSRequest(BaseModel):
    text: str
    voice: str = "pm_santa"
    speed: float = 1.0
    lang: str = "pt-br"

def split_text(text, max_length=400):
    """Divide o texto em chunks menores para processamento"""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""
    for s in sentences:
        if len(current) + len(s) < max_length:
            current += (" " if current else "") + s
        else:
            if current:
                chunks.append(current.strip())
            current = s
    if current:
        chunks.append(current.strip())
    return chunks

def safe_remove(filepath):
    """Remove arquivo de forma segura, ignorando erros"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"Arquivo removido: {filepath}")
    except Exception as e:
        print(f"Erro ao remover {filepath}: {e}")

@app.post("/synthesize")
def synthesize(request: TTSRequest, background_tasks: BackgroundTasks):
    temp_files = []
    final_filename = None
    
    try:
        print(f"Recebida requisição: {request.text[:50]}...")
        
        sentences = split_text(request.text)
        audio_segments = []

        for i, sentence in enumerate(sentences):
            if not sentence.strip():
                continue
            
            try:
                samples, sample_rate = kokoro.create(
                    sentence,
                    voice=request.voice,
                    speed=request.speed,
                    lang=request.lang
                )
            except Exception as lang_error:
                if "not supported by the espeak backend" in str(lang_error):
                    print(f"Idioma {request.lang} não suportado, usando 'pt-br'...")
                    samples, sample_rate = kokoro.create(
                        sentence,
                        voice=request.voice,
                        speed=request.speed,
                        lang="pt-br"
                    )
                else:
                    raise lang_error

            temp_filename = f"temp_{uuid.uuid4()}.wav"
            sf.write(temp_filename, samples, sample_rate)
            temp_files.append(temp_filename)
            
            audio_segments.append(AudioSegment.from_wav(temp_filename))

        if not audio_segments:
            raise HTTPException(status_code=400, detail="Texto vazio ou inválido.")
            
        combined_audio = AudioSegment.empty()
        for seg in audio_segments:
            combined_audio += seg

        final_filename = f"output_{uuid.uuid4()}.mp3"
        combined_audio.export(final_filename, format="mp3")
        
        print(f"Áudio gerado com sucesso: {final_filename}")

        for f in temp_files:
            background_tasks.add_task(safe_remove, f)
        
        return FileResponse(
            path=final_filename,
            media_type="audio/mpeg", 
            filename=final_filename 
        )
        
    except Exception as e:
        print(f"Erro no endpoint /synthesize: {e}")
        raise HTTPException(status_code=500, detail=f"Erro de Síntese: {str(e)}")

@app.get("/")
def read_root():
    return {"message": "API TTS está funcionando!", "status": "ok"}
