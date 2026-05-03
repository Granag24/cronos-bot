import os
import requests
import pandas as pd
import threading
import time
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- CONFIGURACIÓN ---
# Si no usas variables de entorno en Render, pon tu token aquí:
TOKEN = "8679146706:AAHruVmgXuvjubnUEpzMEAr8m7zYR3Agkz8"

TEAMS = {
    "arsenal": {"id": "18bb2c1a", "name": "Arsenal"},
    "barcelona": {"id": "206d90db", "name": "Barcelona"},
    "real madrid": {"id": "53a2f082", "name": "Real-Madrid"},
    "manchester city": {"id": "b8fd0353", "name": "Manchester-City"},
    "liverpool": {"id": "822bd0ba", "name": "Liverpool"},
    "bayern munich": {"id": "05439c85", "name": "Bayern-Munich"}
}

def get_fbref_data(team_id, team_name):
    url = f"https://fbref.com/en/squads/{team_id}/{team_name}-Stats"
    
    # DISFRAZ ANTI-BLOQUEO MEJORADO
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://google.com"
    }
    
    try:
        # Pausa aleatoria para no parecer un robot agresivo
        time.sleep(random.uniform(1.5, 3.0))
        
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 429:
            print("FBref nos bloqueó temporalmente (Error 429)")
            return "bloqueo", None
            
        tables = pd.read_html(r.text)
        
        attack = {"gls": 0, "xG": 0, "shots": 0}
        defense = {"save": 70, "ga90": 1.0} 

        for t in tables:
            if isinstance(t.columns, pd.MultiIndex):
                t.columns = t.columns.get_level_values(-1)

            if "Gls" in t.columns and "xG" in t.columns and "Sh" in t.columns:
                attack["gls"] = pd.to_numeric(t["Gls"], errors='coerce').fillna(0).mean()
                attack["xG"] = pd.to_numeric(t["xG"], errors='coerce').fillna(0).mean()
                attack["shots"] = pd.to_numeric(t["Sh"], errors='coerce').fillna(0).mean()

            if "Save%" in t.columns and "GA90" in t.columns:
                defense["save"] = pd.to_numeric(t["Save%"], errors='coerce').fillna(70).mean()
                defense["ga90"] = pd.to_numeric(t["GA90"], errors='coerce').fillna(1).mean()

        atk_score = (attack["xG"] * 0.5) + (attack["gls"] * 0.3) + (attack["shots"] * 0.2)
        def_score = ((1 - (defense["save"]/100)) * 0.5) + (defense["ga90"] * 0.5)
        
        return round(atk_score, 2), round(def_score, 2)
    except Exception as e:
        print(f"Error en scraping: {e}")
        return None, None

def format_msg(team, atk, dfn):
    status_atk = "Ataque FUERTE 🔥" if atk > 2 else "Ataque MEDIO ⚖️"
    status_def = "Defensa SÓLIDA 🧱" if dfn < 1.2 else "Defensa FRÁGIL ⚠️"
    
    return (
        f"⚽ **{team.upper()}**\n\n"
        f"🔥 **Ataque:** `{atk}`\n"
        f"🧱 **Defensa:** `{dfn}`\n\n"
        f"📊 **LECTURA:**\n"
        f"- {status_atk}\n"
        f"- {status_def}"
    )

async def analizar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Escribe el equipo, ej: /analizar barcelona")
        return

    query = " ".join(context.args).lower()
    if query not in TEAMS:
        await update.message.reply_text(f"❌ Equipo '{query}' no está en mi base de datos.")
        return

    await update.message.reply_text(f"⏳ Consultando FBref para {query.capitalize()}...")
    
    t = TEAMS[query]
    atk_score, def_score = get_fbref_data(t["id"], t["name"])

    if atk_score == "bloqueo":
        await update.message.reply_text("⚠️ FBref detectó mucha actividad. Espera 2 minutos e intenta de nuevo.")
        return
    elif atk_score is None:
        await update.message.reply_text("🤯 FBref no respondió. Reintentando en breve...")
        return

    msg = format_msg(t["name"], atk_score, def_score)
    await update.message.reply_text(msg, parse_mode="Markdown")

# --- SERVIDOR FANTASMA PARA RENDER ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Cronos Bot is Alive!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    server.serve_forever()

def main():
    # Servidor web en hilo separado
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    # Iniciar Bot
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("analizar", analizar))
    print("🚀 Cronos Bot Online en Render...")
    app.run_polling()

if __name__ == "__main__":
    main()
