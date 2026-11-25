import math

from flask import Flask, jsonify, request

app = Flask(__name__)


def get_operands():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, None, (jsonify(error="Request body must be a JSON object"), 400)

    number1 = data.get("number1")
    number2 = data.get("number2")
    for number in (number1, number2):
        if (
            isinstance(number, bool)
            or not isinstance(number, (int, float))
            or isinstance(number, float) and not math.isfinite(number)
        ):
            return None, None, (
                jsonify(error="number1 and number2 must be finite numbers"),
                400,
            )

    return number1, number2, None


def calculate(operation):
    number1, number2, error = get_operands()
    if error:
        return error

    if operation == "divide" and number2 == 0:
        return jsonify(error="Cannot divide by zero"), 400

    result = {
        "add": lambda: number1 + number2,
        "subtract": lambda: number1 - number2,
        "multiply": lambda: number1 * number2,
        "divide": lambda: number1 / number2,
    }[operation]()
    return jsonify(result=result)


@app.post("/add")
def add():
    return calculate("add")


@app.post("/subtract")
def subtract():
    return calculate("subtract")


@app.post("/multiply")
def multiply():
    return calculate("multiply")


@app.post("/divide")
def divide():
    return calculate("divide")


if __name__ == "__main__":
    app.run(port=5001)
