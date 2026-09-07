import random

from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama, OllamaEmbeddings

from auth import get_subject_by_id
from config import Config
from ollama_client import format_llm_runtime_error
from prompts import (
    CORRECCION_PROMPT,
    LAB_ASSISTANT_PROMPT,
    PREGUNTA_PROMPT,
    PREGUNTA_TEMA_PROMPT,
    SYSTEM_PROMPT,
)


def resolve_llm_model(subject_id: int | None = None, llm_model: str | None = None) -> str:
    if llm_model:
        return llm_model.strip()

    if subject_id:
        subject = get_subject_by_id(subject_id)
        if subject and subject.llm_model:
            return subject.llm_model

    return Config.DEFAULT_LLM_MODEL


class ProfesorRAG:
    _db = None
    _llm_cache: dict[str, ChatOllama] = {}

    def __init__(self, llm_model: str | None = None, subject_id: int | None = None):
        self.llm_model = resolve_llm_model(subject_id=subject_id, llm_model=llm_model)

        if ProfesorRAG._db is None:
            embedding = OllamaEmbeddings(model=Config.EMBEDDING_MODEL)
            ProfesorRAG._db = Chroma(
                persist_directory=str(Config.CHROMA_DIR),
                embedding_function=embedding,
            )

        self.db = ProfesorRAG._db
        self.llm = self._get_llm(self.llm_model)

    @classmethod
    def for_subject(cls, subject_id: int):
        return cls(subject_id=subject_id)

    @classmethod
    def _get_llm(cls, model: str) -> ChatOllama:
        if model not in cls._llm_cache:
            cls._llm_cache[model] = ChatOllama(
                model=model,
                temperature=0.4,
                base_url=Config.OLLAMA_BASE_URL,
            )
        return cls._llm_cache[model]

    def _invoke(self, prompt: str) -> str:
        try:
            response = self.llm.invoke(SYSTEM_PROMPT + "\n\n" + prompt)
            return response.content
        except Exception as exc:
            raise RuntimeError(format_llm_runtime_error(exc, self.llm_model)) from exc

    @staticmethod
    def _subject_filter(subject_id: int):
        return {"subject_id": str(subject_id)}

    @staticmethod
    def _subject_documents_filter(subject_id: int):
        return {
            "$and": [
                {"subject_id": str(subject_id)},
                {"doc_scope": "subject"},
            ],
        }

    @staticmethod
    def _is_subject_course_document(subject_id: int, metadata: dict | None) -> bool:
        if not metadata:
            return False
        if metadata.get("doc_scope") == "lab" or metadata.get("lab_id"):
            return False
        if metadata.get("subject_id") != str(subject_id):
            return False
        return metadata.get("doc_scope") in (None, "subject")

    def _filter_subject_course_documents(self, subject_id: int, docs):
        return [
            doc
            for doc in docs
            if self._is_subject_course_document(subject_id, doc.metadata)
        ]

    def _search_subject_course_documents(self, subject_id: int, query: str, k: int):
        docs = self.db.similarity_search(
            query,
            k=k,
            filter=self._subject_documents_filter(subject_id),
        )
        if docs:
            return docs

        fallback = self.db.similarity_search(
            query,
            k=max(k * 3, 15),
            filter=self._subject_filter(subject_id),
        )
        filtered = self._filter_subject_course_documents(subject_id, fallback)
        return filtered[:k]

    def subject_has_course_documents(self, subject_id: int) -> bool:
        docs = self._search_subject_course_documents(
            subject_id,
            "contenido del curso",
            k=1,
        )
        return len(docs) > 0

    @staticmethod
    def _lab_filter(subject_id: int, lab_id: int):
        return {
            "$and": [
                {"subject_id": str(subject_id)},
                {"lab_id": str(lab_id)},
            ],
        }

    def obtener_contexto(self, subject_id: int, topic: str | None = None):
        query = topic.strip() if topic else "contenido del curso"

        docs = self._search_subject_course_documents(subject_id, query, k=20)

        if not docs:
            return None

        elegido = random.choice(docs)

        return {
            "contexto": elegido.page_content,
            "fuente": elegido.metadata.get("source", "Desconocido"),
        }

    def obtener_contextos_por_tema(self, subject_id: int, topic: str, num_questions: int):
        docs = self._search_subject_course_documents(
            subject_id,
            topic,
            k=max(num_questions * 3, 15),
        )

        if not docs:
            return []

        seen = set()
        unique = []
        for doc in docs:
            key = doc.page_content[:120]
            if key not in seen:
                seen.add(key)
                unique.append(doc)

        random.shuffle(unique)
        return unique[:num_questions]

    def generar_pregunta(self, subject_id: int, topic: str | None = None):
        dato = self.obtener_contexto(subject_id, topic)

        if dato is None:
            return {
                "pregunta": None,
                "contexto": None,
                "fuente": None,
                "error": (
                    "No hay documentos procesados para esta asignatura. "
                    "Las preguntas se generan únicamente a partir de los PDFs cargados."
                ),
            }

        contexto = dato["contexto"]
        if topic:
            prompt = PREGUNTA_TEMA_PROMPT.format(contexto=contexto, tema=topic)
        else:
            prompt = PREGUNTA_PROMPT.format(contexto=contexto)

        respuesta = self._invoke(prompt)

        return {
            "pregunta": respuesta,
            "contexto": contexto,
            "fuente": dato["fuente"],
            "error": None,
        }

    def generar_preguntas(self, subject_id: int, topic: str, num_questions: int):
        if not self.subject_has_course_documents(subject_id):
            return {
                "preguntas": [],
                "error": (
                    "No hay documentos procesados para esta asignatura. "
                    "Las evaluaciones solo pueden generarse a partir de los PDFs cargados."
                ),
            }

        docs = self.obtener_contextos_por_tema(subject_id, topic, num_questions)

        if not docs:
            return {
                "preguntas": [],
                "error": (
                    f"No hay contenido sobre «{topic}» en los documentos cargados "
                    f"de esta asignatura."
                ),
            }

        if len(docs) < num_questions:
            return {
                "preguntas": [],
                "error": (
                    f"Solo se encontraron {len(docs)} fragmentos sobre «{topic}» en los "
                    f"documentos cargados. Reduce el número de preguntas o sube más material."
                ),
            }

        preguntas = []
        for i, doc in enumerate(docs, start=1):
            contexto = doc.page_content
            fuente = doc.metadata.get("source", "Desconocido")
            prompt = PREGUNTA_TEMA_PROMPT.format(contexto=contexto, tema=topic)
            respuesta = self._invoke(prompt)
            preguntas.append({
                "question_number": i,
                "pregunta": respuesta,
                "contexto": contexto,
                "fuente": fuente,
            })

        return {"preguntas": preguntas, "error": None}

    def evaluar(self, contexto, pregunta, respuesta_estudiante):
        prompt = CORRECCION_PROMPT.format(
            contexto=contexto,
            pregunta=pregunta,
            respuesta=respuesta_estudiante,
        )

        respuesta = self._invoke(prompt)
        return respuesta

    def obtener_contexto_chat(
        self,
        subject_id: int,
        topic: str,
        user_message: str,
        lab_id: int | None = None,
    ):
        query = f"{topic} {user_message}".strip()
        docs = []

        if lab_id:
            docs = self.db.similarity_search(
                query,
                k=5,
                filter=self._lab_filter(subject_id, lab_id),
            )

        if not docs:
            docs = self.db.similarity_search(
                query,
                k=5,
                filter=self._subject_filter(subject_id),
            )

        if not docs:
            return None

        contexto = "\n\n---\n\n".join(doc.page_content for doc in docs)
        fuentes = list({doc.metadata.get("source", "Desconocido") for doc in docs})

        return {"contexto": contexto, "fuentes": fuentes}

    def responder_laboratorio(
        self,
        subject_id: int,
        instructions: str,
        topic: str,
        history: list,
        user_message: str,
        lab_id: int | None = None,
    ):
        rag_data = self.obtener_contexto_chat(
            subject_id, topic, user_message, lab_id=lab_id
        )
        contexto = (
            rag_data["contexto"]
            if rag_data
            else "No hay documentos indexados para esta asignatura."
        )

        historial = ""
        for msg in history[-10:]:
            rol = "Estudiante" if msg["role"] == "user" else "Asistente"
            historial += f"{rol}: {msg['content']}\n"

        if not historial:
            historial = "(Sin mensajes previos)"

        prompt = LAB_ASSISTANT_PROMPT.format(
            instrucciones=instructions,
            tema=topic,
            contexto=contexto,
            historial=historial,
            mensaje=user_message,
        )

        respuesta = self._invoke(prompt)

        return {
            "respuesta": respuesta,
            "fuentes": rag_data["fuentes"] if rag_data else [],
        }
