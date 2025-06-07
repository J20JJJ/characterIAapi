from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import io
import base64
import asyncio
from PyCharacterAI import get_client
from PyCharacterAI.exceptions import SessionClosedError, ActionError
import uvicorn

app = FastAPI()

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

    # Authenticate
    try:
        client = await get_client(token=token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")

    try:
        # Create or fetch chat
        chat, _ = await client.chat.create_chat(character_id)
        # Send message
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
            # Generate speech
            try:
                audio_bytes = await client.utils.generate_speech(
                    chat.chat_id,
                    respuesta.turn_id,
                    primary.candidate_id,
                    None  # default voice
                )
                audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            except ActionError:
                # Log the failure and continue returning text-only response
                audio_b64 = None

        return ChatResponse(author=author, text=text, audio_base64=audio_b64)

    except SessionClosedError:
        raise HTTPException(status_code=500, detail="Session was closed unexpectedly.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await client.close_session()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
