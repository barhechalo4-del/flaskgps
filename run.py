from pyngrok import ngrok
from app import app

public_url = ngrok.connect(5000, "http")
print("PUBLIC LINK:", public_url)

app.run(host="0.0.0.0", port=5000)