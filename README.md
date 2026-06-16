# Stock Price Prediction Web Application using LSTM

A complete full-stack machine learning project for predicting stock prices using Long Short-Term Memory (LSTM) neural networks.

## Features

- **LSTM Model:** Predicts the next 7 days of closing prices based on the last 60 days of historical data.
- **Flask Backend:** Serves RESTful APIs (`/predict`, `/live_price`) to handle model training, prediction, and data fetching.
- **Modern Frontend:** Built with HTML, CSS, and JS. Features a responsive, glassmorphism UI, Dark Mode, and Chart.js integration.
- **Live Data:** Fetches up-to-date historical and live stock data using the `yfinance` API.
- **Multiple Stocks:** Supports predictions for AAPL, GOOGL, TSLA, TCS.NS, and RELIANCE.NS.

---

## Project Structure

```
.
├── backend/
│   ├── app.py              # Flask server and API endpoints
│   ├── model.py            # LSTM model definition, training, and forecasting logic
│   ├── utils.py            # Data fetching (yfinance) and preprocessing (MinMaxScaler)
│   └── saved_models/       # Directory where trained models (.h5) are cached
├── frontend/
│   ├── index.html          # Main dashboard UI
│   ├── style.css           # Styling (CSS Variables, Flexbox, Dark Mode)
│   └── script.js           # Client-side logic and Chart.js rendering
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
└── Viva_Questions.md       # Explanations for Viva/Presentation
```

---

## Setup Instructions

### 1. Backend Setup

1. **Install Python:** Ensure you have Python 3.9+ installed.
2. **Navigate to the project folder:**
   ```bash
   cd "path/to/project"
   ```
3. **Create a Virtual Environment (Optional but recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
5. **Run the Flask App:**
   ```bash
   cd backend
   python app.py
   ```
   The backend will start running on `http://127.0.0.1:5000`.

### 2. Frontend Setup

1. The frontend consists of static files.
2. You can simply open `frontend/index.html` in any modern web browser.
3. *Alternatively*, for a better experience, run a local web server (e.g., using VS Code Live Server extension) in the `frontend/` directory.

---

## Deployment Guide (Bonus)

### Deploying the Backend on Render (or Heroku)

1. Create a `Procfile` in the root directory (or move backend files to root) and add:
   ```text
   web: gunicorn backend.app:app
   ```
2. Add `gunicorn` to your `requirements.txt`.
3. Push your code to a GitHub repository.
4. Log into [Render](https://render.com/), create a new **Web Service**, and connect your GitHub repo.
5. Set the Build Command to `pip install -r requirements.txt`.
6. Set the Start Command to `gunicorn backend.app:app`.
7. Once deployed, note the URL Render provides.

### Deploying the Frontend on Netlify

1. In your `frontend/script.js`, change the `API_URL` variable from `http://127.0.0.1:5000` to the URL provided by Render in the previous step.
2. Log into [Netlify](https://www.netlify.com/).
3. Drag and drop the `frontend/` folder into Netlify's "Deploy manually" section, OR connect your GitHub repo and select the `frontend/` folder as the publish directory.
4. Your frontend is now live and talking to your cloud backend!
