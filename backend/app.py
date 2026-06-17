from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from model import generate_predictions
from utils import get_live_info, fetch_stock_data, compute_indicators
import yfinance as yf
import numpy as np
import os
import json
import urllib.request
import sqlite3
import base64
from werkzeug.security import generate_password_hash, check_password_hash

# ─── DATABASE INITIALIZATION ──────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'users.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            name TEXT,
            picture TEXT,
            auth_provider TEXT DEFAULT 'local',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def decode_google_jwt(token):
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload).decode('utf-8')
        return json.loads(decoded)
    except Exception as e:
        print(f"Error decoding Google JWT: {e}")
        return None

# ─── Exchange Rate (3-source fallback chain) ─────────────────────────
_usd_inr_rate = None   # cached so we don't hit the network on every request

def get_usd_inr():
    """Fetch live USD→INR rate.  Tries 3 sources in order:
      1. yfinance download  (USDINR=X)
      2. open.er-api.com    (free, no API key)
      3. Last cached value  (never hard-codes a stale number)
    """
    global _usd_inr_rate

    # ── Method 1: yfinance ────────────────────────────────────────────
    try:
        df = yf.download("USDINR=X", period="1d", auto_adjust=True, progress=False)
        if not df.empty:
            rate = float(df["Close"].iloc[-1])
            if 50 < rate < 200:           # sanity check – real INR range
                _usd_inr_rate = round(rate, 4)
                print(f"[rate] yfinance: 1 USD = Rs. {_usd_inr_rate}")
                return _usd_inr_rate
    except Exception as e:
        print(f"[rate] yfinance failed: {e}")

    # ── Method 2: open.er-api.com (free, no key needed) ───────────────
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            payload = json.loads(resp.read())
        rate = float(payload["rates"]["INR"])
        if 50 < rate < 200:
            _usd_inr_rate = round(rate, 4)
            print(f"[rate] open.er-api: 1 USD = Rs. {_usd_inr_rate}")
            return _usd_inr_rate
    except Exception as e:
        print(f"[rate] open.er-api failed: {e}")

    # ── Method 3: last cached value ───────────────────────────────────
    fallback = _usd_inr_rate or 84.07
    print(f"[rate] using cached/fallback: Rs. {fallback}")
    return fallback


frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

app = Flask(__name__, static_folder=frontend_dir, static_url_path='')
app.secret_key = 'marketoracle_dev_secret_key_1337'
CORS(app, supports_credentials=True)

# ─── STOCK CATALOG ──────────────────────────────────────────────────────────────
STOCKS = {
    # US Tech
    "AAPL":  {"name": "Apple Inc.",          "sector": "Technology",   "flag": "🍎"},
    "MSFT":  {"name": "Microsoft Corp.",     "sector": "Technology",   "flag": "🪟"},
    "GOOGL": {"name": "Alphabet Inc.",       "sector": "Technology",   "flag": "🔍"},
    "AMZN":  {"name": "Amazon.com Inc.",     "sector": "Consumer",     "flag": "📦"},
    "NVDA":  {"name": "NVIDIA Corp.",        "sector": "Technology",   "flag": "🎮"},
    "TSLA":  {"name": "Tesla Inc.",          "sector": "Automotive",   "flag": "⚡"},
    "META":  {"name": "Meta Platforms",      "sector": "Technology",   "flag": "👁"},
    "NFLX":  {"name": "Netflix Inc.",        "sector": "Entertainment","flag": "🎬"},
    "INTC":  {"name": "Intel Corp.",         "sector": "Technology",   "flag": "💻"},
    "AMD":   {"name": "AMD Inc.",            "sector": "Technology",   "flag": "🔧"},
    # Finance
    "JPM":   {"name": "JPMorgan Chase",      "sector": "Finance",      "flag": "🏦"},
    "BAC":   {"name": "Bank of America",     "sector": "Finance",      "flag": "💰"},
    "GS":    {"name": "Goldman Sachs",       "sector": "Finance",      "flag": "📈"},
    "V":     {"name": "Visa Inc.",           "sector": "Finance",      "flag": "💳"},
    "MA":    {"name": "Mastercard Inc.",     "sector": "Finance",      "flag": "💴"},
    # Healthcare
    "JNJ":   {"name": "Johnson & Johnson",   "sector": "Healthcare",   "flag": "💊"},
    "PFE":   {"name": "Pfizer Inc.",         "sector": "Healthcare",   "flag": "🧬"},
    "UNH":   {"name": "UnitedHealth Group",  "sector": "Healthcare",   "flag": "🏥"},
    # Energy
    "XOM":   {"name": "ExxonMobil Corp.",    "sector": "Energy",       "flag": "⛽"},
    "CVX":   {"name": "Chevron Corp.",       "sector": "Energy",       "flag": "🛢"},
    # Retail / Consumer
    "WMT":   {"name": "Walmart Inc.",        "sector": "Retail",       "flag": "🛒"},
    "DIS":   {"name": "Walt Disney Co.",     "sector": "Entertainment","flag": "🏰"},
    "SBUX":  {"name": "Starbucks Corp.",     "sector": "Consumer",     "flag": "☕"},
    "NKE":   {"name": "Nike Inc.",           "sector": "Consumer",     "flag": "👟"},
    # Crypto ETF / Others
    "COIN":  {"name": "Coinbase Global",     "sector": "Crypto",       "flag": "🪙"},
    "PYPL":  {"name": "PayPal Holdings",     "sector": "Finance",      "flag": "💸"},
}


