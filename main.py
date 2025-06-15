from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio, httpx, json
import io
import base64
from typing import Optional
from PyCharacterAI import get_client
from PyCharacterAI.exceptions import SessionClosedError, ActionError
import difflib


app = FastAPI(root_path="/api/main")

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
            voice_id = None

            # 1. Primero intentamos coincidencia exacta (como ya lo hacías)
            for v in voces:
                if v.name.strip().lower() == author_name.strip().lower():
                    voice_id = v.voice_id
                    break

            # 2. Si no se encontró, probamos coincidencia parcial (que el nombre esté contenido)
            if not voice_id:
                for v in voces:
                    if author_name.strip().lower() in v.name.strip().lower():
                        voice_id = v.voice_id
                        break

            # 3. Si aún no se encuentra, usamos la voz más parecida con difflib
            if not voice_id and voces:
                nombres_voces = [v.name for v in voces]
                mejor_match = difflib.get_close_matches(author_name, nombres_voces, n=1, cutoff=0.5)
                if mejor_match:
                    for v in voces:
                        if v.name == mejor_match[0]:
                            voice_id = v.voice_id
                            print(f"✅ Voz sugerida por similitud: {v.name}")
                            break

            if not voice_id:
                print(f"⚠️ No se encontró una voz adecuada para {author_name}")

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
    
@app.get("/chat/{chat_id}")
async def get_chat(chat_id: str, token: str):
    url = f"https://neo.character.ai/turns/{chat_id}/"
    headers = {
        "Authorization": f"Token {token}",
        "Accept": "application/json",
        "Origin": "https://character.ai",
        "Referer": "https://character.ai/",
        "User-Agent": "Mozilla/5.0"
    }

    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers)
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)

    data = r.json().get("turns", [])
    result = [{"author": t["author"]["name"], "message": t["candidates"][0]["raw_content"]}
              for t in sorted(data, key=lambda x: x["create_time"]) if t.get("candidates")]

    return JSONResponse(content=result)
