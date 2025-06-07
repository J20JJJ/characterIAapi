import os
import base64
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PyCharacterAI import get_client
from PyCharacterAI.exceptions import SessionClosedError, ActionError
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambia esto en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ------------------------------------------------------

# Nombre del personaje (para buscar voces). Puedes sobreescribir vía ENV: CHARACTER_AI_NAME
CHARACTER_NAME = os.getenv("CHARACTER_AI_NAME", "Megumin")


class ChatRequest(BaseModel):
User_Token: str
Character_ID: str
mensaje: str
Voz: str  # "Si" or "No"


class ChatResponse(BaseModel):
author: str
text: str
audio_base64: Optional[str] = None


@app.post("/chat", response_model=ChatResponse)
async def chat_api(req: ChatRequest):
token = req.User_Token
character_id = req.Character_ID
mensaje = req.mensaje
use_voice = req.Voz.strip().lower() == "si"

# 1) Autenticación
try:
client = await get_client(token=token)
except Exception as e:
raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")

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
# 4) Buscar voces disponibles para este personaje
voces = await client.utils.search_voices(CHARACTER_NAME)
# Para depurar, mira en logs qué voces hay:
print("Voces encontradas:", [v.name for v in voces])

# 5) Seleccionar voice_id (primero intenta match por nombre, si no, la primera)
voice_id = None
for v in voces:
if v.name.strip().lower() == CHARACTER_NAME.strip().lower():
voice_id = v.voice_id
break
if not voice_id and voces:
voice_id = voces[0].voice_id

# 6) Generar audio si tenemos voice_id
if voice_id:
try:
audio_bytes = await client.utils.generate_speech(
chat.chat_id,
respuesta.turn_id,
primary.candidate_id,
voice_id
)
audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
except ActionError as e:
# Si falla, lo imprimimos para depurar y devolvemos solo texto
print("TTS error:", e)
audio_b64 = None

return ChatResponse(author=author, text=text, audio_base64=audio_b64)

except SessionClosedError:
raise HTTPException(status_code=500, detail="Session was closed unexpectedly.")
except Exception as e:
raise HTTPException(status_code=500, detail=str(e))
finally:
await client.close_session()


if __name__ == "__main__":
port = int(os.getenv("PORT", 8000))
uvicorn.run(app, host="0.0.0.0", port=port)