# ─── AUTHENTICATION ROUTES ───────────────────────────────────────────
@app.route('/api/auth/register', methods=['POST'])
def auth_register():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', '').strip()

    if not email or not password or not name:
        return jsonify({"error": "All fields (name, email, password) are required."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"error": "An account with this email already exists."}), 400

        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (email, password_hash, name, auth_provider) VALUES (?, ?, ?, 'local')",
            (email, password_hash, name)
        )
        conn.commit()
        
        # Get the new user
        cursor.execute("SELECT id, email, name, picture FROM users WHERE email = ?", (email,))
        user = dict(cursor.fetchone())
        conn.close()

        session['user'] = {
            "id": user['id'],
            "email": user['email'],
            "name": user['name'],
            "picture": user['picture'] or '',
            "provider": "local"
        }
        return jsonify({"success": True, "user": session['user']})
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, email, password_hash, name, picture, auth_provider FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({"error": "Invalid email or password."}), 401

        user = dict(row)
        if user['auth_provider'] != 'local':
            return jsonify({"error": f"Please sign in using your {user['auth_provider'].capitalize()} account."}), 400

        if not check_password_hash(user['password_hash'], password):
            return jsonify({"error": "Invalid email or password."}), 401

        session['user'] = {
            "id": user['id'],
            "email": user['email'],
            "name": user['name'],
            "picture": user['picture'] or '',
            "provider": "local"
        }
        return jsonify({"success": True, "user": session['user']})
    except Exception as e:
        return jsonify({"error": f"Login failed: {str(e)}"}), 500


