![Unofficial CharacterAI API](./assets/unofficial-characterai-api.png)

¡Interactúa con personajes de **Character.AI** mediante una API no oficial sencilla que además convierte las respuestas en voz!
🎙️ Ideal para integraciones con bots, asistentes virtuales o apps interactivas.

---

🚀 Proyecto desplegado en Koyeb

Este proyecto está publicado y funcionando en Koyeb, permitiendo alta disponibilidad con despliegues rápidos y simples desde GitHub.

 - ⚠️ Importante:

    Está desplegado usando una cuenta gratuita de Koyeb, lo que significa que:
    
    La API puede entrar en modo sleep/inactividad si no se usa por un tiempo.
    
    Existe un límite de uso mensual y concurrencia.
    
    Es posible que ocasionalmente esté temporalmente caída o más lenta.
  
 ### Puedes hacer peticiones directamente si tienes tu token de usuario y el ID del personaje.
---

## 📦 Características

* ✉️ Envío de mensajes a personajes de Character.AI
* 🔊 Respuesta en **voz generada por IA**
* 🔄 Reutilización de chats mediante `chat_id`
* 🎯 Búsqueda de la voz más parecida al personaje automáticamente
* 🌍 CORS habilitado para uso desde frontend

---

## 🛠️ Cómo usar la API

### 1. **Enviar mensaje al personaje**

```http
POST /enviar
```

#### Body JSON:

```json
{
  "User_Token": "tu_token",
  "Character_ID": "ID_del_personaje",
  "mensaje": "Hola, ¿cómo estás?",
  "Voz": "si",
  "Chat_ID": null
}
```

#### Respuesta:

```json
{
  "chat_id": "abc123...",
  "audio_base64": "c29tZWJhc2U2NGRhdGE=",
  "author": "Nombre del personaje",
  "text": "¡Hola! Estoy bien, gracias por preguntar."
}
```

> 🎧 Puedes decodificar `audio_base64` para reproducir la voz directamente en el navegador.

---

### 2. **Obtener historial del chat**

```http
GET /chat/{chat_id}?token=tu_token
```

#### Ejemplo de respuesta:

```json
[
  {"author": "Tú", "message": "Hola"},
  {"author": "AI", "message": "¡Hola! ¿En qué te puedo ayudar hoy?"}
]
```

---

## 🖼️ Ejemplo visual (Frontend personalizado)

> Puedes conectarlo a cualquier frontend: React, Vue, vanilla JS, etc.

---

## 🔐 Necesitas...

* Un token de usuario de [Character.AI](https://character.ai/)
* El `ID` del personaje con el que quieres hablar (puedes obtenerlo desde el link del personaje)

---

## 🧪 Ejemplo de uso con `curl`

```bash
curl -X POST https://tudominio.koyeb.app/enviar \
  -H "Content-Type: application/json" \
  -d '{
    "User_Token": "YOUR_TOKEN",
    "Character_ID": "CHARACTER_ID",
    "mensaje": "Hola!",
    "Voz": "si"
  }'
```

---

## 🧰 Tecnologías usadas

* FastAPI ⚡
* PyCharacterAI 🧠
* httpx 🌐
* Koyeb 🚀 (despliegue serverless gratuito)
* Difflib (para mejorar coincidencias de voz)

---

## 📌 Notas

* Esta API **no almacena datos**, pero puedes extenderla fácilmente con una base de datos.
* Si el personaje no tiene voz, el sistema intenta encontrar la más parecida.
* El audio se retorna en formato base64. Puedes usarlo directamente en HTML5 con `<audio>`.

---

## 🤝 Contribuye

¿Ideas? ¿Mejoras? ¡Haz un fork o abre un issue!

---

¿Te gustaría que te lo devuelva en archivo `.md` también?
