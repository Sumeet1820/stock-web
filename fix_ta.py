content = open('app.py', encoding='utf-8').read()
idx = content.find('def _compute_technical')

# Find end of the old header section (up to and including the first hist.empty check)
marker = "if hist is None or hist.empty: return {'error':f'{sym} ka data nahi mila'}"
end_idx = content.find(marker, idx) + len(marker)

print(f'Replacing chars {idx} to {end_idx}')
print('Old snippet:', repr(content[idx:idx+100]))

new_func_start = (
    "def _compute_technical(sym, fdata=None, mode='swing'):\n"
    "    # mode: swing=daily 1Y, positional=weekly 2Y, longterm=monthly(daily resample) 5Y\n"
    "    import math, statistics as _stats\n"
    "    if mode == 'longterm':\n"
    "        fetch_interval, fetch_period = '1d', '5y'\n"
    "    elif mode == 'positional':\n"
    "        fetch_interval, fetch_period = '1wk', '2y'\n"
    "    else:\n"
    "        fetch_interval, fetch_period = '1d', '1y'\n"
    "    try:\n"
    "        import yfinance as yf, numpy as np\n"
    "        hist = yf.download(f\"{sym}.NS\", period=fetch_period, interval=fetch_interval,\n"
    "                           auto_adjust=True, progress=False)\n"
    "        if hist is None or hist.empty:\n"
    "            hist = yf.Ticker(f\"{sym}.NS\").history(period=fetch_period, interval=fetch_interval,\n"
    "                                                   auto_adjust=True, actions=False)\n"
    "        if hist is None or hist.empty: return {'error': f'{sym} ka data nahi mila'}"
)

new_content = content[:idx] + new_func_start + content[end_idx:]
open('app.py', 'w', encoding='utf-8').write(new_content)
print('Done!')
