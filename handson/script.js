const resultDisplay = document.getElementById("result");
const expressionDisplay = document.getElementById("expression");
const keys = document.querySelector(".keys");

let currentValue = "0";
let storedValue = null;
let pendingOperator = null;
let waitingForOperand = false;
let hasError = false;

function formatNumber(value) {
    if (!Number.isFinite(value)) {
        return "Error";
    }

    const rounded = Number(value.toPrecision(12));
    return String(Object.is(rounded, -0) ? 0 : rounded);
}

function updateDisplay() {
    resultDisplay.textContent = currentValue;
    expressionDisplay.textContent = storedValue === null
        ? ""
        : `${formatNumber(storedValue)} ${operatorSymbol(pendingOperator || "")}`;
}

function operatorSymbol(operator) {
    return { "/": "÷", "*": "×", "-": "−", "+": "+" }[operator] || "";
}

function enterDigit(digit) {
    if (hasError) {
        clearCalculator();
    }

    if (waitingForOperand) {
        currentValue = digit;
        waitingForOperand = false;
    } else if (currentValue === "0") {
        currentValue = digit;
    } else if (currentValue === "-0") {
        currentValue = `-${digit}`;
    } else if (currentValue.replace("-", "").length < 15) {
        currentValue += digit;
    }

    updateDisplay();
}

function enterDecimal() {
    if (hasError) {
        clearCalculator();
    }

    if (waitingForOperand) {
        currentValue = "0.";
        waitingForOperand = false;
    } else if (!currentValue.includes(".")) {
        currentValue += ".";
    }

    updateDisplay();
}

function calculate(left, right, operator) {
    switch (operator) {
        case "+": return left + right;
        case "-": return left - right;
        case "*": return left * right;
        case "/": return right === 0 ? NaN : left / right;
        default: return right;
    }
}

function chooseOperator(nextOperator) {
    if (hasError) {
        clearCalculator();
    }

    const inputValue = Number(currentValue);

    if (pendingOperator && !waitingForOperand) {
        const result = calculate(storedValue, inputValue, pendingOperator);
        currentValue = formatNumber(result);
        if (currentValue === "Error") {
            showError();
            return;
        }
        storedValue = Number(currentValue);
    } else if (storedValue === null || !pendingOperator) {
        storedValue = inputValue;
    }

    pendingOperator = nextOperator;
    waitingForOperand = true;
    updateDisplay();
}

function calculateResult() {
    if (hasError || pendingOperator === null || waitingForOperand) {
        return;
    }

    const rightValue = Number(currentValue);
    const result = calculate(storedValue, rightValue, pendingOperator);
    const expression = `${formatNumber(storedValue)} ${operatorSymbol(pendingOperator)} ${formatNumber(rightValue)} =`;

    currentValue = formatNumber(result);
    if (currentValue === "Error") {
        showError();
        return;
    }

    storedValue = null;
    pendingOperator = null;
    waitingForOperand = true;
    expressionDisplay.textContent = expression;
    resultDisplay.textContent = currentValue;
}

function clearCalculator() {
    currentValue = "0";
    storedValue = null;
    pendingOperator = null;
    waitingForOperand = false;
    hasError = false;
    updateDisplay();
}

function showError() {
    currentValue = "Error";
    storedValue = null;
    pendingOperator = null;
    waitingForOperand = true;
    hasError = true;
    updateDisplay();
}

function toggleSign() {
    if (hasError) {
        clearCalculator();
    }

    if (currentValue !== "0") {
        currentValue = currentValue.startsWith("-")
            ? currentValue.slice(1)
            : `-${currentValue}`;
    }

    updateDisplay();
}

function applyPercent() {
    if (hasError) {
        clearCalculator();
    }

    currentValue = formatNumber(Number(currentValue) / 100);
    updateDisplay();
}

function backspace() {
    if (hasError) {
        clearCalculator();
        return;
    }

    if (waitingForOperand) {
        return;
    }

    currentValue = currentValue.length > 1
        ? currentValue.slice(0, -1)
        : "0";
    if (currentValue === "-") {
        currentValue = "0";
    }
    updateDisplay();
}

function handleAction(action, value) {
    switch (action) {
        case "digit": enterDigit(value); break;
        case "decimal": enterDecimal(); break;
        case "operator": chooseOperator(value); break;
        case "equals": calculateResult(); break;
        case "clear": clearCalculator(); break;
        case "sign": toggleSign(); break;
        case "percent": applyPercent(); break;
        case "backspace": backspace(); break;
    }
}

keys.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (button) {
        handleAction(button.dataset.action, button.dataset.value);
    }
});

document.addEventListener("keydown", (event) => {
    if (/^\d$/.test(event.key)) {
        enterDigit(event.key);
    } else if (event.key === "." || event.key === ",") {
        enterDecimal();
    } else if (["+", "-", "*", "/"].includes(event.key)) {
        chooseOperator(event.key);
    } else if (event.key === "Enter" || event.key === "=") {
        event.preventDefault();
        calculateResult();
    } else if (event.key === "Backspace") {
        backspace();
    } else if (event.key === "Escape") {
        clearCalculator();
    } else {
        return;
    }
    event.preventDefault();
});
