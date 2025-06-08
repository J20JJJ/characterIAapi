from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import os
import io
import base64
from PyCharacterAI import get_client
from PyCharacterAI.exceptions import ActionError, ChatNotFoundError

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
    Voz: str = "no"
    chat_id: str = None

@app.post("/enviar")
async def enviar_mensaje(datos: MensajeEntrada):
    TOKEN = datos.User_Token
    CHARACTER_ID = datos.Character_ID
    voice_id = None
    audio_base64 = None

    try:
        client = await get_client(token=TOKEN)
        me = await client.account.fetch_me()

        # Cargar o crear chat
        chat_id = datos.chat_id
        greeting = None
        if chat_id:
            try:
                await client.chat.fetch_chat(chat_id)  # Verificar si el chat_id es válido
            except ChatNotFoundError:
                await client.close_session()
                return {"error": "Chat_id no valido"}
        else:
            chat, greeting = await client.chat.create_chat(CHARACTER_ID)
            chat_id = chat.chat_id

        # Buscar voz si se solicita
        if datos.Voz.lower() == "si":
            voces = await client.utils.search_voices("Megumin")
            for v in voces:
                if v.name.strip().lower() == "megumin":
                    voice_id = v.voice_id
                    break

        # Enviar mensaje y obtener respuesta
        respuesta = await client.chat.send_message(
            CHARACTER_ID,
            chat_id,
            datos.mensaje,
            streaming=False
        )

        texto_respuesta = respuesta.get_primary_candidate().text
        author_name = respuesta.author_name

        # Generar audio si se solicita
        if datos.Voz.lower() == "si" and voice_id:
            try:
                audio_bytes = await client.utils.generate_speech(
                    chat_id,
                    respuesta.turn_id,
                    respuesta.get_primary_candidate().candidate_id,
                    voice_id
                )
                audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            except ActionError:
                audio_base64 = None

        await client.close_session()

        return {
            "chat_id": chat_id,
            "audio_base64": audio_base64,
            "author": author_name,
            "text": texto_respuesta
        }

    except Exception as e:
        return {"error": str(e)}
