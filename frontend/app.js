const MAX_FILE_SIZE = 10 * 1024 * 1024;
const PREVIEW_LENGTH = 400;
const UPLOAD_TITLE = "Arraste seu PDF até aqui";
const RATE_LIMITED_MESSAGE = "Limite de uso da IA atingido. Aguarde um minuto e tente de novo.";
const CONNECTION_ERROR =
  "Não foi possível conectar à API. Verifique se o servidor está em execução e tente novamente.";

const fileInput = document.querySelector("#document-file");
const uploadArea = document.querySelector("#upload-area");
const uploadTitle = document.querySelector("#upload-title");
const uploadError = document.querySelector("#upload-error");
const activeDocumentPanel = document.querySelector("#active-document");
const activeName = document.querySelector("#active-name");
const activeMeta = document.querySelector("#active-meta");
const newChatButton = document.querySelector("#new-chat-button");
const chatHistory = document.querySelector("#chat-history");
const questionForm = document.querySelector("#question-form");
const questionInput = document.querySelector("#question");
const submitButton = document.querySelector("#submit-button");
const buttonLabel = document.querySelector("#button-label");
const statusMessage = document.querySelector("#status-message");

let activeDocument = null;
let isUploading = false;
let isAsking = false;

class ApiError extends Error {
  constructor(message, status, code) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function showStatus(message, isError = false) {
  statusMessage.textContent = message;
  statusMessage.classList.toggle("error", isError);
  statusMessage.hidden = false;
}

function hideStatus() {
  statusMessage.hidden = true;
}

function showUploadError(message) {
  uploadError.textContent = message;
  uploadError.hidden = false;
}

function getErrorMessage(payload, fallback) {
  if (typeof payload?.detail === "string") {
    return payload.detail;
  }

  if (payload?.detail && typeof payload.detail.message === "string") {
    return payload.detail.message;
  }

  if (Array.isArray(payload?.detail)) {
    return payload.detail.map((error) => error.msg).join(" ");
  }

  return fallback;
}

function getErrorCode(payload) {
  return typeof payload?.detail?.code === "string" ? payload.detail.code : null;
}

async function requestJson(url, options, fallbackMessage) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(
      getErrorMessage(payload, fallbackMessage),
      response.status,
      getErrorCode(payload),
    );
  }

  return payload;
}

function describeError(error) {
  if (error instanceof TypeError) {
    return CONNECTION_ERROR;
  }

  if (error.code === "RATE_LIMITED") {
    return error.message || RATE_LIMITED_MESSAGE;
  }

  return error.message;
}

function validateFile(file) {
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    throw new Error("O arquivo precisa estar no formato PDF.");
  }

  if (file.size > MAX_FILE_SIZE) {
    throw new Error("O arquivo excede o limite máximo permitido de 10 MiB.");
  }
}

function updateControls() {
  const canAsk = Boolean(activeDocument) && !isAsking;
  questionInput.disabled = !canAsk;
  submitButton.disabled = !canAsk;
  submitButton.classList.toggle("is-loading", isAsking);
  newChatButton.disabled = isAsking;
  fileInput.disabled = isUploading || Boolean(activeDocument);
  uploadArea.classList.toggle("is-busy", isUploading);
  buttonLabel.textContent = isAsking ? "Buscando resposta..." : "Perguntar";
  questionInput.placeholder = activeDocument
    ? "Ex.: Quais são os principais prazos mencionados?"
    : "Envie um PDF para começar a perguntar.";
}

function formatPages(pages) {
  return pages === 1 ? "1 página" : `${pages} páginas`;
}

function showActiveDocument(documentInfo) {
  activeName.textContent = documentInfo.filename;
  activeName.title = documentInfo.filename;
  activeMeta.textContent = `${formatPages(documentInfo.pages)} · documento ativo`;
  uploadArea.hidden = true;
  activeDocumentPanel.hidden = false;
}

function resetUploadArea() {
  fileInput.value = "";
  uploadTitle.textContent = UPLOAD_TITLE;
  uploadArea.classList.remove("has-file");
  uploadArea.hidden = false;
  activeDocumentPanel.hidden = true;
}

async function uploadFile(file) {
  if (!file || activeDocument || isUploading) {
    return;
  }

  uploadError.hidden = true;
  hideStatus();

  try {
    validateFile(file);
  } catch (error) {
    resetUploadArea();
    showUploadError(error.message);
    return;
  }

  isUploading = true;
  uploadTitle.textContent = "Analisando seu PDF...";
  uploadArea.classList.add("has-file");
  updateControls();

  try {
    const formData = new FormData();
    formData.append("file", file);
    activeDocument = await requestJson(
      "/documents/upload",
      { method: "POST", body: formData },
      "Não foi possível enviar o documento.",
    );
    showActiveDocument(activeDocument);
  } catch (error) {
    resetUploadArea();
    showUploadError(describeError(error));
  } finally {
    isUploading = false;
    updateControls();
  }

  if (activeDocument) {
    questionInput.focus();
  }
}

fileInput.addEventListener("change", () => {
  uploadFile(fileInput.files[0]);
});

for (const eventName of ["dragenter", "dragover"]) {
  uploadArea.addEventListener(eventName, (event) => {
    event.preventDefault();
    if (!isUploading) {
      uploadArea.classList.add("is-dragging");
    }
  });
}

for (const eventName of ["dragleave", "drop"]) {
  uploadArea.addEventListener(eventName, (event) => {
    event.preventDefault();
    uploadArea.classList.remove("is-dragging");
  });
}

