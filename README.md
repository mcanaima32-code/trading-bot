# 🤖 Bot de Trading de Criptomonedas

Bot completo de trading automatizado con controles avanzados de riesgo, comandos personalizables e interfaz web interactiva. Diseñado especialmente para funcionar en **Google Colab**.

## 🚀 Características Principales

### 📊 Control Avanzado de Riesgo
- **Límites dinámicos**: Pérdida/ganancia máxima diaria configurable
- **Circuit breakers**: Parada automática en condiciones extremas
- **Gestión de exposición**: Control de posiciones y correlaciones
- **Métricas avanzadas**: VaR, Sharpe Ratio, Drawdown, etc.

### 🤖 Comandos Inteligentes
- **Comandos personalizables**: Crea tus propios comandos via regex
- **Plantillas predefinidas**: Compra rápida, stop loss, alertas de precio
- **Integración con LLMs**: Groq, OpenAI, Ollama para análisis IA
- **Control por Telegram**: Interfaz completa via bot de Telegram

### 🌐 Interfaz Web Interactiva
- **Dashboard en tiempo real**: Métricas, gráficos y estado del bot
- **Configuración visual**: Sliders para ajustar parámetros de riesgo
- **Análisis de mercado**: Indicadores técnicos y señales automáticas
- **Gestión de portfolio**: Visualización de posiciones y rendimiento

### 📈 Análisis Técnico Automático
- **Indicadores múltiples**: RSI, MACD, Bollinger Bands, SMA/EMA
- **Scoring inteligente**: Puntuación automática de oportunidades
- **Integración con IA**: Análisis mejorado con modelos de lenguaje
- **Backtesting**: Simulación histórica de estrategias

## 🛠️ Instalación y Configuración

### Para Google Colab (Recomendado)

1. **Abrir Google Colab**
   ```python
   # Clonar el repositorio
   !git clone https://github.com/tu-usuario/trading-bot.git
   %cd trading-bot
   
   # Ejecutar el bot
   from main_colab import colab_start
   bot_manager, public_url = colab_start()
   ```

2. **Configurar Credenciales**
   - El bot creará automáticamente un archivo `.env`
   - Edita las credenciales necesarias:
     ```bash
     TELEGRAM_BOT_TOKEN=tu_token_aqui
     BINANCE_API_KEY=tu_api_key_aqui
     BINANCE_SECRET_KEY=tu_secret_key_aqui
     GROQ_API_KEY=tu_groq_key_aqui  # Opcional
     ```

3. **Acceder a la Interfaz Web**
   - El bot mostrará una URL pública de ngrok
   - Usa esta URL para acceder al dashboard

### Para Instalación Local

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/tu-usuario/trading-bot.git
   cd trading-bot
   ```

2. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar variables de entorno**
   ```bash
   cp .env.example .env
   # Editar .env con tus credenciales
   ```

4. **Ejecutar el bot**
   ```bash
   python main_colab.py
   ```

## 🔑 Configuración de APIs

### 1. Telegram Bot

1. Habla con [@BotFather](https://t.me/botfather) en Telegram
2. Crea un nuevo bot: `/newbot`
3. Copia el token del bot
4. Obtén tu Chat ID:
   - Envía un mensaje a tu bot
   - Ve a: `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Copia el `chat.id`

### 2. Binance API

⚠️ **IMPORTANTE**: Usa siempre Testnet para pruebas

