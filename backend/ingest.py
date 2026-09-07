import os
import shutil
from pathlib import Path

import fitz
from langchain.schema import Document as LangchainDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings

from config import Config

EMBEDDING_MODEL = Config.EMBEDDING_MODEL


def leer_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    texto = ""
    for pagina in doc:
        texto += pagina.get_text()
    return texto


def dividir_texto(texto, metadata):
    documento = LangchainDocument(page_content=texto, metadata=metadata)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ".", " "],
    )
    return splitter.split_documents([documento])


def get_chroma_db():
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    return Chroma(
        persist_directory=str(Config.CHROMA_DIR),
        embedding_function=embeddings,
    )


def ingest_pdf(pdf_path: str, subject_id: int, document_id: int, filename: str):
    texto = leer_pdf(pdf_path)

    metadata = {
        "source": filename,
        "subject_id": str(subject_id),
        "document_id": str(document_id),
        "doc_scope": "subject",
    }

    chunks = dividir_texto(texto, metadata)

    if not chunks:
        return 0

    db = get_chroma_db()
    db.add_documents(chunks)
    return len(chunks)


def ingest_lab_pdf(
    pdf_path: str,
    subject_id: int,
    lab_id: int,
    document_id: int,
    filename: str,
):
    texto = leer_pdf(pdf_path)

    metadata = {
        "source": filename,
        "subject_id": str(subject_id),
        "lab_id": str(lab_id),
        "document_id": str(document_id),
        "doc_scope": "lab",
    }

    chunks = dividir_texto(texto, metadata)

    if not chunks:
        return 0

    db = get_chroma_db()
    db.add_documents(chunks)
    return len(chunks)


def _chunk_matches_subject_document(metadata: dict, document_id: int, subject_id: int) -> bool:
    if metadata.get("document_id") != str(document_id):
        return False
    if metadata.get("subject_id") != str(subject_id):
        return False
    if metadata.get("doc_scope") == "lab" or metadata.get("lab_id"):
        return False
    return metadata.get("doc_scope") in (None, "subject")


def _chunk_matches_lab_document(
    metadata: dict,
    document_id: int,
    subject_id: int,
    lab_id: int,
) -> bool:
    if metadata.get("document_id") != str(document_id):
        return False
    if metadata.get("subject_id") != str(subject_id):
        return False
    if metadata.get("lab_id") != str(lab_id):
        return False
    return metadata.get("doc_scope") in (None, "lab")


def delete_subject_document_from_chroma(document_id: int, subject_id: int) -> int:
    db = get_chroma_db()
    collection = db._collection
    results = collection.get(
        where={"document_id": str(document_id)},
        include=["metadatas"],
    )

    ids_to_delete = [
        chunk_id
        for chunk_id, metadata in zip(results.get("ids", []), results.get("metadatas", []))
        if metadata and _chunk_matches_subject_document(metadata, document_id, subject_id)
    ]

    if ids_to_delete:
        collection.delete(ids=ids_to_delete)

    return len(ids_to_delete)


def delete_lab_document_from_chroma(
    document_id: int,
    subject_id: int,
    lab_id: int,
) -> int:
    db = get_chroma_db()
    collection = db._collection
    results = collection.get(
        where={"document_id": str(document_id)},
        include=["metadatas"],
    )

    ids_to_delete = [
        chunk_id
        for chunk_id, metadata in zip(results.get("ids", []), results.get("metadatas", []))
        if metadata and _chunk_matches_lab_document(metadata, document_id, subject_id, lab_id)
    ]

    if ids_to_delete:
        collection.delete(ids=ids_to_delete)

    return len(ids_to_delete)


def delete_all_subject_chunks_from_chroma(subject_id: int) -> int:
    db = get_chroma_db()
    collection = db._collection
    results = collection.get(
        where={"subject_id": str(subject_id)},
        include=["metadatas"],
    )

    ids_to_delete = results.get("ids", [])
    if ids_to_delete:
        collection.delete(ids=ids_to_delete)

    return len(ids_to_delete)


def save_uploaded_pdf(subject_id: int, filename: str, file_bytes: bytes) -> str:
    folder = Config.DOCUMENTOS_DIR / str(subject_id)
    folder.mkdir(parents=True, exist_ok=True)

    safe_name = Path(filename).name
    dest = folder / safe_name

    with open(dest, "wb") as f:
        f.write(file_bytes)

    return str(dest)


def save_uploaded_lab_pdf(
    subject_id: int,
    lab_id: int,
    filename: str,
    file_bytes: bytes,
) -> str:
    folder = Config.DOCUMENTOS_DIR / str(subject_id) / "labs" / str(lab_id)
    folder.mkdir(parents=True, exist_ok=True)

    safe_name = Path(filename).name
    dest = folder / safe_name

    with open(dest, "wb") as f:
        f.write(file_bytes)

    return str(dest)


def cargar_documentos():
    documentos = []
    carpeta = Config.DOCUMENTOS_DIR

    for archivo in carpeta.glob("*.pdf"):
        print(f"Leyendo {archivo.name}")
        texto = leer_pdf(archivo)
        documentos.append(
            LangchainDocument(
                page_content=texto,
                metadata={"source": archivo.name},
            )
        )

    return documentos


def dividir_documentos(documentos):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ".", " "],
    )
    return splitter.split_documents(documentos)


def crear_base_vectorial(chunks):
    if Config.CHROMA_DIR.exists():
        shutil.rmtree(Config.CHROMA_DIR)

    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)

    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(Config.CHROMA_DIR),
    )

    print(f"Base vectorial creada — {len(chunks)} chunks")


def main():
    documentos = cargar_documentos()
    chunks = dividir_documentos(documentos)
    crear_base_vectorial(chunks)


if __name__ == "__main__":
    main()