uploadArea.addEventListener("drop", (event) => {
  uploadFile(event.dataTransfer.files[0]);
});

function createElement(tagName, className, text) {
  const element = document.createElement(tagName);
  if (className) {
    element.className = className;
  }
  if (text !== undefined) {
    element.textContent = text;
  }
  return element;
}

function previewText(text) {
  if (text.length <= PREVIEW_LENGTH) {
    return text;
  }

  const cut = text.slice(0, PREVIEW_LENGTH);
  const lastSpace = cut.lastIndexOf(" ");
  return `${(lastSpace > PREVIEW_LENGTH * 0.7 ? cut.slice(0, lastSpace) : cut).trimEnd()}…`;
}

function createToggle(label, onToggle) {
  const toggle = createElement("button", "link-button", label);
  toggle.type = "button";
  toggle.setAttribute("aria-expanded", "false");
  toggle.addEventListener("click", () => {
    const expanded = toggle.getAttribute("aria-expanded") !== "true";
    toggle.setAttribute("aria-expanded", String(expanded));
    onToggle(expanded);
  });
  return toggle;
}

function createSourceCard(source) {
  const card = createElement("article", "source-card");

  const header = createElement("p", "source-page");
  header.append(createElement("span", "source-ref", String(source.ref)), `Página ${source.page}`);
  card.append(header);

  const quote = source.quote.trim();
  const text = createElement("p", "source-text");

  if (quote) {
    card.append(createElement("blockquote", "source-quote", `“${quote}”`));
    text.textContent = source.text;
    text.hidden = true;
    const toggle = createToggle("Ver trecho completo", (expanded) => {
      text.hidden = !expanded;
      toggle.textContent = expanded ? "Ocultar trecho" : "Ver trecho completo";
    });
    card.append(text, toggle);
    return card;
  }

  const preview = previewText(source.text);
  text.textContent = preview;
  card.append(text);

  if (preview !== source.text) {
    const toggle = createToggle("Ver mais", (expanded) => {
      text.textContent = expanded ? source.text : preview;
      toggle.textContent = expanded ? "Ver menos" : "Ver mais";
    });
    card.append(toggle);
  }

  return card;
}

function renderAnswerText(container, answer) {
  for (const part of answer.split(/(\[\d+\])/)) {
    const match = part.match(/^\[(\d+)\]$/);
    if (match) {
      const ref = createElement("span", "citation-ref", match[1]);
      ref.title = `Fonte ${match[1]}`;
      container.append(ref);
    } else if (part) {
      container.append(part);
    }
  }
}

function renderAnswer(answerBlock, result) {
  answerBlock.classList.remove("is-pending");
  answerBlock.replaceChildren();

  const text = createElement("p", "answer-text");

  if (!result.found) {
    answerBlock.classList.add("is-not-found");
    text.textContent = result.answer;
    answerBlock.append(text);
    return;
  }

  renderAnswerText(text, result.answer);
  answerBlock.append(text);

  if (result.sources.length === 0) {
    return;
  }

  const sourcesSection = createElement("div", "sources-section");
  const title = createElement("h3", null, "Fontes ");
  title.append(createElement("span", null, String(result.sources.length)));
  const list = createElement("div", "sources-list");
  list.append(...result.sources.map(createSourceCard));
  sourcesSection.append(title, list);
  answerBlock.append(sourcesSection);
}

function addChatEntry(question) {
  const entry = createElement("article", "chat-entry");
  const questionBubble = createElement("p", "chat-question");
  questionBubble.append(createElement("span", "visually-hidden", "Você perguntou: "), question);

  const answerBlock = createElement("div", "chat-answer is-pending");
  answerBlock.append(createElement("p", "answer-text", "Procurando no documento..."));

  entry.append(questionBubble, answerBlock);
  chatHistory.append(entry);
  chatHistory.hidden = false;
  entry.scrollIntoView({ block: "nearest", behavior: "smooth" });
  return { entry, answerBlock };
}

questionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideStatus();

  const question = questionInput.value.trim();

  if (!activeDocument || isAsking) {
    return;
  }

  if (!question) {
    showStatus("Escreva uma pergunta antes de consultar.", true);
    questionInput.focus();
    return;
  }

  isAsking = true;
  updateControls();
  questionInput.value = "";
  const { entry, answerBlock } = addChatEntry(question);

  try {
    const result = await requestJson(
      `/documents/${encodeURIComponent(activeDocument.document_id)}/ask`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      },
      "Não foi possível consultar o documento.",
    );
    renderAnswer(answerBlock, result);
  } catch (error) {
    entry.remove();
    chatHistory.hidden = chatHistory.childElementCount === 0;
    questionInput.value = question;
    showStatus(describeError(error), true);
  } finally {
    isAsking = false;
    updateControls();
    questionInput.focus();
  }
});

questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    questionForm.requestSubmit();
  }
});

newChatButton.addEventListener("click", async () => {
  if (!activeDocument || isAsking) {
    return;
  }

  newChatButton.disabled = true;
  hideStatus();

  try {
    await requestJson(
      `/documents/${encodeURIComponent(activeDocument.document_id)}`,
      { method: "DELETE" },
      "Não foi possível encerrar a conversa.",
    );
  } catch (error) {
    if (error.status !== 404) {
      showStatus(describeError(error), true);
      newChatButton.disabled = false;
      return;
    }
  }

  activeDocument = null;
  chatHistory.replaceChildren();
  chatHistory.hidden = true;
  questionInput.value = "";
  uploadError.hidden = true;
  resetUploadArea();
  updateControls();
  fileInput.focus();
});

updateControls();
