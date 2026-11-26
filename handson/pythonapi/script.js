"use strict";

const API_URL = "https://jsonplaceholder.typicode.com/todos";
const PAGE_SIZE = 10;

const elements = {
  allCount: document.getElementById("all-filter-count"),
  completedCount: document.getElementById("completed-count"),
  list: document.getElementById("todo-list"),
  listCaption: document.getElementById("list-caption"),
  nextPage: document.getElementById("next-page"),
  pageIndicator: document.getElementById("page-indicator"),
  pageSummary: document.getElementById("page-summary"),
  pendingCount: document.getElementById("pending-count"),
  previousPage: document.getElementById("previous-page"),
  refreshButton: document.getElementById("refresh-button"),
  searchInput: document.getElementById("search-input"),
  sortSelect: document.getElementById("sort-select"),
  statusMessage: document.getElementById("status-message"),
  totalCount: document.getElementById("total-count"),
};

let todos = [];
let currentFilter = "all";
let currentPage = 1;
let request;

function showStatus(message, state) {
  elements.statusMessage.replaceChildren();
  elements.statusMessage.className = `status-message visible${state ? ` ${state}` : ""}`;

  if (state === "loading") {
    const spinner = document.createElement("span");
    spinner.className = "spinner";
    spinner.setAttribute("aria-hidden", "true");
    elements.statusMessage.append(spinner);
  }

  const text = document.createElement("span");
  text.textContent = message;
  elements.statusMessage.append(text);
}

function hideStatus() {
  elements.statusMessage.className = "status-message";
  elements.statusMessage.replaceChildren();
}

function loadTodos() {
  if (request) {
    request.abort();
  }

  elements.refreshButton.disabled = true;
  elements.list.replaceChildren();
  elements.pageSummary.textContent = "—";
  showStatus("Fetching your tasks…", "loading");

  request = new XMLHttpRequest();
  request.open("GET", API_URL, true);
  request.timeout = 15000;

  request.onload = function () {
    elements.refreshButton.disabled = false;

    if (request.status < 200 || request.status >= 300) {
      showStatus(`Couldn't load tasks (HTTP ${request.status}). Please try again.`, "error");
      return;
    }

    try {
      const data = JSON.parse(request.responseText);
      if (!Array.isArray(data) || !data.every(isTodo)) {
        throw new Error("The server returned an unexpected todo list.");
      }

      todos = data;
      currentPage = 1;
      updateSummary();
      renderTodos();
    } catch (error) {
      showStatus(error instanceof SyntaxError
        ? "The server returned an invalid response. Please try again."
        : error.message, "error");
    }
  };

  request.onerror = function () {
    elements.refreshButton.disabled = false;
    showStatus("Couldn't connect to the todo service. Check your connection and try again.", "error");
  };

  request.ontimeout = function () {
    elements.refreshButton.disabled = false;
    showStatus("The request took too long. Please try again.", "error");
  };

  request.onabort = function () {
    elements.refreshButton.disabled = false;
  };

  request.send();
}

function isTodo(todo) {
  return todo !== null
    && typeof todo === "object"
    && Number.isInteger(todo.id)
    && Number.isInteger(todo.userId)
    && typeof todo.title === "string"
    && typeof todo.completed === "boolean";
}

function updateSummary() {
  const completed = todos.filter((todo) => todo.completed).length;
  elements.totalCount.textContent = todos.length;
  elements.completedCount.textContent = completed;
  elements.pendingCount.textContent = todos.length - completed;
  elements.allCount.textContent = todos.length;
  elements.listCaption.textContent = `${todos.length} tasks across your workspace`;
}

function getVisibleTodos() {
  const query = elements.searchInput.value.trim().toLocaleLowerCase();
  const filtered = todos.filter((todo) => {
    const matchesStatus = currentFilter === "all"
      || (currentFilter === "completed" ? todo.completed : !todo.completed);
    const matchesSearch = !query
      || todo.title.toLocaleLowerCase().includes(query)
      || String(todo.id).includes(query)
      || String(todo.userId).includes(query);
    return matchesStatus && matchesSearch;
  });

  const sort = elements.sortSelect.value;
  filtered.sort((first, second) => {
    if (sort === "id-desc") return second.id - first.id;
    if (sort === "title-asc") return first.title.localeCompare(second.title);
    if (sort === "title-desc") return second.title.localeCompare(first.title);
    return first.id - second.id;
  });

  return filtered;
}

