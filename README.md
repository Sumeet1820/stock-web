# 📈 Stock Analyzer Pro — Web Version

## Yeh kya hai?
Aapka `stock_analyzer_v32.py` (Tkinter desktop app) ab ek **website** ban gayi hai!  
Saari logic same hai — sirf UI browser mein open hoti hai.

---

## 📁 Folder Structure

```
stock_web/
├── app.py                    ← Flask backend (main file)
├── stock_analyzer_v32.py     ← Aapka original code (bilkul same, touch mat karo)
├── requirements.txt          ← Dependencies
├── templates/
│   └── index.html            ← Main HTML page
└── static/
    ├── css/
    │   └── style.css         ← Dark theme CSS
    └── js/
        └── app.js            ← Frontend JavaScript
```

---

## 🚀 Setup & Run kaise karo

### Step 1 — Dependencies install karo
```bash
pip install -r requirements.txt
```

### Step 2 — App run karo
```bash
python app.py
```

### Step 3 — Browser mein open karo
```
http://localhost:5000
```

---

## ⚠️ Important Notes

### Screener.in Cookies (ZAROORI!)
`stock_analyzer_v32.py` mein apni fresh cookies daalo:
```python
COOKIES = {
    'csrftoken': 'YOUR_CSRF_TOKEN',
    'sessionid': 'YOUR_SESSION_ID',
}
```
**Cookies kaise milti hain:**
1. Screener.in pe login karo
2. Browser DevTools kholo (F12)
3. Network tab → koi request click karo
4. Headers mein `Cookie:` field se copy karo

### Chartink Cookies
Similarly `CHARTINK_COOKIES` bhi update karo.

---

## 🌟 Features

| Feature | Status |
|---------|--------|
| Stock Search (Screener.in) | ✅ |
| NSE Live Price | ✅ |
| Fundamentals (PE, ROE, D/E etc.) | ✅ |
| Swing/Positional/LongTerm Checklist | ✅ |
| Technical Analysis (RSI, MACD, EMA, BB) | ✅ |
| Candlestick & Chart Patterns | ✅ |
| Support & Resistance | ✅ |
| Target & Stop Loss | ✅ |
| Market Gainers/Losers/Volume | ✅ |
| Chartink Screeners | ✅ |
| ETF List & Screener | ✅ |
| Watchlist | ✅ |
| Notes & Trade Tracker | ✅ |
| Price Chart (60 days) | ✅ |

---

## 🌐 Network pe share karo (Optional)

Ghar ke doosre devices pe access karna ho:
```bash
# app.py ke end mein change karo:
app.run(debug=False, host='0.0.0.0', port=5000)
```
Phir `http://YOUR_IP:5000` pe access karo.

---

*Made with ❤️ — Tkinter se Web tak*
