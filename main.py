import os
import time
import numpy as np
import pandas as pd
import requests
import yfinance as yf

# ==========================================
# CONFIGURACIÓN DE TELEGRAM
# GitHub Actions leerá los datos desde Variables Secretas (Secrets)
# ==========================================
TELEGRAM_TOKEN = os.getenv("7826119341:AAE56SlDtp1GBEpO6yMyynjNDhBrR8JAxRM")
TELEGRAM_CHAT_ID = os.getenv("5892087866")


def enviar_mensaje_telegram(mensaje):
    """Envía un mensaje directo a tu celular a través del Bot de Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ ERROR: No se encontraron las variables TELEGRAM_TOKEN o TELEGRAM_CHAT_ID")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown",
    }
    try:
        requests.post(url, data=payload, timeout=10)
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

    comprar_ya = []
    vender_ya = []
    mantener = []
    esperar_fuera = []

    for ticker in lista_tickers:
        try:
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

            rapida_h, rapida_a = (
                df["LR_Rapida"].iloc[-1],
                df["LR_Rapida"].iloc[-2],
            )
            lenta_h, lenta_a = df["LR_Lenta"].iloc[-1], df["LR_Lenta"].iloc[-2]
            precio_h = df["Close"].iloc[-1]
            vol_f = df["Volumen_Fuerte"].iloc[-1]

            cruce_compra = (rapida_a <= lenta_a and rapida_h > lenta_h) and vol_f
            cruce_venta = rapida_a >= lenta_a and rapida_h < lenta_h
            tendencia_alcista = rapida_h > lenta_h

            if cruce_compra:
                comprar_ya.append(f"• `{ticker}` ➔ Entrada a `${precio_h:.4f}`")
            elif cruce_venta:
                vender_ya.append(f"• `{ticker}` ➔ Salida a `${precio_h:.4f}`")
            elif tendencia_alcista:
                mantener.append(f"• `{ticker}`: `${precio_h:.4f}`")
            else:
                esperar_fuera.append(f"• `{ticker}`: `${precio_h:.4f}`")

        except Exception as e:
            print(f"  ⚠️ Error en {ticker}: {e}")

    # Construcción del mensaje para Telegram
    mensaje_partes = [f"🚨 *ACCIONES RECOMENDADAS ({hora_actual})* 🚨\n"]

    if comprar_ya:
        mensaje_partes.append("🟢 *¡COMPRAR AHORA (NUEVA ENTRADA)!*")
        mensaje_partes.extend(comprar_ya)
        mensaje_partes.append("")

    if vender_ya:
        mensaje_partes.append("🔴 *¡VENDER AHORA (NUEVA SALIDA)!*")
        mensaje_partes.extend(vender_ya)
        mensaje_partes.append("")

    if mantener:
        mensaje_partes.append("🟢 *MANTENER POSICIÓN (Sigue Alcista):*")
        mensaje_partes.extend(mantener)
        mensaje_partes.append("")

    if esperar_fuera:
        mensaje_partes.append("⚪ *EN EFECTIVO / ESPERAR FUERA (Sin Señal):*")
        mensaje_partes.extend(esperar_fuera)

    mensaje_final = "\n".join(mensaje_partes)
    enviar_mensaje_telegram(mensaje_final)
    print("✅ Reporte ejecutado y enviado a Telegram correctamente.")


mis_cryptos = [
    "BTC-USD",
    "ETH-USD",
    "SOL-USD",
    "BNB-USD",
    "XRP-USD",
    "ADA-USD",
    "AVAX-USD",
]

# Se ejecuta solo una vez cuando GitHub Actions despierta la tarea
if __name__ == "__main__":
    escanear_crypto_15m(mis_cryptos)
