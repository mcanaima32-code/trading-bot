import asyncio
import json
import logging
import requests
from typing import Dict, List, Optional
from config.settings import settings

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

class LLMAdvisor:
    def __init__(self):
        self.groq_client = None
        self.openai_client = None
        self.ollama_available = False
        
        # Inicializar clientes disponibles
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Inicializar clientes de LLM disponibles"""
        # Groq
        if GROQ_AVAILABLE and settings.GROQ_API_KEY:
            try:
                self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
                logger.info("Cliente Groq inicializado")
            except Exception as e:
                logger.error(f"Error inicializando Groq: {e}")
        
        # OpenAI
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            try:
                self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("Cliente OpenAI inicializado")
            except Exception as e:
                logger.error(f"Error inicializando OpenAI: {e}")
        
        # Verificar Ollama
        try:
            response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                self.ollama_available = True
                logger.info("Ollama disponible")
        except Exception as e:
            logger.warning(f"Ollama no disponible: {e}")
    
    def _create_trading_prompt(self, symbol: str, market_data: Dict, technical_analysis: Dict) -> str:
        """Crear prompt para análisis de trading"""
        prompt = f"""
Eres un experto analista de trading de criptomonedas. Analiza la siguiente información y proporciona una recomendación de trading.

SÍMBOLO: {symbol}

DATOS DE MERCADO:
- Precio actual: ${market_data.get('price', 0):.4f}
- Cambio 24h: {market_data.get('change_24h', 0):.2f}%
- Volumen 24h: {market_data.get('volume_24h', 0):,.0f}
- Máximo 24h: ${market_data.get('high_24h', 0):.4f}
- Mínimo 24h: ${market_data.get('low_24h', 0):.4f}

ANÁLISIS TÉCNICO:
- Score técnico: {technical_analysis.get('score', 5):.1f}/10
- Tendencia: {technical_analysis.get('trend', 'NEUTRAL')}
- RSI: {technical_analysis.get('indicators', {}).get('rsi', 50):.1f}
- MACD: {technical_analysis.get('indicators', {}).get('macd', 0):.4f}
- Bollinger Bands %: {technical_analysis.get('indicators', {}).get('bb_percent', 0.5):.2f}
- Stochastic K: {technical_analysis.get('indicators', {}).get('stoch_k', 50):.1f}

SEÑALES DETECTADAS:
{json.dumps(technical_analysis.get('signals', []), indent=2)}

OBJETIVO: Obtener 30% de ganancia semanal con gestión de riesgo conservadora.

Proporciona tu análisis en el siguiente formato JSON:
{{
    "recommendation": "BUY/SELL/HOLD",
    "confidence": 85,
    "reasoning": "Explicación detallada de tu recomendación",
    "entry_price": 0.0000,
    "stop_loss": 0.0000,
    "take_profit": 0.0000,
    "risk_level": "LOW/MEDIUM/HIGH",
    "time_horizon": "SHORT/MEDIUM/LONG",
    "key_factors": ["factor1", "factor2", "factor3"]
}}

