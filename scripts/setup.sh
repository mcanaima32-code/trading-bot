#!/bin/bash

# Script de configuración automática del Bot de Trading
echo "🤖 Configurando Bot de Trading de Criptomonedas..."

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 no está instalado"
    echo "Instala Python 3.8+ y ejecuta este script nuevamente"
    exit 1
fi

echo "✅ Python encontrado: $(python3 --version)"

# Crear entorno virtual
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
echo "🔧 Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias
echo "📚 Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

# Crear archivo .env si no existe
if [ ! -f ".env" ]; then
    echo "⚙️ Creando archivo de configuración..."
    cp .env.example .env
    echo "✏️ Edita el archivo .env con tus credenciales antes de ejecutar el bot"
fi

# Crear directorio de logs
mkdir -p logs

echo ""
echo "🎉 ¡Configuración completada!"
echo ""
echo "📝 Próximos pasos:"
echo "1. Edita el archivo .env con tus credenciales"
echo "2. Ejecuta: source venv/bin/activate"
echo "3. Ejecuta: python main.py"
echo ""
echo "📖 Lee el README.md para instrucciones detalladas"