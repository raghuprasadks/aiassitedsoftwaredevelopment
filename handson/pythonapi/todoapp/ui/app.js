"use strict";

const API_URL = "http://127.0.0.1:5003/todos";
const PAGE_SIZE = 8;

const elements = {
  addButton: document.getElementById("add-todo-button"),
  allCount: document.getElementById("all-filter-count"),
  completedCount: document.getElementById("completed-count"),
  completedField: document.getElementById("completed-field"),
  completedInput: document.getElementById("todo-completed"),
  dialog: document.getElementById("todo-dialog"),
  dialogTitle: document.getElementById("dialog-title"),
  feedback: document.getElementById("feedback"),
  form: document.getElementById("todo-form"),
  formError: document.getElementById("form-error"),
  list: document.getElementById("todo-list"),
  listCaption: document.getElementById("list-caption"),
  loading: document.getElementById("loading-state"),
  nextPage: document.getElementById("next-page"),
  pageIndicator: document.getElementById("page-indicator"),
  pageSummary: document.getElementById("page-summary"),
  pendingCount: document.getElementById("pending-count"),
  previousPage: document.getElementById("previous-page"),
  saveButton: document.getElementById("save-todo-button"),
  search: document.getElementById("search-input"),
  sort: document.getElementById("sort-select"),
  titleInput: document.getElementById("todo-title"),
  totalCount: document.getElementById("total-count"),
  userInput: document.getElementById("todo-user"),
};

let todos = [];
let currentFilter = "all";
let currentPage = 1;
let feedbackTimeout;

function request(method, url, data) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open(method, url, true);
    xhr.timeout = 15000;
    if (data !== undefined) {
      xhr.setRequestHeader("Content-Type", "application/json");
    }

    xhr.onload = () => {
      let response;
      try {
        response = xhr.responseText ? JSON.parse(xhr.responseText) : null;
      } catch {
        reject(new Error("The server returned an invalid response."));
        return;
      }

      if (xhr.status < 200 || xhr.status >= 300) {
        reject(new Error(response?.error || `Request failed (HTTP ${xhr.status}).`));
        return;
      }
      resolve(response);
    };

    xhr.onerror = () => reject(new Error("Could not connect to the todo API."));
    xhr.ontimeout = () => reject(new Error("The request timed out. Please try again."));
    xhr.send(data === undefined ? null : JSON.stringify(data));
  });
}

function showFeedback(message, isError = false) {
  window.clearTimeout(feedbackTimeout);
  elements.feedback.textContent = message;
  elements.feedback.className = `feedback visible${isError ? " error" : ""}`;
  if (!isError) {
    feedbackTimeout = window.setTimeout(() => {
      elements.feedback.className = "feedback";
      elements.feedback.textContent = "";
    }, 3500);
  }
}

function showLoading(isLoading) {
  elements.loading.classList.toggle("visible", isLoading);
}

function updateSummary() {
  const completed = todos.filter((todo) => todo.completed).length;
  elements.totalCount.textContent = todos.length;
  elements.completedCount.textContent = completed;
  elements.pendingCount.textContent = todos.length - completed;
  elements.allCount.textContent = todos.length;
  elements.listCaption.textContent = `${todos.length} ${todos.length === 1 ? "task" : "tasks"} in your workspace`;
}

async function loadTodos() {
  showLoading(true);
  elements.list.replaceChildren();
  elements.pageSummary.textContent = "—";

  try {
    const response = await request("GET", API_URL);
    if (!response || !Array.isArray(response.todos) || !response.todos.every(isTodo)) {
      throw new Error("The server returned an unexpected todo list.");
    }

    todos = response.todos;
    currentPage = 1;
    updateSummary();
    renderTodos();
  } catch (error) {
    elements.list.replaceChildren();
    showFeedback(error.message, true);
  } finally {
    showLoading(false);
  }
}

function isTodo(todo) {
  return todo !== null
    && typeof todo === "object"
    && Number.isInteger(todo.id)
    && Number.isInteger(todo.userId)
    && typeof todo.title === "string"
    && typeof todo.completed === "boolean";
}

function getVisibleTodos() {
  const query = elements.search.value.trim().toLocaleLowerCase();
  const visible = todos.filter((todo) => {
    const matchesStatus = currentFilter === "all"
      || (currentFilter === "completed" ? todo.completed : !todo.completed);
    const matchesText = !query
      || todo.title.toLocaleLowerCase().includes(query)
      || String(todo.id).includes(query)
      || String(todo.userId).includes(query);
    return matchesStatus && matchesText;
  });

  const sortBy = elements.sort.value;
  visible.sort((first, second) => {
    if (sortBy === "id-desc") return second.id - first.id;
    if (sortBy === "title-asc") return first.title.localeCompare(second.title);
    if (sortBy === "title-desc") return second.title.localeCompare(first.title);
    return first.id - second.id;
  });
  return visible;
}

function renderTodos() {
  const visibleTodos = getVisibleTodos();
  const pageCount = Math.max(1, Math.ceil(visibleTodos.length / PAGE_SIZE));
  currentPage = Math.min(currentPage, pageCount);
  const start = (currentPage - 1) * PAGE_SIZE;
  const pageTodos = visibleTodos.slice(start, start + PAGE_SIZE);
  elements.list.replaceChildren();

  if (pageTodos.length === 0) {
    const empty = document.createElement("li");
    empty.className = "empty-state";
    const heading = document.createElement("strong");
    heading.textContent = todos.length ? "No tasks found" : "Your list is clear";
    const description = document.createElement("span");
    description.textContent = todos.length
      ? "Try a different search or filter."
      : "Create a task to get started.";
    empty.append(heading, description);
    elements.list.append(empty);
  } else {
    pageTodos.forEach((todo) => elements.list.append(createTodoRow(todo)));
  }

  elements.pageSummary.textContent = visibleTodos.length
    ? `Showing ${start + 1}–${Math.min(start + PAGE_SIZE, visibleTodos.length)} of ${visibleTodos.length} tasks`
    : "Showing 0 tasks";
  elements.pageIndicator.textContent = `${currentPage} / ${pageCount}`;
  elements.previousPage.disabled = currentPage <= 1;
  elements.nextPage.disabled = currentPage >= pageCount;
}