function renderTodos() {
  const visibleTodos = getVisibleTodos();
  const totalPages = Math.max(1, Math.ceil(visibleTodos.length / PAGE_SIZE));
  currentPage = Math.min(currentPage, totalPages);
  const start = (currentPage - 1) * PAGE_SIZE;
  const pageTodos = visibleTodos.slice(start, start + PAGE_SIZE);

  elements.list.replaceChildren();

  if (pageTodos.length === 0) {
    showStatus("No tasks match your search. Try another keyword or filter.", "empty");
    const message = document.createElement("strong");
    message.textContent = todos.length ? "No tasks found" : "Your todo list is empty";
    elements.statusMessage.prepend(message);
  } else {
    hideStatus();
    pageTodos.forEach((todo) => elements.list.append(createTodoRow(todo)));
  }

  elements.pageSummary.textContent = visibleTodos.length
    ? `Showing ${start + 1}–${Math.min(start + PAGE_SIZE, visibleTodos.length)} of ${visibleTodos.length} tasks`
    : "Showing 0 tasks";
  elements.pageIndicator.textContent = `${currentPage} / ${totalPages}`;
  elements.previousPage.disabled = currentPage <= 1;
  elements.nextPage.disabled = currentPage >= totalPages;
}

function createTodoRow(todo) {
  const item = document.createElement("li");
  item.className = `todo-row${todo.completed ? " is-completed" : ""}`;

  const number = document.createElement("span");
  number.className = "task-number";
  number.textContent = `#${String(todo.id).padStart(3, "0")}`;

  const copy = document.createElement("div");
  copy.className = "task-copy";

  const title = document.createElement("p");
  title.className = "task-title";
  title.textContent = todo.title;

  const meta = document.createElement("div");
  meta.className = "task-meta";

  const user = document.createElement("span");
  user.className = "user-label";
  user.textContent = `User ${todo.userId}`;

  const status = document.createElement("span");
  status.className = `status-pill ${todo.completed ? "completed" : "pending"}`;
  status.textContent = todo.completed ? "Completed" : "To do";

  meta.append(user, status);
  copy.append(title, meta);
  item.append(number, copy);
  return item;
}

document.querySelectorAll(".filter-button").forEach((button) => {
  button.addEventListener("click", () => {
    currentFilter = button.dataset.filter;
    currentPage = 1;

    document.querySelectorAll(".filter-button").forEach((filterButton) => {
      const isActive = filterButton === button;
      filterButton.classList.toggle("active", isActive);
      filterButton.setAttribute("aria-pressed", String(isActive));
    });

    renderTodos();
  });
});

elements.searchInput.addEventListener("input", () => {
  currentPage = 1;
  renderTodos();
});

elements.sortSelect.addEventListener("change", () => {
  currentPage = 1;
  renderTodos();
});

elements.previousPage.addEventListener("click", () => {
  if (currentPage > 1) {
    currentPage -= 1;
    renderTodos();
  }
});

elements.nextPage.addEventListener("click", () => {
  const totalPages = Math.ceil(getVisibleTodos().length / PAGE_SIZE);
  if (currentPage < totalPages) {
    currentPage += 1;
    renderTodos();
  }
});

elements.refreshButton.addEventListener("click", loadTodos);

document.addEventListener("keydown", (event) => {
  if (event.key === "/" && document.activeElement !== elements.searchInput) {
    event.preventDefault();
    elements.searchInput.focus();
  }
  if (event.key === "Escape" && document.activeElement === elements.searchInput) {
    elements.searchInput.value = "";
    elements.searchInput.blur();
    currentPage = 1;
    renderTodos();
  }
});

loadTodos();
