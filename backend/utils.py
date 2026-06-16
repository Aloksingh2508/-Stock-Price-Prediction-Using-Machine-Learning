import yfinance as yf
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

def fetch_stock_data(ticker, period="2y"):
    try:
        df = yf.download(ticker, period=period, auto_adjust=True)
        if df.empty:
            return None
        return df[['Close', 'Volume', 'High', 'Low', 'Open']]
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

def preprocess_data(df, time_step=60):
    close = df[['Close']].values
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(close)

    X, y = [], []
    for i in range(time_step, len(scaled_data)):
        X.append(scaled_data[i-time_step:i, 0])
        y.append(scaled_data[i, 0])

    X, y = np.array(X), np.array(y)
    X = X.reshape(X.shape[0], X.shape[1], 1)
    return X, y, scaler, scaled_data

def compute_rsi(series, window=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window).mean()
    loss = -delta.where(delta < 0, 0).rolling(window).mean()
    rs = gain / (loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def compute_bollinger_bands(series, window=20, num_std=2):
    sma = series.rolling(window).mean()
    std = series.rolling(window).std()
    upper = sma + (num_std * std)
    lower = sma - (num_std * std)
    return upper, sma, lower

def compute_indicators(df):
    close = df['Close'].squeeze()
    volume = df['Volume'].squeeze()
    high = df['High'].squeeze()
    low = df['Low'].squeeze()

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    ema12 = close.ewm(span=12).mean()
    rsi = compute_rsi(close)
    macd_line, signal_line, histogram = compute_macd(close)
    bb_upper, bb_mid, bb_lower = compute_bollinger_bands(close)

    # Average True Range (ATR)
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()

    # Volume moving average
    vol_ma = volume.rolling(20).mean()

    return {
        "sma20": sma20.dropna().tolist(),
        "sma50": sma50.dropna().tolist(),
        "ema12": ema12.dropna().tolist(),
        "rsi": rsi.dropna().tolist(),
        "macd": macd_line.dropna().tolist(),
        "macd_signal": signal_line.dropna().tolist(),
        "macd_hist": histogram.dropna().tolist(),
        "bb_upper": bb_upper.dropna().tolist(),
        "bb_mid": bb_mid.dropna().tolist(),
        "bb_lower": bb_lower.dropna().tolist(),
        "atr": atr.dropna().tolist(),
        "volume": volume.tolist(),
        "vol_ma": vol_ma.dropna().tolist(),
        "current_rsi": float(rsi.dropna().iloc[-1]) if not rsi.dropna().empty else 50.0,
        "current_macd": float(macd_line.dropna().iloc[-1]) if not macd_line.dropna().empty else 0.0,
        "current_signal": float(signal_line.dropna().iloc[-1]) if not signal_line.dropna().empty else 0.0,
        "current_bb_upper": float(bb_upper.dropna().iloc[-1]) if not bb_upper.dropna().empty else 0.0,
        "current_bb_lower": float(bb_lower.dropna().iloc[-1]) if not bb_lower.dropna().empty else 0.0,
    }

def generate_ai_suggestion(close_prices, rsi, macd, macd_signal, bb_upper, bb_lower, predicted_next):
    current_price = float(close_prices[-1])
    signals = []
    score = 0

    # RSI analysis — explained in plain English
    if rsi < 30:
        signals.append(f"🟢 Momentum (RSI): {rsi:.1f} — The stock looks oversold. People may have sold too aggressively, which can create a buying opportunity.")
        score += 2
    elif rsi < 45:
        signals.append(f"🟡 Momentum (RSI): {rsi:.1f} — Slightly low. The stock has been leaning downward but not at an extreme level.")
        score += 1
    elif rsi > 70:
        signals.append(f"🔴 Momentum (RSI): {rsi:.1f} — The stock looks overbought. It may have risen too fast and could be due for a pullback.")
        score -= 2
    elif rsi > 55:
        signals.append(f"🟠 Momentum (RSI): {rsi:.1f} — Slightly elevated. The stock has been trending up but isn't at a danger zone yet.")
        score -= 1
    else:
        signals.append(f"⚪ Momentum (RSI): {rsi:.1f} — Neutral. No extreme buying or selling pressure right now.")

    # MACD analysis — plain English
    if macd > macd_signal:
        signals.append("🟢 Trend strength (MACD): The short-term trend is rising faster than the long-term — a positive (bullish) signal.")
        score += 1
    else:
        signals.append("🔴 Trend strength (MACD): The short-term trend is falling below the long-term — a negative (bearish) signal.")
        score -= 1

    # Bollinger Band analysis — plain English
    if current_price < bb_lower:
        signals.append(f"🟢 Price range (Bollinger): At ${current_price:.2f}, the price is below the lower boundary — it may be unusually cheap right now.")
        score += 2
    elif current_price > bb_upper:
        signals.append(f"🔴 Price range (Bollinger): At ${current_price:.2f}, the price is above the upper boundary — it may be unusually expensive right now.")
        score -= 2
    else:
        signals.append(f"⚪ Price range (Bollinger): At ${current_price:.2f}, the price is within normal boundaries — no extreme valuation.")

    # AI prediction analysis — plain English
    change_pct = ((predicted_next - current_price) / current_price) * 100
    if change_pct > 1.5:
        signals.append(f"🟢 AI forecast: The model expects the price to rise by about +{change_pct:.1f}% — a meaningfully positive prediction.")
        score += 2
    elif change_pct > 0:
        signals.append(f"🟡 AI forecast: The model expects a small rise of +{change_pct:.1f}% — mildly positive.")
        score += 1
    elif change_pct > -1.5:
        signals.append(f"🟠 AI forecast: The model expects a small dip of {change_pct:.1f}% — mildly cautious.")
        score -= 1
    else:
        signals.append(f"🔴 AI forecast: The model expects a notable decline of {change_pct:.1f}% — a negative prediction.")
        score -= 2

    # Final decision
    if score >= 3:
        action = "STRONG BUY"
        action_color = "#00ff88"
        confidence = min(95, 70 + score * 4)
    elif score >= 1:
        action = "BUY"
        action_color = "#4ade80"
        confidence = min(80, 60 + score * 5)
    elif score <= -3:
        action = "STRONG SELL"
        action_color = "#ff4d4d"
        confidence = min(95, 70 + abs(score) * 4)
    elif score <= -1:
        action = "SELL"
        action_color = "#f87171"
        confidence = min(80, 60 + abs(score) * 5)
    else:
        action = "HOLD"
        action_color = "#facc15"
        confidence = 55

    return {
        "action": action,
        "color": action_color,
        "confidence": int(confidence),
        "score": score,
        "signals": signals,
        "predicted_change_pct": round(change_pct, 2),
        "current_price": round(current_price, 2),
        "predicted_next": round(predicted_next, 2)
    }

def get_live_info(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.info
        hist = t.history(period="5d")

        current_price = float(hist['Close'].iloc[-1]) if not hist.empty else 0
        prev_price = float(hist['Close'].iloc[-2]) if len(hist) >= 2 else current_price
        change = current_price - prev_price
        change_pct = (change / prev_price * 100) if prev_price else 0

        return {
            "price": round(current_price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "market_cap": info.get("marketCap", 0),
            "pe_ratio": info.get("trailingPE", "N/A"),
            "volume": info.get("volume", 0),
            "avg_volume": info.get("averageVolume", 0),
            "52w_high": info.get("fiftyTwoWeekHigh", 0),
            "52w_low": info.get("fiftyTwoWeekLow", 0),
            "sector": info.get("sector", "Technology"),
            "name": info.get("longName", ticker)
        }
    except Exception as e:
        print(f"Live info error for {ticker}: {e}")
        return {"price": 0, "change": 0, "change_pct": 0}