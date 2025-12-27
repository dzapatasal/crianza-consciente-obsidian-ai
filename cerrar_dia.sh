#!/bin/bash
# Obtener la ruta del baúl desde el archivo .env
export $(grep -v '^#' .env | xargs)
RAW_DIR="$OBSIDIAN_VAULT_PATH/00_INBOX/Audio_Captures/raw"

# Crear el archivo disparador
touch "$RAW_DIR/CERRAR_DIA.txt"

echo "🚀 Señal de cierre enviada. Procesando audios del día..."