import os
import time
import datetime
import subprocess  # Para obtener la duración del audio
import google.generativeai as genai
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

load_dotenv()

# Configuración de la API y Modelo
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('models/gemini-flash-latest')

VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH")
MONITOR_DIR = os.path.join(VAULT_PATH, "00_INBOX", "Audio_Captures", "raw")

# --- NUEVAS FUNCIONES PARA EL MANEJO DEL BAÚL ---

def obtener_duracion(file_path):
    """Obtiene la duración del audio usando ffprobe"""
    try:
        comando = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', file_path
        ]
        segundos = float(subprocess.check_output(comando).decode('utf-8').strip())
        minutos = int(segundos // 60)
        segundos_restantes = int(segundos % 60)
        return f"{minutos}m {segundos_restantes}s"
    except:
        return "Duración desconocida"


def leer_prompt_externo():
    """Lee las instrucciones desde el archivo prompt_crianza.txt"""
    ruta_prompt = os.path.join(os.path.dirname(__file__), "..", "config", "prompt_crianza.txt")
    try:
        with open(ruta_prompt, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Actúa como un experto en crianza. Transcribe y analiza este audio."

def obtener_conocimientos_disponibles(vault_path):
    """Escanea las carpetas de pilares para listar las notas de teoría disponibles"""
    # Basado en tu estructura: Desarrollo, Disciplina y Conexión [cite: 1]
    carpetas_pilar = ["20_PILAR_Desarrollo", "30_PILAR_Disciplina", "40_PILAR_Conexión"]
    indices = []
    
    for pilar in carpetas_pilar:
        ruta = os.path.join(vault_path, pilar)
        if os.path.exists(ruta):
            for raiz, dirs, archivos in os.walk(ruta):
                for archivo in archivos:
                    if archivo.endswith(".md"):
                        # Guardamos el nombre sin .md para que Gemini cree el enlace [[Nota]] 
                        indices.append(archivo.replace(".md", ""))
    return indices

# --- CLASE DE MANEJO DE EVENTOS ---

class AudioHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(('.webm', '.mp3', '.m4a', '.ogg')):
            print(f"\n🔔 Detectado: {os.path.basename(event.src_path)}")
            time.sleep(2)
            # Pasamos la duración al procesador
            duracion = obtener_duracion(event.src_path)
            self.process_with_gemini(event.src_path, duracion)

    def process_with_gemini(self, file_path, duracion):
        try:
            print(f"🧠 Gemini analizando ({duracion})...")
            sample_file = genai.upload_file(path=file_path)
            while sample_file.state.name == "PROCESSING":
                time.sleep(1)
                sample_file = genai.get_file(sample_file.name)

            instrucciones = leer_prompt_externo()
            notas_baul = obtener_conocimientos_disponibles(VAULT_PATH)
            
            # Ajuste en el prompt para el formato de enlaces [[archivo|nombre]]
            prompt_final = f"""
            {instrucciones}

            INSTRUCCIÓN DE FORMATO DE ENLACES:
            Cuando menciones conceptos de mi baúl, usa SIEMPRE este formato: [[Nombre del Archivo|Nombre Legible]].
            Por ejemplo, si la nota se llama "32.01_Berrinches (Desregulación)", escribe: [[32.01_Berrinches (Desregulación)|Berrinches]].
            
            LISTA DE NOTAS DISPONIBLES:
            {", ".join(notas_baul)}
            """

            response = model.generate_content([prompt_final, sample_file])
            self.update_obsidian(response.text, duracion)
            
            base_audio_path = os.path.dirname(MONITOR_DIR)
            processed_dir = os.path.join(base_audio_path, "processed")

            os.makedirs(processed_dir, exist_ok=True)
            os.rename(file_path, os.path.join(processed_dir, os.path.basename(file_path)))
            print(f"✅ Procesado con éxito y movido de /raw a /processed.")
            
        except Exception as e:
            print(f"❌ Error: {e}")

    def update_obsidian(self, content, duracion):
        hoy = datetime.date.today()
        mes_carpeta = f"{hoy.month:02}_{hoy.strftime('%B')}"
        ruta_carpeta = os.path.join(VAULT_PATH, "60_REGISTROS_DIARIOS", str(hoy.year), mes_carpeta)
        ruta_archivo = os.path.join(ruta_carpeta, f"{hoy.strftime('%Y-%m-%d')}.md")
        
        os.makedirs(ruta_carpeta, exist_ok=True)

        # Leer el contenido actual para contar notas
        numero_nota = 1
        if os.path.exists(ruta_archivo):
            with open(ruta_archivo, "r", encoding="utf-8") as f:
                texto_actual = f.read()
                # Contamos cuántas veces aparece el encabezado de nota de voz
                numero_nota = texto_actual.count("# 🎙️ Nota de Voz") + 1
        
        modo = "a" if os.path.exists(ruta_archivo) else "w"
        with open(ruta_archivo, modo, encoding="utf-8") as f:
            if modo == "w":
                f.write(f"---\ntags:\n  - Crianza/Diario\n---\n# Registro {hoy}\n")
            # Incluye el numero de nota
            f.write(f"\n\n# 🎙️ Nota de Voz #{numero_nota} ({duracion})\n")
            f.write(content)
        print(f"📝 Nota actualizada con duración: {duracion}")

if __name__ == "__main__":
    handler = AudioHandler()
    
    if os.path.exists(MONITOR_DIR):
        print(f"🔍 Revisando archivos existentes en {MONITOR_DIR}...")
    for f in os.listdir(MONITOR_DIR):
        if f.endswith(('.webm', '.mp3', '.m4a', '.ogg')):
            full_path = os.path.join(MONITOR_DIR, f)
            dur_existente = obtener_duracion(full_path)
            handler.process_with_gemini(full_path, dur_existente)

    observer = Observer()
    observer.schedule(handler, MONITOR_DIR, recursive=False)
    print(f"🚀 Vigilante activo en {MONITOR_DIR}...")
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()