from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 👉 Agregar CORS aquí
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Puedes poner ["http://localhost:5173"] para mayor seguridad
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
