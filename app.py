from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class MensajeEntrada(BaseModel):
    User_Token: str
    Character_ID: str
    mensaje: str
    Voz: str

@app.post("/enviar")
async def enviar_mensaje(datos: MensajeEntrada):
    return {
        "audio_base64": "audioo",
        "author": "Megumin",
        "text": "¡Hola!"
    }
