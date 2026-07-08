import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv()

app = Flask(__name__)
app.config["DEBUG"] = os.getenv("FLASK_DEBUG", "false").lower() == "true"


def _get_operands():
    if request.method == "GET":
        a = request.args.get("a")
        b = request.args.get("b")
    else:
        data = request.get_json(silent=True) or {}
        a = data.get("a")
        b = data.get("b")

    if a is None or b is None:
        return None, None, ("Missing required parameters 'a' and 'b'", 400)

    try:
        return float(a), float(b), None
    except (TypeError, ValueError):
        return None, None, ("Parameters 'a' and 'b' must be numbers", 400)


@app.route("/sum", methods=["GET", "POST"])
def sum_endpoint():
    a, b, error = _get_operands()
    if error:
        message, status = error
        return jsonify({"error": message}), status
    return jsonify({"a": a, "b": b, "operation": "sum", "result": a + b})


@app.route("/subtract", methods=["GET", "POST"])
def subtract_endpoint():
    a, b, error = _get_operands()
    if error:
        message, status = error
        return jsonify({"error": message}), status
    return jsonify({"a": a, "b": b, "operation": "subtract", "result": a - b})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
