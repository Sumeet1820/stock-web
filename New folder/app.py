from flask import Flask, request, jsonify, render_template
from analyzer import full_analyze

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/analyze")
def analyze():
    symbol = request.args.get("symbol")
    return jsonify(full_analyze(symbol))

app.run(debug=True)