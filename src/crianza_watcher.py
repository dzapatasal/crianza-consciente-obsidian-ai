import os
import time
import datetime
import subprocess
import google.generativeai as genai
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('models/gemini-flash-latest')

VAULT_PATH = os.getenv("OBSIDIAN_VAULT_PATH")
MONITOR_DIR = os.path.join(VAULT_PATH, "00_INBOX", "Audio_Captures", "raw")
TRIGGER_FILE = "CERRAR_DIA.txt" # El "Botón" de cierre 

def obtener_duracion(file_path):
    try:
        comando = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
        segundos = float(subprocess.check_output(comando).decode('utf-8').strip())
        return f"{int(segundos // 60)}m {int(segundos % 60)}s"
    except: return "Desconocida"

def leer_prompt_externo():
    ruta_prompt = os.path.join(os.path.dirname(__file__), "..", "config", "prompt_crianza.txt")
    try:
        with open(ruta_prompt, "r", encoding="utf-8") as f: return f.read()
    except FileNotFoundError: return "Analiza estos audios de crianza."

def obtener_conocimientos_disponibles(vault_path):
    carpetas_pilar = ["20_PILAR_Desarrollo", "30_PILAR_Disciplina", "40_PILAR_Conexión"]
    indices = []
    for pilar in carpetas_pilar:
        ruta = os.path.join(vault_path, pilar)
        if os.path.exists(ruta):
            for raiz, _, archivos in os.walk(ruta):
                for archivo in archivos:
                    if archivo.endswith(".md"): indices.append(archivo.replace(".md", ""))
    return indices

class BatchAudioHandler(FileSystemEventHandler):
    def on_created(self, event):
        # Si se crea el archivo disparador, procesamos todo el lote
        if os.path.basename(event.src_path) == TRIGGER_FILE:
            print(f"\n🚀 ¡Señal de Cierre Recibida! Iniciando procesamiento por lotes...")
            self.process_batch()

    def process_batch(self):
        audios = [os.path.join(MONITOR_DIR, f) for f in os.listdir(MONITOR_DIR) 
                  if f.endswith(('.webm', '.mp3', '.m4a', '.ogg'))]
        
        if not audios:
            print("⚠️ No hay audios acumulados para procesar.")
            os.remove(os.path.join(MONITOR_DIR, TRIGGER_FILE))
            return

        print(f"📦 Procesando {len(audios)} audios acumulados...")
        try:
            # Subir todos los archivos a Gemini
            uploaded_files = []
            resumen_metadatos = ""
            for path in sorted(audios): # Ordenados por nombre/tiempo
                dur = obtener_duracion(path)
                f_gemini = genai.upload_file(path=path)
                uploaded_files.append(f_gemini)
                resumen_metadatos += f"- Audio: {os.path.basename(path)} | Duración: {dur}\n"

            # Esperar procesamiento
            for f in uploaded_files:
                while f.state.name == "PROCESSING":
                    time.sleep(1)
                    f = genai.get_file(f.name)

            instrucciones = leer_prompt_externo()
            notas_baul = obtener_conocimientos_disponibles(VAULT_PATH)
            
            # Nuevo Prompt para LÍNEA DE TIEMPO y BATCH 
            prompt_final = f"""
            {instrucciones}

            INSTRUCCIONES DE LOTE:
            He subido {len(audios)} audios. Tu tarea es:
            1. Crear una LÍNEA DE TIEMPO cronológica resumiendo cada evento brevemente.
            2. Realizar un ANÁLISIS GLOBAL detectando patrones conductuales en el conjunto.
            3. Vincular con mi baúl usando [[Archivo|Nombre]].

            METADATOS DE ARCHIVOS:
            {resumen_metadatos}

            LISTA DE NOTAS DISPONIBLES EN MI BAÚL:
            {", ".join(notas_baul)}
            """

            response = model.generate_content([prompt_final] + uploaded_files)
            self.save_to_obsidian(response.text, len(audios))
            
            # Limpiar: Mover audios a processed y borrar trigger
            processed_dir = os.path.join(os.path.dirname(MONITOR_DIR), "processed")
            os.makedirs(processed_dir, exist_ok=True)
            for path in audios:
                os.rename(path, os.path.join(processed_dir, os.path.basename(path)))
            os.remove(os.path.join(MONITOR_DIR, TRIGGER_FILE))
            
            print(f"✅ Jornada cerrada con {len(audios)} eventos registrados.")

        except Exception as e:
            print(f"❌ Error en batch: {e}")

    def save_to_obsidian(self, content, total_audios):
        hoy = datetime.date.today()
        ruta_carpeta = os.path.join(VAULT_PATH, "60_REGISTROS_DIARIOS", str(hoy.year), f"{hoy.month:02}_{hoy.strftime('%B')}")
        ruta_archivo = os.path.join(ruta_carpeta, f"{hoy.strftime('%Y-%m-%d')}.md")
        os.makedirs(ruta_carpeta, exist_ok=True)

        modo = "a" if os.path.exists(ruta_archivo) else "w"
        with open(ruta_archivo, modo, encoding="utf-8") as f:
            if modo == "w":
                f.write(f"---\ntags:\n  - Crianza/Diario\n---\n# Registro {hoy}\n")
            f.write(f"\n\n## 🗓️ Resumen de Jornada ({total_audios} interacciones)\n")
            f.write(content)

if __name__ == "__main__":
    observer = Observer()
    observer.schedule(BatchAudioHandler(), MONITOR_DIR, recursive=False)
    print(f"🚀 Vigilante de BATCH activo. Crea '{TRIGGER_FILE}' en /raw para cerrar el día.")
    observer.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()