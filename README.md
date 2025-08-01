# 🤖 Bot de Trading de Criptomonedas

Un bot de trading inteligente controlado por Telegram que utiliza análisis técnico e inteligencia artificial para operar en Binance con el objetivo de obtener un 30% de ganancia semanal.

## ✨ Características

- 🤖 **Control por Telegram**: Controla completamente el bot desde Telegram
- 📊 **Análisis Técnico Automático**: RSI, MACD, Bollinger Bands, medias móviles y más
- 🧠 **Asesoramiento con IA**: Integración con LLMs gratuitos (Groq, Ollama)
- 💰 **Objetivo Ambicioso**: 30% de ganancia semanal con gestión de riesgo
- ⚡ **Trading Automático**: Ejecuta trades basados en señales técnicas y IA
- 🛡️ **Gestión de Riesgo**: Stop-loss, take-profit y límites de exposición
- 📈 **Monitoreo en Tiempo Real**: Seguimiento de posiciones y rendimiento
- 🗄️ **Base de Datos**: Almacena historial de trades y estadísticas

## 🚀 Instalación Rápida

### 1. Clonar el Repositorio
```bash
git clone <repository-url>
cd crypto-trading-bot
```

### 2. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno
```bash
cp .env.example .env
```

Edita el archivo `.env` con tus credenciales:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=tu_token_de_telegram
TELEGRAM_CHAT_ID=tu_chat_id

# Binance API (¡Usa TESTNET para pruebas!)
BINANCE_API_KEY=tu_api_key_de_binance
BINANCE_SECRET_KEY=tu_secret_key_de_binance
BINANCE_TESTNET=True

# LLM (elige uno)
GROQ_API_KEY=tu_api_key_de_groq
```

### 4. Ejecutar el Bot
```bash
python main.py
```

## 🔧 Configuración Detallada

### Telegram Bot

1. Crear bot con [@BotFather](https://t.me/botfather)
2. Obtener el token del bot
3. Obtener tu Chat ID enviando un mensaje al bot y visitando:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```

### Binance API

