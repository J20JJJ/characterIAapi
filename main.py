from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import os
import io
import base64
import pygame
from PyCharacterAI import get_client
from PyCharacterAI.exceptions import SessionClosedError, ActionError

app = FastAPI()

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo de entrada
class MensajeEntrada(BaseModel):
    User_Token: str
    Character_ID: str
    mensaje: str
    Voz: str

@app.post("/enviar")
async def enviar_mensaje(datos: MensajeEntrada):
    TOKEN = datos.User_Token
    CHARACTER_ID = datos.Character_ID
    voice_id = None
    buffer_audio = None
    texto_respuesta = ""
    author_name = ""

    try:
        client = await get_client(token=TOKEN)
        me = await client.account.fetch_me()
        print(f"✅ Autenticado como @{me.username}")

        chat, greeting = await client.chat.create_chat(CHARACTER_ID)
        author_name = greeting.author_name

        if datos.Voz.lower() == "si":
            voces = await client.utils.search_voices("Megumin")
            for v in voces:
                if v.name.strip().lower() == "megumin":
                    voice_id = v.voice_id
                    break

            try:
                # pygame.mixer.init()
                print("🔊 pygame.mixer iniciado. Ahora se reproducirá el audio en lugar de guardarlo.")
            except Exception as e:
                return {"error": f"No se pudo inicializar pygame: {e}"}

        # Enviar mensaje y obtener respuesta
        respuesta = await client.chat.send_message(
            CHARACTER_ID,
            chat.chat_id,
            datos.mensaje,
            streaming=False
        )
        texto_respuesta = respuesta.get_primary_candidate().text

        if datos.Voz.lower() == "si":
            chat_id = chat.chat_id
            turn_id = respuesta.turn_id
            candidate_id = respuesta.get_primary_candidate().candidate_id

            try:
                audio_bytes = await client.utils.generate_speech(
                    chat_id,
                    turn_id,
                    candidate_id,
                    voice_id
                )

                buffer_audio = io.BytesIO(audio_bytes)
                # pygame.mixer.music.load(buffer_audio, "mp3")
                # pygame.mixer.music.play()
                # while pygame.mixer.music.get_busy():
                #     await asyncio.sleep(0.1)
                # pygame.mixer.quit()

                audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            except ActionError as e:
                print(f"❌ No se pudo generar el audio: {e}")
                audio_base64 = None
        else:
            audio_base64 = None

        await client.close_session()

        return {
            "audio_base64": audio_base64,
            "author": author_name,
            "text": texto_respuesta
        }

    except Exception as e:
        return {"error": str(e)}
