import os
import time
import numpy as np
import pandas as pd
import requests
import yfinance as yf

# ==========================================
# 1. CONFIGURACIÓN DE TELEGRAM
# ==========================================
TELEGRAM_TOKEN = "7826119341:AAE56SlDtp1GBEpO6yMyynjNDhBrR8JAxRM"
TELEGRAM_CHAT_ID = "5892087866"


def enviar_mensaje_telegram(mensaje):
    """Envía un mensaje directo a tu celular a través del Bot de Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown",
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Error en respuesta de Telegram: {response.text}")
    except Exception as e:
        print(f"⚠️ Error al conectar con Telegram: {e}")


def calcular_regresion_rapida(serie, periodos):
    """Calcula la regresión lineal optimizada."""
    y = serie.to_numpy()
    n = len(y)
    pendientes = np.zeros(n)

    if n < periodos:
        return pd.Series(pendientes, index=serie.index)

    x = np.arange(periodos)
    x_mean = x.mean()
    x_diff = x - x_mean
    x_var = (x_diff**2).sum()

    for i in range(periodos, n):
        y_window = y[i - periodos : i]
        y_mean = y_window.mean()
        slope = (x_diff * (y_window - y_mean)).sum() / x_var
        intercept = y_mean - slope * x_mean
        pendientes[i] = slope * (periodos - 1) + intercept

    return pd.Series(pendientes, index=serie.index)


def escanear_crypto_15m(lista_tickers):
    hora_actual = time.strftime("%H:%M:%S")
    print(f"[{hora_actual}] 🔍 Escaneando mercado (Velas 15m)...")

    dentro_comprado = []
    fuera_vendido = []
    alertas_nuevas = []

    for ticker in lista_tickers:
        try:
            # Descargar datos de 15 minutos (5 días)
            df = yf.download(
                ticker, period="5d", interval="15m", progress=False
            )

            if df.empty or len(df) < 20:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Cálculo de Regresiones
            df["LR_Rapida"] = calcular_regresion_rapida(
                df["Close"], periodos=5
            )
            df["LR_Lenta"] = calcular_regresion_rapida(
                df["Close"], periodos=15
            )

            df["Volumen_SMA"] = df["Volume"].rolling(window=10).mean()
            df["Volumen_Fuerte"] = df["Volume"] >= (df["Volumen_SMA"] * 0.9)

            # Evaluar penúltima (-2) y última vela (-1)
            rapida_h, rapida_a = (
                df["LR_Rapida"].iloc[-1],
                df["LR_Rapida"].iloc[-2],
            )
            lenta_h, lenta_a = df["LR_Lenta"].iloc[-1], df["LR_Lenta"].iloc[-2]
            precio_h = df["Close"].iloc[-1]
            vol_f = df["Volumen_Fuerte"].iloc[-1]

            # Detección de cruce fresco en la vela actual
            cruce_compra = (rapida_a <= lenta_a and rapida_h > lenta_h) and vol_f
            cruce_venta = rapida_a >= lenta_a and rapida_h < lenta_h

            # Determinar estado actual (Si la rápida está sobre la lenta = Tendencia Alcista/Comprado)
            esta_comprado = rapida_h > lenta_h

            if cruce_compra:
                alertas_nuevas.append(f"🟢 *¡NUEVO CRUCE DE COMPRA!* en `{ticker}` a `${precio_h:.4f}`")
            elif cruce_venta:
                alertas_nuevas.append(f"🔴 *¡NUEVO CRUCE DE VENTA!* en `{ticker}` a `${precio_h:.4f}`")

            # Clasificación de estado general
            if esta_comprado:
                dentro_comprado.append(f"• `{ticker}`: `${precio_h:.4f}`")
            else:
                fuera_vendido.append(f"• `{ticker}`: `${precio_h:.4f}`")

        except Exception as e:
            print(f"  ⚠️ Error en {ticker}: {e}")

    # ==========================================
    # CONSTRUCCIÓN DEL MENSAJE DE TELEGRAM
    # ==========================================
    mensaje_partes = []

    # 1. Si hubo cruce nuevo en esta vela, lo pone arriba en grande
    if alertas_nuevas:
        mensaje_partes.append("🚨 *ALERTAS EN LA VELA ACTUAL:*")
        mensaje_partes.extend(alertas_nuevas)
        mensaje_partes.append("")

    # 2. Resumen del Estado de Mercado
    mensaje_partes.append(f"📊 *REPORTE DE ESTADO ({hora_actual})*")
    mensaje_partes.append("----------------------------------")

    mensaje_partes.append("🟢 *ENTRAR / PERMANECER COMPRADO:*")
    if dentro_comprado:
        mensaje_partes.extend(dentro_comprado)
    else:
        mensaje_partes.append("• _Ninguna moneda en tendencia alcista_")

    mensaje_partes.append("")
    mensaje_partes.append("🔴 *SALIR / PERMANECER EN EFECTIVO:*")
    if fuera_vendido:
        mensaje_partes.extend(fuera_vendido)
    else:
        mensaje_partes.append("• _Ninguna moneda en tendencia bajista_")

    mensaje_final = "\n".join(mensaje_partes)

    # Enviar reporte a Telegram
    enviar_mensaje_telegram(mensaje_final)
    print("  ✅ Reporte con precios enviado a Telegram correctamente.")


# ==========================================
# 2. LISTA DE CRIPTOMONEDAS Y EJECUCIÓN
# ==========================================
mis_cryptos = [
    "BTC-USD",
    "ETH-USD",
    "SOL-USD",
    "BNB-USD",
    "XRP-USD",
    "ADA-USD",
    "AVAX-USD",
]

print("🚀 Iniciando servicio de alertas...")
enviar_mensaje_telegram(
    "🤖 *Bot de Señales Crypto Activado*\nEl escáner enviará el estado y precio de cada moneda cada 15 minutos."
)

# Bucle continuo (Revisa cada 15 minutos = 900 segundos)
while True:
    escanear_crypto_15m(mis_cryptos)
    print("⏳ Esperando 15 minutos para la siguiente vela...\n")
    time.sleep(900)