function createTodoRow(todo) {
  const row = document.createElement("li");
  row.className = `todo-row${todo.completed ? " is-completed" : ""}`;

  const checkbox = document.createElement("input");
  checkbox.className = "todo-check";
  checkbox.type = "checkbox";
  checkbox.checked = todo.completed;
  checkbox.setAttribute("aria-label", `Mark "${todo.title}" ${todo.completed ? "to do" : "completed"}`);
  checkbox.addEventListener("change", () => toggleTodo(todo, checkbox));

  const main = document.createElement("div");
  main.className = "task-main";
  const copy = document.createElement("div");
  copy.className = "task-copy";
  const number = document.createElement("p");
  number.className = "task-number";
  number.textContent = `TASK ${String(todo.id).padStart(3, "0")}`;
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
  copy.append(number, title);
  main.append(copy, meta);

  const actions = document.createElement("div");
  actions.className = "task-actions";
  const edit = document.createElement("button");
  edit.className = "icon-action";
  edit.type = "button";
  edit.textContent = "✎";
  edit.setAttribute("aria-label", `Edit "${todo.title}"`);
  edit.addEventListener("click", () => openDialog(todo));
  const remove = document.createElement("button");
  remove.className = "icon-action delete";
  remove.type = "button";
  remove.textContent = "×";
  remove.setAttribute("aria-label", `Delete "${todo.title}"`);
  remove.addEventListener("click", () => deleteTodo(todo));
  actions.append(edit, remove);
  row.append(checkbox, main, actions);
  return row;
}

async function toggleTodo(todo, checkbox) {
  checkbox.disabled = true;
  try {
    await request("PATCH", `${API_URL}/${todo.id}`, { completed: checkbox.checked });
    await loadTodos();
    showFeedback(checkbox.checked ? "Task marked as completed." : "Task marked as to do.");
  } catch (error) {
    checkbox.checked = todo.completed;
    checkbox.disabled = false;
    showFeedback(error.message, true);
  }
}

async function deleteTodo(todo) {
  if (!window.confirm(`Delete "${todo.title}"? This can't be undone.`)) {
    return;
  }

  try {
    await request("DELETE", `${API_URL}/${todo.id}`);
    todos = todos.filter((item) => item.id !== todo.id);
    updateSummary();
    renderTodos();
    showFeedback("Task deleted.");
  } catch (error) {
    showFeedback(error.message, true);
  }
}

function openDialog(todo = null) {
  elements.form.reset();
  elements.formError.textContent = "";
  elements.form.dataset.todoId = todo ? String(todo.id) : "";
  elements.dialogTitle.textContent = todo ? "Edit task" : "Create a task";
  elements.saveButton.textContent = todo ? "Save changes" : "Create task";
  elements.completedField.hidden = !todo;
  elements.titleInput.value = todo ? todo.title : "";
  elements.userInput.value = todo ? String(todo.userId) : "1";
  elements.completedInput.checked = todo ? todo.completed : false;
  elements.dialog.showModal();
  elements.titleInput.focus();
}

async function saveTodo(event) {
  event.preventDefault();
  elements.formError.textContent = "";
  if (!elements.form.reportValidity()) {
    return;
  }

  const todoId = elements.form.dataset.todoId;
  const payload = {
    title: elements.titleInput.value.trim(),
    userId: Number(elements.userInput.value),
    completed: elements.completedInput.checked,
  };
  elements.saveButton.disabled = true;

  try {
    await request(todoId ? "PUT" : "POST", todoId ? `${API_URL}/${todoId}` : API_URL, payload);
    elements.dialog.close();
    showFeedback(todoId ? "Task updated." : "Task created.");
    await loadTodos();
  } catch (error) {
    elements.formError.textContent = error.message;
  } finally {
    elements.saveButton.disabled = false;
  }
}

document.querySelectorAll(".filter-button").forEach((button) => {
  button.addEventListener("click", () => {
    currentFilter = button.dataset.filter;
    currentPage = 1;
    document.querySelectorAll(".filter-button").forEach((filterButton) => {
      const active = filterButton === button;
      filterButton.classList.toggle("active", active);
      filterButton.setAttribute("aria-pressed", String(active));
    });
    renderTodos();
  });
});

elements.addButton.addEventListener("click", () => openDialog());
elements.form.addEventListener("submit", saveTodo);
elements.search.addEventListener("input", () => {
  currentPage = 1;
  renderTodos();
});
elements.sort.addEventListener("change", () => {
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
  if (currentPage < Math.ceil(getVisibleTodos().length / PAGE_SIZE)) {
    currentPage += 1;
    renderTodos();
  }
});
document.getElementById("close-dialog-button").addEventListener("click", () => elements.dialog.close());
document.getElementById("cancel-dialog-button").addEventListener("click", () => elements.dialog.close());
document.addEventListener("keydown", (event) => {
  if (event.key === "/" && document.activeElement !== elements.search) {
    event.preventDefault();
    elements.search.focus();
  }
  if (event.key === "Escape" && document.activeElement === elements.search) {
    elements.search.value = "";
    elements.search.blur();
    currentPage = 1;
    renderTodos();
  }
});

loadTodos();
