const MAX_FILE_SIZE = 10 * 1024 * 1024;

const fileInput = document.querySelector("#document-file");
const uploadArea = document.querySelector("#upload-area");
const fileName = document.querySelector("#file-name");
const questionForm = document.querySelector("#question-form");
const questionInput = document.querySelector("#question");
const submitButton = document.querySelector("#submit-button");
const buttonLabel = document.querySelector("#button-label");
const statusMessage = document.querySelector("#status-message");
const answerSection = document.querySelector("#answer-section");
const answerText = document.querySelector("#answer-text");
const documentBadge = document.querySelector("#document-badge");
const sourcesSection = document.querySelector("#sources-section");
const sourceCount = document.querySelector("#source-count");
const sourcesList = document.querySelector("#sources-list");

let uploadedDocument = null;

function showStatus(message, isError = false) {
  statusMessage.textContent = message;
  statusMessage.classList.toggle("error", isError);
  statusMessage.hidden = false;
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

async function requestJson(url, options, fallbackMessage) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(getErrorMessage(payload, fallbackMessage));
  }

  return payload;
}

function validateFile(file) {
  if (!file) {
    throw new Error("Escolha um arquivo PDF para continuar.");
  }

  if (!file.name.toLowerCase().endsWith(".pdf")) {
    throw new Error("O arquivo precisa estar no formato PDF.");
  }

  if (file.size > MAX_FILE_SIZE) {
    throw new Error("O arquivo excede o limite máximo permitido de 10 MiB.");
  }
}

function setSelectedFile(file) {
  if (!file) {
    return;
  }

  try {
    validateFile(file);
    fileInput.files = createFileList(file);
    fileName.textContent = file.name;
    uploadArea.classList.add("has-file");
    uploadedDocument = null;
    answerSection.hidden = true;
    statusMessage.hidden = true;
  } catch (error) {
    fileInput.value = "";
    fileName.textContent = "Arraste seu PDF até aqui";
    uploadArea.classList.remove("has-file");
    showStatus(error.message, true);
  }
}

function createFileList(file) {
  const transfer = new DataTransfer();
  transfer.items.add(file);
  return transfer.files;
}

fileInput.addEventListener("change", () => {
  setSelectedFile(fileInput.files[0]);
});

for (const eventName of ["dragenter", "dragover"]) {
  uploadArea.addEventListener(eventName, (event) => {
    event.preventDefault();
    uploadArea.classList.add("is-dragging");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  uploadArea.addEventListener(eventName, (event) => {
    event.preventDefault();
    uploadArea.classList.remove("is-dragging");
  });
}

uploadArea.addEventListener("drop", (event) => {
  setSelectedFile(event.dataTransfer.files[0]);
});

function renderAnswer(result) {
  answerText.textContent = result.answer;
  documentBadge.textContent = uploadedDocument.filename;
  documentBadge.title = uploadedDocument.filename;
  sourcesList.replaceChildren();

  for (const source of result.sources) {
    const card = document.createElement("article");
    card.className = "source-card";

    const page = document.createElement("p");
    page.className = "source-page";
    page.textContent = `Página ${source.page}`;

    const text = document.createElement("p");
    text.className = "source-text";
    text.textContent = source.text;

    card.append(page, text);
    sourcesList.append(card);
  }

  sourceCount.textContent = String(result.sources.length);
  sourcesSection.hidden = result.sources.length === 0;
  answerSection.hidden = false;
}

questionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  statusMessage.hidden = true;
  answerSection.hidden = true;

  const question = questionInput.value.trim();

  if (!question) {
    showStatus("Escreva uma pergunta antes de consultar.", true);
    questionInput.focus();
    return;
  }

  if (!uploadedDocument) {
    try {
      validateFile(fileInput.files[0]);
    } catch (error) {
      showStatus(error.message, true);
      fileInput.focus();
      return;
    }
  }

  submitButton.disabled = true;

  try {
    if (!uploadedDocument) {
      buttonLabel.textContent = "Enviando documento...";
      showStatus("Enviando e analisando seu PDF...");

      const formData = new FormData();
      formData.append("file", fileInput.files[0]);
      uploadedDocument = await requestJson(
        "/documents/upload",
        { method: "POST", body: formData },
        "Não foi possível enviar o documento.",
      );
    }

    buttonLabel.textContent = "Buscando resposta...";
    showStatus("Documento pronto. Procurando os trechos relevantes...");
    const result = await requestJson(
      `/documents/${encodeURIComponent(uploadedDocument.document_id)}/ask`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      },
      "Não foi possível consultar o documento.",
    );

    renderAnswer(result);
    showStatus("Consulta concluída. Você pode fazer outra pergunta sobre este documento.");
  } catch (error) {
    showStatus(
      error instanceof TypeError
        ? "Não foi possível conectar à API. Verifique se o servidor está em execução e tente novamente."
        : error.message,
      true,
    );
  } finally {
    submitButton.disabled = false;
    buttonLabel.textContent = "Consultar documento";
  }
});
