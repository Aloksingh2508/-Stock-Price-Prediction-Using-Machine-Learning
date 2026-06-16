# Viva Support & Explanations

This document provides answers to common questions you might be asked during your final year project viva regarding the Stock Price Prediction system.

## 1. What is LSTM and how does it work?

**LSTM (Long Short-Term Memory)** is a specialized type of Recurrent Neural Network (RNN) designed to overcome the "vanishing gradient" problem commonly faced by standard RNNs when dealing with long sequences of data.

**How it works:**
Unlike standard neural networks that treat inputs independently, LSTMs have "memory". They use a mechanism called **gates** to control the flow of information: 
- **Forget Gate:** Decides what relevant information from previous steps to keep and what to throw away.
- **Input Gate:** Decides what new information from the current step should be added to the memory.
- **Output Gate:** Decides what the next hidden state should be, which is passed to the next time step.

These gates allow the LSTM to maintain a "cell state" (a long-term memory) over many time steps, making it excellent for time-series data.

## 2. Why use LSTM for Stock Price Prediction?

Stock prices are essentially **time-series data**. The price of a stock tomorrow is highly dependent on its price today, yesterday, and over the past few weeks (temporal dependencies).
- **Standard ANNs (Artificial Neural Networks)** cannot remember previous inputs; they treat Tuesday's price entirely independently of Monday's price.
- **Standard RNNs** can remember recent pasts but suffer from short-term memory (they forget data from 60 days ago due to vanishing gradients).
- **LSTMs** excel here because they can remember trends from 60 or 100 days ago (long-term memory) while also reacting to sudden recent changes (short-term memory).

## 3. What are the Limitations of this Model?

While impressive, predicting the stock market with pure mathematics has inherent limitations:
1. **Unpredictable External Factors:** The model only looks at historical price data. It does *not* know about news events, CEO changes, earnings reports, pandemics, or government policies.
2. **Market Volatility:** The stock market is highly stochastic (random) and heavily influenced by human emotion and algorithmic high-frequency trading.
3. **Overfitting:** Neural networks can sometimes memorize historical noise rather than learning true underlying trends, leading to poor performance on future unseen data.
4. **Assumption of Continuity:** The model assumes the future will behave statistically similarly to the past, which is often not true in financial markets.

## 4. What are potential Future Improvements?

If you were to expand this project, you could mention the following upgrades:
1. **Sentiment Analysis:** Integrate a Natural Language Processing (NLP) model to scrape Twitter (X) or financial news (like Bloomberg) and calculate a "Sentiment Score" to use as an additional input feature alongside the price.
2. **Multivariate Input:** Instead of just using the `Close` price, feed the model `Open`, `High`, `Low`, `Volume`, and technical indicators like RSI (Relative Strength Index) or MACD.
3. **Transformer Models:** Upgrade the architecture from LSTM to an Attention-based Transformer (like Time-Series Transformers), which are currently state-of-the-art for sequence data.
4. **Real-Time Retraining:** Implement an automated pipeline that retrains the model every night with the latest daily closing prices so it adapts to new market conditions dynamically.