1. Registrarse en [Binance](https://binance.com)
2. Crear API Key en la configuración de la cuenta
3. **IMPORTANTE**: Usar Binance Testnet para pruebas:
   - [Testnet](https://testnet.binance.vision/)
   - Configurar `BINANCE_TESTNET=True`

### LLMs Gratuitos

#### Groq (Recomendado)
- Registrarse en [Groq](https://console.groq.com)
- Obtener API key gratuita
- Límite: ~6000 tokens/minuto

#### Ollama (Local)
```bash
# Instalar Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Descargar modelo
ollama pull llama2
```

## 📱 Comandos de Telegram

### Comandos Básicos
- `/start` - Iniciar el bot
- `/ayuda` - Ver todos los comandos
- `/status` - Estado del bot y balance
- `/analizar` - Analizar mercado actual

### Trading
- `/comprar BTCUSDT` - Comprar criptomoneda
- `/vender BTCUSDT` - Vender criptomoneda
- `/balance` - Ver balance actual
- `/posiciones` - Ver posiciones abiertas

### Control Automático
- `/activar` - Activar trading automático
- `/desactivar` - Desactivar trading automático

### Palabras Clave
También puedes usar texto natural:
- `comprar btc` - Comprar Bitcoin
- `vender eth` - Vender Ethereum
- `analizar sol` - Analizar Solana
- `precio ada` - Ver precio de Cardano

## 🎯 Estrategia de Trading

### Objetivo
- **Meta**: 30% ganancia semanal
- **Riesgo por trade**: Máximo 2% del capital
- **Stop Loss**: 5% por defecto
- **Take Profit**: 10% por defecto

### Análisis Técnico
El bot utiliza múltiples indicadores:

- **RSI (14)**: Sobrecompra/sobreventa
- **MACD**: Momentum y divergencias
- **Bollinger Bands**: Volatilidad y niveles
- **Medias Móviles**: Tendencias (SMA 10, 20, 50)
- **Oscilador Estocástico**: Momentum
- **Volumen**: Confirmación de movimientos

### Evaluación de Oportunidades
Cada oportunidad se evalúa con un score de 0-10 basado en:

- **30%** - Score técnico de indicadores
- **25%** - Confianza de la IA
- **15%** - Volumen de trading
- **15%** - Volatilidad óptima
- **15%** - Relación riesgo/recompensa

### Gestión de Riesgo

#### Límites Diarios
- Máximo 10 trades por día
- Pérdida máxima diaria: $2,000
- Una posición por símbolo

#### Stop Loss Automático
- Monitoreo continuo de posiciones
- Ejecución automática de stop loss
- Take profit automático

#### Gestión de Capital
- Máximo 2% del capital por trade
- Ajuste basado en confianza del análisis
- Mínimo $10 por trade

## 🧠 Integración con IA

### Groq (LLaMA 3)
```python
# El bot consulta automáticamente a Groq para:
- Análisis de mercado
- Recomendaciones de trading
- Evaluación de riesgo/recompensa
- Sentimiento del mercado
```

### Ollama (Local)
```python
# Modelo local para:
- Análisis sin límites de API
- Mayor privacidad
- Disponibilidad 24/7
```

### Sistema de Respaldo
Si los LLMs no están disponibles, el bot usa:
- Análisis basado en reglas
- Lógica de indicadores técnicos
- Gestión de riesgo conservadora

## 📊 Monitoreo y Estadísticas

### Métricas en Tiempo Real
- P&L diario y semanal
- Número de trades ejecutados
- Posiciones activas
- Progreso hacia objetivo semanal

### Base de Datos
El bot almacena:
- Historial completo de trades
- Análisis técnicos históricos
- Configuraciones del bot
- Estadísticas de rendimiento

### Reportes Automáticos
- Resumen después de cada trade
- Reporte diario a las 8:00 AM
- Limpieza automática de datos antiguos

## ⚙️ Configuración Avanzada

### Parámetros de Trading
```env
TARGET_WEEKLY_RETURN=0.30      # 30% objetivo semanal
MAX_RISK_PER_TRADE=0.02        # 2% máximo por trade
STOP_LOSS_PERCENTAGE=0.05      # 5% stop loss
TAKE_PROFIT_PERCENTAGE=0.10    # 10% take profit
```

### Símbolos de Trading
El bot opera con las principales criptomonedas:
- BTCUSDT, ETHUSDT, BNBUSDT
- ADAUSDT, SOLUSDT, XRPUSDT
- DOTUSDT, LINKUSDT, LTCUSDT, BCHUSDT

### Timeframes de Análisis
- 1m, 5m, 15m (scalping)
- 1h, 4h (swing trading)
- 1d (análisis de tendencia)

## 🚨 Advertencias Importantes

### ⚠️ Riesgos del Trading
- **Alto Riesgo**: El trading de criptomonedas es extremadamente arriesgado
- **Pérdidas**: Puedes perder todo tu capital
- **Volatilidad**: Los precios pueden cambiar drásticamente
- **No Garantías**: El objetivo del 30% semanal es ambicioso y no garantizado

### 🧪 Recomendaciones
1. **Usar Testnet**: Siempre prueba primero en testnet
2. **Capital de Riesgo**: Solo invierte lo que puedes permitirte perder
3. **Monitoreo**: Supervisa el bot regularmente
4. **Backtesting**: Prueba estrategias con datos históricos
5. **Educación**: Aprende sobre trading antes de usar el bot

### 🔒 Seguridad
- Nunca compartas tus API keys
- Usa IP whitelisting en Binance
- Mantén las dependencias actualizadas
- Revisa los logs regularmente

## 🛠️ Desarrollo

### Estructura del Proyecto
```
crypto-trading-bot/
├── main.py                 # Archivo principal
├── config/
│   └── settings.py         # Configuración
├── src/
│   ├── telegram_bot.py     # Bot de Telegram
│   ├── binance_client.py   # Cliente de Binance
│   ├── market_analyzer.py  # Análisis técnico
│   ├── llm_advisor.py      # Asesor con IA
│   ├── trading_strategy.py # Estrategia de trading
│   └── database.py         # Gestor de base de datos
├── requirements.txt        # Dependencias
├── .env.example           # Ejemplo de configuración
└── README.md              # Esta documentación
```

### Agregar Nuevos Indicadores
```python
# En market_analyzer.py
def calculate_new_indicator(self, df: pd.DataFrame) -> pd.Series:
    # Tu lógica aquí
    return indicator_values
```

### Modificar Estrategia
```python
# En trading_strategy.py
async def _evaluate_opportunity(self, symbol: str, ...):
    # Modifica la lógica de evaluación
    pass
```

## 📈 Optimización para Hardware Limitado

### Configuración Ligera
```env
# Reducir carga computacional
MAX_DAILY_TRADES=5          # Menos trades
ANALYSIS_INTERVAL=30        # Análisis cada 30 min
TRADING_PAIRS=["BTCUSDT", "ETHUSDT"]  # Solo principales
```

### Uso de Memoria
- Base de datos SQLite (ligera)
- Limpieza automática de datos
- Análisis por lotes eficiente

### CPU Optimizado
- Análisis asíncrono
- Cache de indicadores
- Procesamiento paralelo limitado

## 🤝 Contribuciones

### Reportar Bugs
1. Crear issue en GitHub
2. Incluir logs de error
3. Describir pasos para reproducir

### Nuevas Características
1. Fork del repositorio
2. Crear branch para feature
3. Hacer pull request

### Mejoras Sugeridas
- [ ] Más indicadores técnicos
- [ ] Backtesting automático
- [ ] Dashboard web
- [ ] Alertas por email
- [ ] Soporte para más exchanges

## 📄 Licencia

Este proyecto es de código abierto. Úsalo bajo tu propia responsabilidad.

## 💬 Soporte

- **Issues**: GitHub Issues
- **Documentación**: Este README
- **Logs**: Revisa `trading_bot.log`

---

## ⚡ Inicio Rápido

```bash
# 1. Configurar
cp .env.example .env
# Editar .env con tus credenciales

# 2. Instalar
pip install -r requirements.txt

# 3. Ejecutar
python main.py
```

¡Listo! Tu bot de trading está funcionando. 🚀

---

**Disclaimer**: Este bot es para fines educativos. El trading de criptomonedas conlleva riesgos significativos. Nunca inviertas más de lo que puedes permitirte perder.