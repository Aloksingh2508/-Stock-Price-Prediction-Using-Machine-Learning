import numpy as np
from sklearn.metrics import mean_squared_error
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from utils import (
    fetch_stock_data,
    preprocess_data,
    compute_indicators,
    generate_ai_suggestion
)
import pandas as pd

def generate_predictions(ticker):
    df = fetch_stock_data(ticker)

    if df is None or df.empty:
        return {"error": "No data available for this ticker"}

    # Keep at most 500 rows for speed during demo
    df_model = df.tail(500).copy()

    X, y, scaler, scaled_data = preprocess_data(df_model)

    # --- Build improved LSTM model ---
    model = Sequential([
        LSTM(128, return_sequences=True, input_shape=(X.shape[1], 1)),
        Dropout(0.2),
        LSTM(64, return_sequences=False),
        Dropout(0.2),
        Dense(32, activation='relu'),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='huber')

    early_stop = EarlyStopping(monitor='loss', patience=3, restore_best_weights=True)
    model.fit(X, y, epochs=15, batch_size=32, verbose=0, callbacks=[early_stop])

    predictions = model.predict(X, verbose=0)
    predictions_inv = scaler.inverse_transform(predictions)
    actual_inv = scaler.inverse_transform(y.reshape(-1, 1))

    # RMSE & confidence
    rmse = float(np.sqrt(mean_squared_error(actual_inv, predictions_inv)))
    mean_price = float(np.mean(actual_inv))
    confidence_score = max(10, min(98, int(100 - (rmse / mean_price) * 100)))

    # Future 7-day predictions
    last_seq = scaled_data[-60:].reshape(1, 60, 1)
    future_preds = []
    current_seq = last_seq.copy()
    for _ in range(7):
        next_pred = model.predict(current_seq, verbose=0)[0, 0]
        future_preds.append(next_pred)
        current_seq = np.roll(current_seq, -1, axis=1)
        current_seq[0, -1, 0] = next_pred

    future_inv = scaler.inverse_transform(np.array(future_preds).reshape(-1, 1)).flatten().tolist()

    # Dates
    dates = df_model.index[-len(actual_inv):]
    date_strings = [str(d.date()) for d in dates]

    # Indicators
    indicators = compute_indicators(df_model)

    # AI suggestion
    rsi_val = indicators.get("current_rsi", 50)
    macd_val = indicators.get("current_macd", 0)
    signal_val = indicators.get("current_signal", 0)
    bb_upper = indicators.get("current_bb_upper", 0)
    bb_lower = indicators.get("current_bb_lower", 0)
    close_arr = actual_inv.flatten()
    predicted_next = float(future_inv[0]) if future_inv else float(close_arr[-1])

    ai_suggestion = generate_ai_suggestion(
        close_arr, rsi_val, macd_val, signal_val,
        bb_upper, bb_lower, predicted_next
    )

    return {
        "dates": date_strings,
        "actual": actual_inv.flatten().tolist(),
        "predicted": predictions_inv.flatten().tolist(),
        "future_dates": [f"Day +{i+1}" for i in range(7)],
        "future_predicted": future_inv,
        "rmse": round(rmse, 4),
        "confidence_score": confidence_score,
        "trading_signal": ai_suggestion["action"],
        "ai_suggestion": ai_suggestion,
        "indicators": indicators
    }