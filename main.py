from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

# Ruta POST
@app.post("/enviar")
async def enviar_mensaje(datos: MensajeEntrada):
    print("User_Token:", datos.User_Token)
    print("Character_ID:", datos.Character_ID)
    print("mensaje:", datos.mensaje)
    print("Voz:", datos.Voz)

    return {
        "audio_base64": "audioo",
        "author": "Megumin",
        "text": "¡Hola!"
    }
