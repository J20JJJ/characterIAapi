from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio, httpx
import io
import base64
from typing import Optional
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
    Chat_ID: Optional[str] = None  # Nuevo campo opcional

async def nombre_personaje(token: str, character_id: str) -> str:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://beta.character.ai/chat/character/info/",
            headers={"Authorization": "Token " + token},
            json={"external_id": "" + character_id}
        )
        print(r.json().get("character", {}).get("name"))
        return r.json().get("character", {}).get("name", "Desconocido")

@app.post("/enviar")
async def enviar_mensaje(datos: MensajeEntrada):
    TOKEN = datos.User_Token
    CHARACTER_ID = datos.Character_ID
    voice_id = None
    buffer_audio = None
    texto_respuesta = ""
    author_name = ""
    chat_id = datos.Chat_ID

    try:
        client = await get_client(token=TOKEN)
        me = await client.account.fetch_me()
        print(f"✅ Autenticado como @{me.username}")

        # Usar chat existente o crear uno nuevo
        if chat_id:
            print(f"🔄 Usando chat existente con ID: {chat_id}")
            chat = await client.chat.fetch_chat(chat_id)
            
            author_name = await nombre_personaje(TOKEN, CHARACTER_ID)

        else:
            chat, greeting = await client.chat.create_chat(CHARACTER_ID)
            chat_id = chat.chat_id
            author_name = greeting.author_name
            print(f"🆕 Chat creado con ID: {chat_id}")

        # Buscar voz si es necesario
        if datos.Voz.lower() == "si":
            voces = await client.utils.search_voices(author_name)
            for v in voces:
                if v.name.strip().lower() == author_name.strip().lower():
                    voice_id = v.voice_id
                    break

        # Enviar mensaje
        respuesta = await client.chat.send_message(
            CHARACTER_ID,
            chat_id,
            datos.mensaje,
            streaming=False
        )
        texto_respuesta = respuesta.get_primary_candidate().text

        # Generar audio si se pidió
        if datos.Voz.lower() == "si":
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
                audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            except ActionError as e:
                print(f"❌ No se pudo generar el audio: {e}")
                audio_base64 = None
        else:
            audio_base64 = None

        await client.close_session()

        return {
            "chat_id": chat_id,  # Importante devolver esto para reusar el chat
            "audio_base64": audio_base64,
            "author": author_name,
            "text": texto_respuesta
        }

    except Exception as e:
        return {"error": str(e)}
