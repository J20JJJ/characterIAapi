import asyncio
import base64
import os
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from PyCharacterAI import get_client
from PyCharacterAI.exceptions import SessionClosedError, ActionError

app = FastAPI()

# 👉 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 👉 Modelo de entrada
class MensajeEntrada(BaseModel):
    User_Token: str
    Character_ID: str
    mensaje: str
    Voz: str = "Megumin"  # Valor por defecto

@app.post("/enviar")
async def enviar_mensaje(datos: MensajeEntrada):
    try:
        client = await get_client(token=datos.User_Token)
    except Exception as e:
        return {"error": f"No se pudo autenticar: {str(e)}"}

    try:
        me = await client.account.fetch_me()
    except Exception as e:
        await client.close_session()
        return {"error": f"Error al obtener el usuario: {str(e)}"}

    # 👉 Obtener voz
    voice_id = None
    try:
        voces = await client.utils.search_voices(datos.Voz)
        for v in voces:
            if v.name.strip().lower() == datos.Voz.strip().lower():
                voice_id = v.voice_id
                break
    except Exception as e:
        await client.close_session()
        return {"error": f"Error al buscar voz: {str(e)}"}

    try:
        chat, _ = await client.chat.create_chat(datos.Character_ID)
        respuesta = await client.chat.send_message(
            datos.Character_ID,
            chat.chat_id,
            datos.mensaje,
            streaming=False
        )

        texto_respuesta = respuesta.get_primary_candidate().text
        author = respuesta.author_name

        # Extraer IDs necesarios para generar el audio
        chat_id = chat.chat_id
        turn_id = respuesta.turn_id
        candidate_id = respuesta.get_primary_candidate().candidate_id

        # 👉 Intentar generar el audio con y sin voice_id
        try:
            if voice_id:
                audio_bytes = await client.utils.generate_speech(
                    chat_id, turn_id, candidate_id, voice_id
                )
            else:
                # Intentar sin voice_id directamente
                audio_bytes = await client.utils.generate_speech(
                    chat_id, turn_id, candidate_id
                )
        except ActionError:
            try:
                # Fallback: intentar sin voice_id si falló el anterior
                audio_bytes = await client.utils.generate_speech(
                    chat_id, turn_id, candidate_id
                )
            except ActionError as e:
                await client.close_session()
                return {"error": f"No se pudo generar el audio con o sin voz: {str(e)}"}

        if not audio_bytes:
            await client.close_session()
            return {"error": "El audio generado está vacío."}

        # Codificar el audio a base64
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        await client.close_session()
        return {
            "audio_base64": audio_base64,
            "author": author,
            "text": texto_respuesta,
            "audio_length": len(audio_bytes)
        }

    except SessionClosedError:
        return {"error": "Sesión cerrada"}
    except Exception as e:
        return {"error": f"Error inesperado: {str(e)}"}
    finally:
        await client.close_session()
