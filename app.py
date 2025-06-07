import os
import base64
import asyncio
from typing import Optional

from flask import Flask, request, jsonify, abort
from flask_cors import CORS
from PyCharacterAI import get_client
from PyCharacterAI.exceptions import SessionClosedError, ActionError

# --- Configuración de Flask + CORS --------------------
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
# -------------------------------------------------------

# Nombre del personaje (override con CHARACTER_AI_NAME env var)
CHARACTER_NAME = os.getenv("CHARACTER_AI_NAME", "Megumin")


class AuthenticationError(Exception):
    """Para distinguir errores de token vs. otros errores."""
    pass


async def _chat_flow(token: str, character_id: str, mensaje: str, use_voice: bool):
    """Flujo async: autenticación, chat, TTS."""
    # 1) Autenticación
    try:
        client = await get_client(token=token)
    except Exception as e:
        raise AuthenticationError(f"Authentication failed: {e}")

    try:
        # 2) Crear o recuperar chat
        chat, _ = await client.chat.create_chat(character_id)

        # 3) Enviar mensaje y obtener respuesta
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
            # 4) Buscar voces disponibles
            voces = await client.utils.search_voices(CHARACTER_NAME)
            print("Voces encontradas:", [v.name for v in voces])  # debug

            # 5) Seleccionar voice_id
            voice_id = None
            for v in voces:
                if v.name.strip().lower() == CHARACTER_NAME.strip().lower():
                    voice_id = v.voice_id
                    break
            if not voice_id and voces:
                voice_id = voces[0].voice_id

            # 6) Generar audio
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
        # lo dejamos propagar para que lo capture el caller
        raise
    finally:
        await client.close_session()


@app.route("/chat", methods=["POST"])
def chat_api():
    data = request.get_json(force=True)
    # Validación del body
    for field in ("User_Token", "Character_ID", "mensaje", "Voz"):
        if field not in data:
            abort(400, description=f"Missing field: {field}")

    token = data["User_Token"]
    character_id = data["Character_ID"]
    mensaje = data["mensaje"]
    use_voice = data["Voz"].strip().lower() == "si"

    # Ejecuta el flujo async
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
    # En desarrollo puedes poner debug=True
    app.run(host="0.0.0.0", port=port)
