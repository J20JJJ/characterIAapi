import os
import io
import asyncio
import pygame
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from PyCharacterAI import get_client
from PyCharacterAI.exceptions import SessionClosedError, ActionError

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambia esto en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MensajeEntrada(BaseModel):
    User_Token: str
    Character_ID: str
    mensaje: str
    Voz: str  # "Si" para usar voz personalizada, cualquier otra cosa para omitir

# Inicializar pygame mixer solo una vez
pygame.mixer.init()

@app.post("/hablar")
async def hablar(data: MensajeEntrada):
    try:
        client = await get_client(token=data.User_Token, web_next_auth=None)
        me = await client.account.fetch_me()
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"No se pudo autenticar: {str(e)}")

    # Buscar voz si se solicitó
    voice_id = None
    if data.Voz.lower() == "si":
        voces = await client.utils.search_voices("Megumin")
        for v in voces:
            if v.name.strip().lower() == "megumin":
                voice_id = v.voice_id
                break

    try:
        chat, greeting = await client.chat.create_chat(data.Character_ID)

        respuesta = await client.chat.send_message(
            data.Character_ID,
            chat.chat_id,
            data.mensaje,
            streaming=False
        )
        texto_respuesta = respuesta.get_primary_candidate().text

        # Extraer datos para síntesis de voz
        chat_id = chat.chat_id
        turn_id = respuesta.turn_id
        candidate_id = respuesta.get_primary_candidate().candidate_id

        # Intentar generar audio
        try:
            audio_bytes = await client.utils.generate_speech(
                chat_id,
                turn_id,
                candidate_id,
                voice_id
            )
        except ActionError as e:
            raise HTTPException(status_code=500, detail=f"No se pudo generar audio: {e}")

        # Devolver el audio como MP3 para el navegador
        audio_stream = io.BytesIO(audio_bytes)
        headers = {
            "Content-Disposition": "inline; filename=respuesta.mp3"
        }
        return StreamingResponse(audio_stream, media_type="audio/mpeg", headers=headers)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close_session()
