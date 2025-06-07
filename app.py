import os
import base64
import asyncio
from typing import Optional

from flask import Flask, request, jsonify, abort
from flask_cors import CORS
from PyCharacterAI import get_client
from PyCharacterAI.exceptions import SessionClosedError, ActionError

# --- Inicializa Flask + CORS global -------------------
app = Flask(__name__)
# Esto añade Access-Control-Allow-Origin: * (y el resto) en todas las rutas
CORS(app)
# -------------------------------------------------------

# Nombre del personaje (override con CHARACTER_AI_NAME env var)
CHARACTER_NAME = os.getenv("CHARACTER_AI_NAME", "Megumin")


class AuthenticationError(Exception):
    """Para distinguir errores de token vs. otros errores."""
    pass


async def _chat_flow(token: str, character_id: str, mensaje: str, use_voice: bool):
    """Flujo async: autenticación, chat, TTS."""
    try:
        client = await get_client(token=token)
    except Exception as e:
        raise AuthenticationError(f"Authentication failed: {e}")

    try:
        chat, _ = await client.chat.create_chat(character_id)
        respuesta = await client.chat.send_message(
            character_id,
            chat.chat_id,
            mensaje,
            streaming=False
        )
        primary = respuesta.get_primary_candidate()
        text = primary.text
        author = respuesta.author_name

        audio_b64: Optional[str] = None
        if use_voice:
            voces = await client.utils.search_voices(CHARACTER_NAME)
            print("Voces encontradas:", [v.name for v in voces])  # debug

            voice_id = next(
                (v.voice_id for v in voces
                 if v.name.strip().lower() == CHARACTER_NAME.strip().lower()),
                None
            ) or (voces[0].voice_id if voces else None)

            if voice_id:
                try:
                    audio_bytes = await client.utils.generate_speech(
                        chat.chat_id,
                        respuesta.turn_id,
                        primary.candidate_id,
                        voice_id
                    )
                    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                except ActionError as e:
                    print("TTS error:", e)
                    audio_b64 = None

        return {"author": author, "text": text, "audio_base64": audio_b64}

    except SessionClosedError:
        raise
    finally:
        await client.close_session()


@app.route("/chat", methods=["OPTIONS", "POST"])
def chat_api():
    # Responde al preflight automáticamente y con headers CORS
    if request.method == "OPTIONS":
        return ("", 200)

    data = request.get_json(force=True)
    for field in ("User_Token", "Character_ID", "mensaje", "Voz"):
        if field not in data:
            abort(400, description=f"Missing field: {field}")

    token = data["User_Token"]
    character_id = data["Character_ID"]
    mensaje = data["mensaje"]
    use_voice = data["Voz"].strip().lower() == "si"

    try:
        result = asyncio.run(_chat_flow(token, character_id, mensaje, use_voice))
    except AuthenticationError as e:
        abort(401, description=str(e))
    except SessionClosedError:
        abort(500, description="Session was closed unexpectedly.")
    except Exception as e:
        abort(500, description=str(e))

    return jsonify(result), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    # En desarrollo podrías poner debug=True
    app.run(host="0.0.0.0", port=port)
