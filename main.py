import base64
import io
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PyCharacterAI import get_client
from PyCharacterAI.exceptions import ActionError, SessionClosedError

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
    Voz: str  # "Si" o "No"

# Ruta POST principal
@app.post("/enviar")
async def enviar_mensaje(datos: MensajeEntrada):
    try:
        client = await get_client(token=datos.User_Token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"No se pudo autenticar: {e}")

    try:
        await client.account.fetch_me()

        voice_id = None
        if datos.Voz.lower() == "si":
            voces = await client.utils.search_voices("Megumin")
            for v in voces:
                if v.name.strip().lower() == "megumin":
                    voice_id = v.voice_id
                    break

        chat, greeting = await client.chat.create_chat(datos.Character_ID)

        respuesta = await client.chat.send_message(
            datos.Character_ID,
            chat.chat_id,
            datos.mensaje,
            streaming=False
        )
        texto_respuesta = respuesta.get_primary_candidate().text
        personaje_nombre = respuesta.author_name

        audio_base64 = None
        if datos.Voz.lower() == "si":
            try:
                audio_bytes = await client.utils.generate_speech(
                    chat.chat_id,
                    respuesta.turn_id,
                    respuesta.get_primary_candidate().candidate_id,
                    voice_id
                )
                audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            except ActionError:
                audio_base64 = None  # Si no hay audio disponible

        await client.close_session()

        return {
            "audio_base64": audio_base64,
            "author": personaje_nombre,
            "text": texto_respuesta
        }

    except SessionClosedError:
        raise HTTPException(status_code=400, detail="Sesión cerrada inesperadamente")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el chat: {e}")
