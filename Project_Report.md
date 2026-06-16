# Project Report: Stock Price Prediction using Machine Learning

## 1. Abstract
The stock market is known for its highly volatile and non-linear nature, making it one of the most challenging environments for predictive modeling. Predicting stock prices effectively can yield significant profits while minimizing risks. This project aims to predict the future closing prices of a specific stock (Apple Inc. - AAPL) using historical data. We implement and compare two different approaches: a traditional Machine Learning algorithm (Linear Regression) and an advanced Deep Learning algorithm (Long Short-Term Memory - LSTM). The results demonstrate that the LSTM model, designed specifically for sequential and time-series data, significantly outperforms Linear Regression in capturing market trends.

## 2. Introduction
Stock market prediction is the act of trying to determine the future value of a company's stock traded on an exchange. The successful prediction of a stock's future price could yield significant profit. With the advent of artificial intelligence and increased computational power, predictive modeling has shifted from traditional statistical methods to robust Machine Learning (ML) and Deep Learning (DL) techniques. 

In this project, we utilize Python to fetch real-time historical data from the Yahoo Finance API. We preprocess this data, extract meaningful features like Moving Averages, and train predictive models. The ultimate goal is to provide a reliable tool that can assist traders and investors in making informed decisions.

## 3. Literature Survey
Traditionally, two main approaches are used in stock market prediction:
1. **Fundamental Analysis:** Relies on a company's financial statements, health, and market position.
2. **Technical Analysis:** Relies on historical price charts and market statistics.

In recent years, Algorithmic Trading has gained popularity. Early ML approaches included Support Vector Machines (SVM) and Random Forests. While effective to a degree, these models struggle with the sequential nature of time-series data. Recently, Recurrent Neural Networks (RNN) and specifically Long Short-Term Memory (LSTM) networks have become the state-of-the-art for time-series forecasting because they can remember long-term dependencies and ignore temporary market noise.

## 4. Methodology
The project follows a standard Data Science pipeline:
1. **Data Collection:** The `yfinance` library is used to download Apple (AAPL) stock data from Jan 2015 to Jan 2024.
2. **Data Preprocessing:** Missing values (NaN) are handled. For the DL model, data is normalized using `MinMaxScaler` to fit within a 0-1 range, optimizing the neural network's learning speed.
3. **Feature Engineering:** We calculated the 50-day Moving Average (MA50), 200-day Moving Average (MA200), and the Previous Day's Close to feed into the Linear Regression model.
4. **Train-Test Split:** The dataset is split sequentially—80% of the older data is used for training the model, and the remaining 20% of the recent data is used for testing.

## 5. Implementation
### 5.1 Linear Regression Model
Linear Regression is a fundamental statistical algorithm that assumes a linear relationship between input features and the target variable. We trained this model using `sklearn.linear_model.LinearRegression`.

### 5.2 LSTM Model
LSTM is a specialized RNN capable of learning long-term dependencies.
* **Input Shape:** The data is transformed into sequences of 60 days. The model uses the past 60 days to predict the 61st day.
* **Architecture:** 
  * Two LSTM layers with 50 neurons each.
  * Dropout layers (20%) are added to prevent overfitting.
  * Dense layers compile the output into a single predicted price.
* **Compilation:** Uses the 'Adam' optimizer and Mean Squared Error (MSE) loss function.

## 6. Results
The models were evaluated visually by plotting the Predicted Prices against the Actual Prices using `matplotlib`.
* **Linear Regression:** The model identified the general upward trend of Apple's stock but failed to capture the non-linear volatility (sudden drops or spikes).
* **LSTM Model:** The LSTM model performed exceptionally well. The predicted price curve closely followed the actual price curve, successfully identifying complex patterns and shifts in momentum.

## 7. Conclusion
This project successfully demonstrates the application of Machine Learning and Deep Learning in financial markets. We conclude that traditional models like Linear Regression are too simplistic for the highly volatile stock market. Deep Learning models, specifically LSTMs, are highly capable of understanding sequence data and provide much more accurate and reliable forecasts. 

## 8. Future Scope
While the current model is robust, it can be further improved by:
1. **Sentiment Analysis:** Integrating Natural Language Processing (NLP) to analyze financial news and Twitter sentiments, as human emotion heavily drives the market.
2. **Multiple Indicators:** Adding more technical indicators like RSI (Relative Strength Index) and MACD.
3. **Web Deployment:** Creating a user-friendly UI using Flask, Django, or Streamlit where users can enter any stock ticker and get real-time predictions.