**Testnet (Recomendado para pruebas):**
1. Ve a [Binance Testnet](https://testnet.binance.vision/)
2. Inicia sesión con tu cuenta de Binance
3. Crea una API Key
4. Configura `BINANCE_TESTNET=True`

**Mainnet (Solo para trading real):**
1. Ve a [Binance API Management](https://www.binance.com/en/my/settings/api-management)
2. Crea una nueva API Key
3. Habilita "Spot & Margin Trading"
4. Configura `BINANCE_TESTNET=False`

### 3. LLM APIs (Opcional)

**Groq (Gratuito con límites):**
1. Ve a [Groq Console](https://console.groq.com/)
2. Crea una cuenta gratuita
3. Genera una API Key
4. Configura `GROQ_API_KEY`

**OpenAI (De pago):**
1. Ve a [OpenAI API](https://openai.com/api/)
2. Crea una cuenta y agrega créditos
3. Genera una API Key
4. Configura `OPENAI_API_KEY`

**Ollama (Local, gratuito):**
1. Instala [Ollama](https://ollama.ai/)
2. Descarga un modelo: `ollama pull llama2`
3. Configura `OLLAMA_BASE_URL=http://localhost:11434`

## 📱 Uso del Bot

### Comandos de Telegram

**Comandos básicos:**
- `/start` - Iniciar el bot
- `/status` - Ver estado y balance
- `/analizar` - Analizar mercado
- `/balance` - Ver balance actual
- `/help` - Mostrar ayuda

**Comandos de trading:**
- `/comprar BTCUSDT` - Comprar Bitcoin
- `/vender BTCUSDT` - Vender Bitcoin
- `/posiciones` - Ver posiciones abiertas

**Comandos por texto natural:**
- `comprar btc 100` - Comprar $100 de Bitcoin
- `vender eth` - Vender todo Ethereum
- `precio btc` - Ver precio de Bitcoin
- `analizar sol` - Analizar Solana

### Interfaz Web

**Dashboard Principal (`/`):**
- Estado del bot en tiempo real
- Métricas de riesgo y P&L
- Análisis de mercado automático
- Portfolio y trades recientes
- Panel de trading rápido

**Configuración de Riesgo (`/risk-config`):**
- Límites de pérdida/ganancia diaria
- Tamaños máximos de posición
- Control de drawdown
- Circuit breakers
- Configuraciones predefinidas

**Comandos Personalizados (`/commands`):**
- Crear comandos con regex
- Plantillas predefinidas
- Editor visual de comandos
- Pruebas de comandos

**Análisis Avanzado (`/analytics`):**
- Métricas de rendimiento
- Gráficos interactivos
- Backtesting de estrategias
- Reportes detallados

## ⚙️ Configuración de Riesgo

### Configuraciones Predefinidas

**Conservador:**
- Pérdida máxima diaria: 2%
- Ganancia objetivo: 8%
- Máximo por posición: 5%
- Drawdown máximo: 5%

**Moderado (Por defecto):**
- Pérdida máxima diaria: 5%
- Ganancia objetivo: 15%
- Máximo por posición: 10%
- Drawdown máximo: 10%

**Agresivo:**
- Pérdida máxima diaria: 10%
- Ganancia objetivo: 30%
- Máximo por posición: 20%
- Drawdown máximo: 20%

### Parámetros Personalizables

- **Límites diarios**: Pérdida/ganancia máxima, número de trades
- **Límites de posición**: Tamaño máximo, riesgo por trade
- **Control de drawdown**: Límites de caída y pérdidas consecutivas
- **Horarios de trading**: Inicio/fin, fines de semana
- **Circuit breakers**: Volatilidad, crash de mercado

## 🔒 Seguridad

### Mejores Prácticas

1. **Usa siempre Testnet** para pruebas
2. **Nunca compartas** tus API keys
3. **Configura límites conservadores** al inicio
4. **Monitorea constantemente** el bot
5. **Ten un plan de salida** claro

### Medidas de Seguridad Implementadas

- **Circuit breakers automáticos**
- **Límites de riesgo estrictos**
- **Validación de todas las operaciones**
- **Logs detallados de actividad**
- **Emergency stop manual**

## 📊 Métricas y Análisis

### Indicadores Técnicos
- **RSI**: Relative Strength Index
- **MACD**: Moving Average Convergence Divergence
- **Bollinger Bands**: Bandas de volatilidad
- **SMA/EMA**: Medias móviles simples y exponenciales
- **Stochastic**: Oscilador estocástico

### Métricas de Riesgo
- **VaR**: Value at Risk (1 día, 95% confianza)
- **Sharpe Ratio**: Rendimiento ajustado por riesgo
- **Drawdown**: Pérdida máxima desde el pico
- **Win Rate**: Porcentaje de trades ganadores
- **Profit Factor**: Ratio ganancia/pérdida

## 🚨 Troubleshooting

### Problemas Comunes

**Error de conexión a Binance:**
- Verifica tus API keys
- Asegúrate de usar Testnet para pruebas
- Revisa las restricciones IP

**Bot de Telegram no responde:**
- Verifica el token del bot
- Asegúrate de tener el Chat ID correcto
- Revisa que el bot esté iniciado

**Interfaz web no carga:**
- Verifica que ngrok esté funcionando
- Revisa los logs para errores
- Intenta reiniciar el bot

**Error de permisos en Colab:**
- Asegúrate de tener los archivos en el directorio correcto
- Verifica que las dependencias estén instaladas
- Revisa los logs de error

### Logs y Debugging

Los logs se guardan en:
- `trading_bot.log` - Logs principales
- Consola de Colab - Output en tiempo real
- Interfaz web - Estado y errores

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## ⚠️ Disclaimer

**ADVERTENCIA IMPORTANTE:**

Este bot es para fines educativos y experimentales. El trading de criptomonedas conlleva riesgos significativos:

- ❌ **Nunca inviertas más de lo que puedes permitirte perder**
- ❌ **Los resultados pasados no garantizan resultados futuros**
- ❌ **Usa siempre Testnet para pruebas**
- ❌ **El autor no se hace responsable de pérdidas financieras**

**Usa este bot bajo tu propia responsabilidad.**

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🙏 Agradecimientos

- [python-binance](https://github.com/sammchardy/python-binance) - Cliente de Binance
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Bot de Telegram
- [TA-Lib](https://github.com/mrjbq7/ta-lib) - Análisis técnico
- [Flask](https://flask.palletsprojects.com/) - Framework web
- [Bootstrap](https://getbootstrap.com/) - UI Framework

---

**¡Happy Trading! 🚀📈**