Responde SOLO con el JSON válido, sin texto adicional.
        """
        return prompt.strip()
    
    async def _query_groq(self, prompt: str) -> Optional[Dict]:
        """Consultar Groq"""
        if not self.groq_client:
            return None
        
        try:
            response = self.groq_client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": "Eres un experto analista de trading de criptomonedas."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Error consultando Groq: {e}")
            return None
    
    async def _query_openai(self, prompt: str) -> Optional[Dict]:
        """Consultar OpenAI"""
        if not self.openai_client:
            return None
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un experto analista de trading de criptomonedas."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Error consultando OpenAI: {e}")
            return None
    
    async def _query_ollama(self, prompt: str) -> Optional[Dict]:
        """Consultar Ollama"""
        if not self.ollama_available:
            return None
        
        try:
            response = requests.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 500
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('response', '').strip()
                
                # Intentar extraer JSON del contenido
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_content = content[start_idx:end_idx]
                    return json.loads(json_content)
            
            return None
            
        except Exception as e:
            logger.error(f"Error consultando Ollama: {e}")
            return None
    
    def _create_fallback_analysis(self, symbol: str, technical_analysis: Dict) -> Dict:
        """Crear análisis de respaldo basado en reglas"""
        score = technical_analysis.get('score', 5)
        signals = technical_analysis.get('signals', [])
        indicators = technical_analysis.get('indicators', {})
        
        # Determinar recomendación basada en score
        if score >= 7:
            recommendation = "BUY"
            confidence = min(95, int(score * 10))
            reasoning = f"Score técnico alto ({score:.1f}/10) con múltiples indicadores positivos"
        elif score <= 3:
            recommendation = "SELL"
            confidence = min(95, int((10 - score) * 10))
            reasoning = f"Score técnico bajo ({score:.1f}/10) con señales de venta"
        else:
            recommendation = "HOLD"
            confidence = 60
            reasoning = f"Score técnico neutral ({score:.1f}/10), esperar mejor oportunidad"
        
        # Calcular precios objetivo
        current_price = technical_analysis.get('current_price', 0)
        if current_price > 0:
            if recommendation == "BUY":
                entry_price = current_price
                stop_loss = current_price * (1 - settings.STOP_LOSS_PERCENTAGE)
                take_profit = current_price * (1 + settings.TAKE_PROFIT_PERCENTAGE)
            elif recommendation == "SELL":
                entry_price = current_price
                stop_loss = current_price * (1 + settings.STOP_LOSS_PERCENTAGE)
                take_profit = current_price * (1 - settings.TAKE_PROFIT_PERCENTAGE)
            else:
                entry_price = current_price
                stop_loss = current_price * 0.95
                take_profit = current_price * 1.05
        else:
            entry_price = stop_loss = take_profit = 0
        
        # Determinar nivel de riesgo
        rsi = indicators.get('rsi', 50)
        if rsi < 30 or rsi > 70:
            risk_level = "HIGH"
        elif rsi < 40 or rsi > 60:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        # Factores clave
        key_factors = []
        buy_signals = [s for s in signals if s['type'] == 'BUY']
        sell_signals = [s for s in signals if s['type'] == 'SELL']
        
        if len(buy_signals) > len(sell_signals):
            key_factors.append(f"{len(buy_signals)} señales de compra")
        elif len(sell_signals) > len(buy_signals):
            key_factors.append(f"{len(sell_signals)} señales de venta")
        
        if rsi < 30:
            key_factors.append("RSI oversold")
        elif rsi > 70:
            key_factors.append("RSI overbought")
        
        trend = technical_analysis.get('trend', 'NEUTRAL')
        key_factors.append(f"Tendencia {trend}")
        
        return {
            "recommendation": recommendation,
            "confidence": confidence,
            "reasoning": reasoning,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_level": risk_level,
            "time_horizon": "SHORT",
            "key_factors": key_factors[:3]
        }
    
    async def get_trading_advice(self, symbol: str, market_data: Dict, technical_analysis: Dict) -> Dict:
        """Obtener consejo de trading usando LLMs disponibles"""
        prompt = self._create_trading_prompt(symbol, market_data, technical_analysis)
        
        # Intentar con diferentes LLMs
        llm_results = []
        
        # Groq (gratuito con límites)
        if self.groq_client:
            groq_result = await self._query_groq(prompt)
            if groq_result:
                groq_result['source'] = 'groq'
                llm_results.append(groq_result)
        
        # Ollama (local, gratuito)
        if self.ollama_available:
            ollama_result = await self._query_ollama(prompt)
            if ollama_result:
                ollama_result['source'] = 'ollama'
                llm_results.append(ollama_result)
        
        # OpenAI (de pago, como respaldo)
        if self.openai_client and len(llm_results) == 0:
            openai_result = await self._query_openai(prompt)
            if openai_result:
                openai_result['source'] = 'openai'
                llm_results.append(openai_result)
        
        # Si tenemos resultados de LLM, usar el mejor
        if llm_results:
            # Si hay múltiples resultados, usar el de mayor confianza
            best_result = max(llm_results, key=lambda x: x.get('confidence', 0))
            logger.info(f"Usando consejo de {best_result.get('source', 'unknown')} para {symbol}")
            return best_result
        
        # Usar análisis de respaldo
        logger.warning(f"Usando análisis de respaldo para {symbol}")
        fallback_result = self._create_fallback_analysis(symbol, technical_analysis)
        fallback_result['source'] = 'fallback'
        return fallback_result
    
    async def get_market_sentiment(self, symbols: List[str]) -> Dict:
        """Obtener sentimiento general del mercado"""
        try:
            prompt = f"""