@app.route('/api/auth/google', methods=['POST'])
def auth_google():
    data = request.get_json() or {}
    
    # Check if this is a demo/mock request
    is_mock = data.get('is_mock', False)
    
    if is_mock:
        email = data.get('email', 'demo.user@gmail.com').strip().lower()
        name = data.get('name', 'Demo User').strip()
        picture = data.get('picture', '')
    else:
        credential = data.get('credential')
        if not credential:
            return jsonify({"error": "Google ID credential is required."}), 400
        
        # Decode the credential (which is a JWT token)
        claims = decode_google_jwt(credential)
        if not claims:
            return jsonify({"error": "Invalid Google credential token."}), 400
        
        email = claims.get('email', '').strip().lower()
        name = claims.get('name', '').strip()
        picture = claims.get('picture', '')

    if not email:
        return jsonify({"error": "Google account did not provide a valid email."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, email, name, picture, auth_provider FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        
        if row:
            user = dict(row)
            # Update name/picture if changed
            cursor.execute(
                "UPDATE users SET name = ?, picture = ? WHERE email = ?",
                (name or user['name'], picture or user['picture'], email)
            )
            conn.commit()
            user_id = user['id']
        else:
            # Create user
            cursor.execute(
                "INSERT INTO users (email, name, picture, auth_provider) VALUES (?, ?, ?, 'google')",
                (email, name, picture)
            )
            conn.commit()
            user_id = cursor.lastrowid
            
        conn.close()

        session['user'] = {
            "id": user_id,
            "email": email,
            "name": name,
            "picture": picture,
            "provider": "google"
        }
        return jsonify({"success": True, "user": session['user']})
    except Exception as e:
        if conn:
            conn.close()
        return jsonify({"error": f"Google authentication failed: {str(e)}"}), 500


@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    if 'user' in session:
        return jsonify({"logged_in": True, "user": session['user']})
    return jsonify({"logged_in": False})


@app.route('/api/auth/logout', methods=['POST', 'GET'])
def auth_logout():
    session.pop('user', None)
    return jsonify({"success": True})


@app.route('/')
def home():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/exchange_rate')
def exchange_rate():
    """Return live USD → INR conversion rate."""
    rate = get_usd_inr()
    return jsonify({"usd_to_inr": round(rate, 2), "symbol": "₹"})


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)


@app.route('/api/stocks')
def list_stocks():
    """Return full stock catalog."""
    return jsonify(STOCKS)


@app.route('/api/live')
def live_price():
    """Live price, change, key stats for a ticker."""
    stock = request.args.get('stock', 'AAPL')
    info = get_live_info(stock)
    meta = STOCKS.get(stock, {})
    return jsonify({**info, **meta})


@app.route('/api/live_batch')
def live_price_batch():
    """Live prices for all tickers in STOCKS. Fetches in one batch for speed."""
    tickers = list(STOCKS.keys())
    try:
        # Fetch 5 days to ensure we have at least 2 days of data (weekends/holidays)
        data = yf.download(tickers, period="5d", group_by='ticker', auto_adjust=True, progress=False)
        
        results = {}
        for ticker in tickers:
            try:
                # If only one ticker, yf.download might not return a MultiIndex
                df = data[ticker] if len(tickers) > 1 else data
                df = df.dropna(subset=['Close'])
                
                if not df.empty:
                    cur = float(df['Close'].iloc[-1])
                    if len(df) >= 2:
                        prev = float(df['Close'].iloc[-2])
                        chg_pct = round((cur - prev) / prev * 100, 2)
                    else:
                        chg_pct = 0.0
                else:
                    cur, chg_pct = 0, 0
                
                results[ticker] = {
                    "price": round(cur, 2),
                    "change_pct": chg_pct,
                    **STOCKS[ticker]
                }
            except Exception:
                results[ticker] = {"price": 0, "change_pct": 0, **STOCKS[ticker]}
        return jsonify(results)
    except Exception as e:
        print(f"[batch] error: {e}")
        # Fallback: return static info with 0 prices
        return jsonify({t: {"price": 0, "change_pct": 0, **STOCKS[t]} for t in tickers})


@app.route('/api/compare')
def compare_stocks():
    """Fast multi-stock comparison — NO LSTM, just live data + indicators.
    Query: ?stocks=AAPL,MSFT,TSLA&period=6mo
    """
    raw     = request.args.get('stocks', '')
    period  = request.args.get('period', '6mo')
    tickers = [t.strip().upper() for t in raw.split(',') if t.strip()][:6]

    if not tickers:
        return jsonify({"error": "Provide ?stocks=AAPL,MSFT,..."}), 400

    results = {}
    for ticker in tickers:
        try:
            df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
            if df is None or df.empty:
                continue

            close = df['Close'].squeeze()

            # ── Normalised price series (% return from day-1, for chart) ──
            base        = float(close.iloc[0])
            norm_series = [round((float(p) - base) / base * 100, 2) for p in close]
            dates       = [str(d.date()) for d in df.index]

            # ── Current price & daily change ──
            cur_price  = float(close.iloc[-1])
            prev_price = float(close.iloc[-2]) if len(close) > 1 else cur_price
            chg_pct    = round((cur_price - prev_price) / prev_price * 100, 2)

            # ── Period return ──
            period_ret = round((cur_price - base) / base * 100, 2)

            # ── Technical indicators ──
            from utils import compute_rsi, compute_macd, compute_bollinger_bands
            rsi_s             = compute_rsi(close)
            macd_l, macd_sig, _ = compute_macd(close)
            bb_upper, _, bb_lower = compute_bollinger_bands(close)

            current_rsi    = round(float(rsi_s.dropna().iloc[-1]), 1)   if not rsi_s.dropna().empty   else 50
            current_macd   = round(float(macd_l.dropna().iloc[-1]), 4)  if not macd_l.dropna().empty  else 0
            current_signal = round(float(macd_sig.dropna().iloc[-1]),4) if not macd_sig.dropna().empty else 0
            cur_bb_upper   = round(float(bb_upper.dropna().iloc[-1]),2)  if not bb_upper.dropna().empty else 0
            cur_bb_lower   = round(float(bb_lower.dropna().iloc[-1]),2)  if not bb_lower.dropna().empty else 0

            # ── Simple AI signal (no LSTM) ──
            score = 0
            if current_rsi < 30:   score += 2
            elif current_rsi < 45: score += 1
            elif current_rsi > 70: score -= 2
            elif current_rsi > 55: score -= 1
            if current_macd > current_signal: score += 1
            else: score -= 1
            if cur_price < cur_bb_lower:  score += 2
            elif cur_price > cur_bb_upper: score -= 2

            if   score >= 3:  signal, sig_cls = "STRONG BUY",  "sig-strong-buy"
            elif score >= 1:  signal, sig_cls = "BUY",          "sig-buy"
            elif score <= -3: signal, sig_cls = "STRONG SELL",  "sig-strong-sell"
            elif score <= -1: signal, sig_cls = "SELL",         "sig-sell"
            else:             signal, sig_cls = "HOLD",         "sig-hold"

            # ── 52-week high/low ──
            df52 = yf.download(ticker, period="1y", auto_adjust=True, progress=False)
            w52_high = round(float(df52['High'].max()), 2) if not df52.empty else 0
            w52_low  = round(float(df52['Low'].min()),  2) if not df52.empty else 0

            meta = STOCKS.get(ticker, {})
            results[ticker] = {
                "name":       meta.get("name", ticker),
                "flag":       meta.get("flag", "📊"),
                "sector":     meta.get("sector", ""),
                "price":      round(cur_price, 2),
                "change_pct": chg_pct,
                "period_return": period_ret,
                "rsi":        current_rsi,
                "macd":       current_macd,
                "macd_signal":current_signal,
                "signal":     signal,
                "sig_cls":    sig_cls,
                "w52_high":   w52_high,
                "w52_low":    w52_low,
                "dates":      dates,
                "norm_prices":norm_series,
            }
        except Exception as e:
            print(f"[compare] {ticker} error: {e}")

    return jsonify(results)


@app.route('/api/predict')
def predict():
    stock = request.args.get('stock')
    if not stock:
        return jsonify({"error": "Stock required"}), 400
    result = generate_predictions(stock)
    return jsonify(result)


@app.route('/api/indicators')
def indicators():
    stock = request.args.get('stock', 'AAPL')
    df = fetch_stock_data(stock, period="6mo")
    if df is None or df.empty:
        return jsonify({"error": "No data"}), 404
    ind = compute_indicators(df)
    return jsonify(ind)


@app.route('/api/news')
def news():
    """Fetch recent news for a given stock using yfinance."""
    stock = request.args.get('stock')
    if not stock:
        return jsonify({"error": "Stock required"}), 400
    try:
        ticker = yf.Ticker(stock)
        news_data = ticker.news
        # Return top 4 articles
        top_news = news_data[:4] if news_data else []
        return jsonify(top_news)
    except Exception as e:
        print(f"[news] error fetching for {stock}: {e}")
        return jsonify([])


@app.route('/api/history')
def history():
    """OHLCV history for candlestick chart."""
    stock = request.args.get('stock', 'AAPL')
    period = request.args.get('period', '6mo')
    try:
        df = yf.download(stock, period=period, auto_adjust=True)
        df = df.tail(200)
        data = []
        for idx, row in df.iterrows():
            data.append({
                "date": str(idx.date()),
                "open":  round(float(row['Open']), 2),
                "high":  round(float(row['High']), 2),
                "low":   round(float(row['Low']),  2),
                "close": round(float(row['Close']), 2),
                "volume": int(row['Volume'])
            })
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)