## 🛠️ Guía de Ejecución (Paso a Paso)

### 1. Preparar el Entorno

Abre tu terminal y asegúrate de estar en la carpeta raíz del proyecto.

```bash
cd /home/degops/Projects/Repositorios/repo_crianza_auto/root/
source venv/bin/activate

```

* **Nota:** Sabrás que está activo porque verás `(venv)` al inicio de tu línea de comandos.

### 2. Encender el "Ojo" del Sistema (Vigilancia)

Ejecuta el script que se queda esperando los audios y la señal de cierre.

```bash
python3 src/crianza_watcher.py

```

* **Qué esperar:** La terminal se quedará "bloqueada" mostrando el mensaje: `🚀 Vigilante de BATCH activo ... Crea 'CERRAR_DIA.txt' en /raw para cerrar el día.`. </br>
**>> No cierres esta ventana !!**



### 3. Cargar tus Audios

Mueve o copia todos los audios que grabaste durante el día a la carpeta de entrada:
`baby/00_INBOX/Audio_Captures/raw/`

### 4. Disparar el Procesamiento (El Botón)

Abre una **nueva pestaña o ventana** de la terminal (porque la primera está ocupada vigilando) y ejecuta:

```bash
cd /home/degops/Projects/Repositorios/repo_crianza_auto/root/
./cerrar_dia.sh

```

* 
**Qué pasará:** Este comando creará el archivo `CERRAR_DIA.txt`.


* 
**En la primera terminal:** </br>
Verás que el script despierta, sube los audios a Gemini, calcula la edad de Bruno usando `perfil_bruno.txt` y redacta la nota vinculando tus pilares como el de **Disciplina** o **Conexión**.



### 5. Verificar en Obsidian

Ve a tu carpeta `60_REGISTROS_DIARIOS`. Verás una nota nueva (o actualizada) con:

* La edad exacta calculada.
* La línea de tiempo de tus audios.
* Las menciones a los acuerdos de **Mónica** de la nota `43.03`.



---

### Sugerencia Adicional

Si al ejecutar `./cerrar_dia.sh` te dice "Permiso denegado", ejecuta esto una sola vez:
```bash
chmod +x cerrar_dia.sh
```