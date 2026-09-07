const API_BASE = import.meta.env.VITE_API_URL || "/api";

function getToken() {
  return localStorage.getItem("token");
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    if (
      response.status === 401 &&
      (data.error === "Token inválido" || data.error === "Token expirado")
    ) {
      localStorage.removeItem("token");
    }
    throw new Error(data.error || "Error en la solicitud");
  }

  return data;
}

function uploadFormData(path, formData, { onUploadProgress } = {}) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}${path}`);

    const token = getToken();
    if (token) {
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    }

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onUploadProgress) {
        onUploadProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      let data = {};
      try {
        data = JSON.parse(xhr.responseText || "{}");
      } catch {
        reject(new Error("Respuesta inválida del servidor"));
        return;
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data);
        return;
      }

      if (
        xhr.status === 401 &&
        (data.error === "Token inválido" || data.error === "Token expirado")
      ) {
        localStorage.removeItem("token");
      }
      reject(new Error(data.error || "Error en la solicitud"));
    };

    xhr.onerror = () => reject(new Error("Error de red al subir el archivo"));
    xhr.send(formData);
  });
}

async function uploadFilesSequential(path, files, onProgress) {
  const allResults = [];
  const total = files.length;

  for (let index = 0; index < total; index += 1) {
    const file = files[index];
    const formData = new FormData();
    formData.append("files", file);

    onProgress?.({
      current: index + 1,
      total,
      filename: file.name,
      percent: Math.round((index / total) * 100),
      status: "uploading",
    });

    const data = await uploadFormData(path, formData, {
      onUploadProgress: (filePercent) => {
        if (filePercent >= 100) {
          onProgress?.({
            current: index + 1,
            total,
            filename: file.name,
            percent: Math.round(((index + 0.85) / total) * 100),
            status: "processing",
          });
          return;
        }

        const uploadShare = 0.7;
        const overall = Math.round(
          ((index + (filePercent / 100) * uploadShare) / total) * 100,
        );
        onProgress?.({
          current: index + 1,
          total,
          filename: file.name,
          percent: overall,
          status: "uploading",
        });
      },
    });

    allResults.push(...(data.results || []));

    onProgress?.({
      current: index + 1,
      total,
      filename: file.name,
      percent: Math.round(((index + 1) / total) * 100),
      status: "done",
    });
  }

  return { results: allResults };
}

export const api = {
  login: (email, password) =>
    request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  register: (payload) =>
    request("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getSecurityQuestions: () => request("/auth/security-questions"),

  forgotPasswordLookup: (email) =>
    request("/auth/forgot-password/lookup", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  forgotPasswordReset: (payload) =>
    request("/auth/forgot-password/reset", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  me: () => request("/auth/me"),

  getMySubjects: () => request("/subjects/mine"),

  createSubject: (name, description, llmModel = "") =>
    request("/subjects/", {
      method: "POST",
      body: JSON.stringify({
        name,
        description,
        llm_model: llmModel || undefined,
      }),
    }),

  updateSubject: (subjectId, payload) =>
    request(`/subjects/${subjectId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  deleteSubject: (subjectId) =>
    request(`/subjects/${subjectId}`, { method: "DELETE" }),

  getSubjectTeachers: (subjectId) => request(`/subjects/${subjectId}/teachers`),

  addSubjectTeacher: (subjectId, email) =>
    request(`/subjects/${subjectId}/teachers`, {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  removeSubjectTeacher: (subjectId, teacherId) =>
    request(`/subjects/${subjectId}/teachers/${teacherId}`, {
      method: "DELETE",
    }),

  getOllamaModels: () => request("/models/"),

  getAllSubjects: () => request("/subjects/"),

  getEnrollments: () => request("/subjects/enrollments"),

  enroll: (subjectId) =>
    request(`/subjects/${subjectId}/enroll`, { method: "POST" }),

  getDocuments: (subjectId) => request(`/subjects/${subjectId}/documents`),

  uploadDocuments: (subjectId, files, onProgress) =>
    uploadFilesSequential(`/subjects/${subjectId}/documents`, files, onProgress),

  deleteSubjectDocument: (documentId) =>
    request(`/subjects/documents/${documentId}`, { method: "DELETE" }),

  generateQuestion: (subjectId) =>
    request("/practice/question", {
      method: "POST",
      body: JSON.stringify({ subject_id: subjectId }),
    }),

  evaluateAnswer: (payload) =>
    request("/practice/evaluate", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  createEvaluation: (payload) =>
    request("/evaluations/", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getEvaluations: (subjectId) =>
    request(`/evaluations/?subject_id=${subjectId}`),

  updateEvaluation: (evaluationId, payload) =>
    request(`/evaluations/${evaluationId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  deleteEvaluation: (evaluationId) =>
    request(`/evaluations/${evaluationId}`, { method: "DELETE" }),

  getAvailableEvaluations: () => request("/evaluations/available"),

  startEvaluation: (evaluationId) =>
    request(`/evaluations/${evaluationId}/start`, { method: "POST" }),

  submitEvaluation: (attemptId, answers) =>
    request(`/evaluations/attempts/${attemptId}/submit`, {
      method: "POST",
      body: JSON.stringify({ answers }),
    }),

  downloadAttemptPdf: async (attemptId) => {
    const token = getToken();
    const response = await fetch(
      `${API_BASE}/evaluations/attempts/${attemptId}/pdf`,
      { headers: { Authorization: `Bearer ${token}` } },
    );

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || "Error al descargar el PDF");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `evaluacion_${attemptId}_resultados.pdf`;
    link.click();
    window.URL.revokeObjectURL(url);
  },

  createLab: (payload) =>
    request("/labs/", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getLabs: (subjectId) => request(`/labs/?subject_id=${subjectId}`),

  getLabDocuments: (labId) => request(`/labs/${labId}/documents`),

  uploadLabDocuments: (labId, files, onProgress) =>
    uploadFilesSequential(`/labs/${labId}/documents`, files, onProgress),

  deleteLabDocument: (documentId) =>
    request(`/labs/documents/${documentId}`, { method: "DELETE" }),

  getLabSessions: (labId) => request(`/labs/${labId}/sessions`),

  getLabSession: (sessionId) => request(`/labs/sessions/${sessionId}`),

  getAvailableLabs: () => request("/labs/available"),

  startLab: (labId) => request(`/labs/${labId}/start`, { method: "POST" }),

  sendLabMessage: (sessionId, message) =>
    request(`/labs/sessions/${sessionId}/chat`, {
      method: "POST",
      body: JSON.stringify({ message }),
    }),

  completeLab: (sessionId) =>
    request(`/labs/sessions/${sessionId}/complete`, { method: "POST" }),

  downloadLabChatPdf: async (sessionId) => {
    const token = getToken();
    const response = await fetch(
      `${API_BASE}/labs/sessions/${sessionId}/pdf`,
      { headers: { Authorization: `Bearer ${token}` } },
    );

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || "Error al descargar el PDF");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `lab_${sessionId}_chat.pdf`;
    link.click();
    window.URL.revokeObjectURL(url);
  },

  uploadLabEvidence: (sessionId, files, note = "") => {
    const formData = new FormData();
    for (const file of files) {
      formData.append("files", file);
    }
    if (note) {
      formData.append("note", note);
    }
    return request(`/labs/sessions/${sessionId}/evidence`, {
      method: "POST",
      body: formData,
    });
  },

  downloadLabEvidence: async (sessionId, evidenceId, filename) => {
    const token = getToken();
    const response = await fetch(
      `${API_BASE}/labs/sessions/${sessionId}/evidence/${evidenceId}/download`,
      { headers: { Authorization: `Bearer ${token}` } },
    );

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || "Error al descargar la evidencia");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename || `evidencia_${evidenceId}`;
    link.click();
    window.URL.revokeObjectURL(url);
  },

  getSubjectMetrics: (subjectId) => request(`/metrics/subjects/${subjectId}`),

  getConversationPdfs: (subjectId) =>
    request(`/wordclouds/subjects/${subjectId}/pdfs`),

  uploadConversationPdfs: (subjectId, files, onProgress) =>
    uploadFilesSequential(`/wordclouds/subjects/${subjectId}/pdfs`, files, onProgress),

  deleteConversationPdf: (pdfId) =>
    request(`/wordclouds/pdfs/${pdfId}`, { method: "DELETE" }),

  generateWordCloud: (subjectId, pdfIds) =>
    request(`/wordclouds/subjects/${subjectId}/generate`, {
      method: "POST",
      body: JSON.stringify({ pdf_ids: pdfIds }),
    }),
};