Analiza el sentimiento general del mercado de criptomonedas basado en los siguientes símbolos:
{', '.join(symbols)}

Considera:
- Tendencias generales del mercado
- Factores macroeconómicos
- Adopción institucional
- Regulaciones
- Sentimiento de redes sociales

Proporciona tu análisis en formato JSON:
{{
    "sentiment": "BULLISH/BEARISH/NEUTRAL",
    "confidence": 85,
    "reasoning": "Explicación del sentimiento",
    "market_phase": "ACCUMULATION/MARKUP/DISTRIBUTION/MARKDOWN",
    "key_drivers": ["driver1", "driver2", "driver3"],
    "outlook": "Perspectiva a corto plazo"
}}

Responde SOLO con el JSON válido.
            """
            
            # Intentar con LLMs disponibles
            if self.groq_client:
                result = await self._query_groq(prompt)
                if result:
                    return result
            
            if self.ollama_available:
                result = await self._query_ollama(prompt)
                if result:
                    return result
            
            # Respaldo simple
            return {
                "sentiment": "NEUTRAL",
                "confidence": 50,
                "reasoning": "Análisis automático no disponible",
                "market_phase": "NEUTRAL",
                "key_drivers": ["Volatilidad normal", "Volumen estable"],
                "outlook": "Mantener cautela y seguir indicadores técnicos"
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo sentimiento del mercado: {e}")
            return {
                "sentiment": "NEUTRAL",
                "confidence": 50,
                "reasoning": f"Error en análisis: {str(e)}",
                "market_phase": "NEUTRAL",
                "key_drivers": ["Error en análisis"],
                "outlook": "Usar análisis técnico como referencia principal"
            }
    
    async def analyze_risk_reward(self, symbol: str, entry_price: float, stop_loss: float, take_profit: float) -> Dict:
        """Analizar relación riesgo/recompensa"""
        try:
            if entry_price <= 0:
                return {"risk_reward_ratio": 0, "analysis": "Precio de entrada inválido"}
            
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
            
            if risk == 0:
                return {"risk_reward_ratio": float('inf'), "analysis": "Sin riesgo definido"}
            
            ratio = reward / risk
            
            analysis = ""
            if ratio >= 3:
                analysis = "Excelente relación riesgo/recompensa"
            elif ratio >= 2:
                analysis = "Buena relación riesgo/recompensa"
            elif ratio >= 1.5:
                analysis = "Relación riesgo/recompensa aceptable"
            else:
                analysis = "Relación riesgo/recompensa desfavorable"
            
            return {
                "risk_reward_ratio": ratio,
                "risk_amount": risk,
                "reward_amount": reward,
                "analysis": analysis,
                "recommendation": "PROCEED" if ratio >= 2 else "CAUTION" if ratio >= 1.5 else "AVOID"
            }
            
        except Exception as e:
            logger.error(f"Error analizando riesgo/recompensa: {e}")
            return {"risk_reward_ratio": 0, "analysis": f"Error: {str(e)}"}
    
    def get_available_llms(self) -> List[str]:
        """Obtener lista de LLMs disponibles"""
        available = []
        
        if self.groq_client:
            available.append("Groq (llama3-8b)")
        
        if self.ollama_available:
            available.append(f"Ollama ({settings.OLLAMA_MODEL})")
        
        if self.openai_client:
            available.append("OpenAI (gpt-3.5-turbo)")
        
        available.append("Fallback Rules")
        
        return available