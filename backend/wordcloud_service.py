import base64
import os
import re
from collections import Counter
from io import BytesIO

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from wordcloud import WordCloud

from ingest import leer_pdf

SPANISH_STOPWORDS = {
    "a", "al", "algo", "algunas", "algunos", "ante", "antes", "como", "con",
    "contra", "cual", "cuando", "de", "del", "desde", "donde", "dos", "el",
    "ella", "ellas", "ello", "ellos", "en", "entre", "era", "erais", "eran",
    "eras", "eres", "es", "esa", "esas", "ese", "eso", "esos", "esta", "estaba",
    "estabais", "estaban", "estabas", "estad", "estada", "estadas", "estado",
    "estados", "estamos", "estan", "estando", "estar", "estaremos", "estara",
    "estaran", "estaras", "estaria", "estariais", "estarian", "estarias",
    "estas", "este", "estemos", "esto", "estos", "estoy", "estuve", "estuviera",
    "estuvierais", "estuvieran", "estuvieras", "estuvieron", "estuviese",
    "estuvieseis", "estuviesen", "estuvieses", "estuvimos", "estuviste",
    "estuvisteis", "estuvo", "fin", "fue", "fuera", "fuerais", "fueran",
    "fueras", "fueron", "fuese", "fueseis", "fuesen", "fueses", "fui", "fuimos",
    "fuiste", "fuisteis", "ha", "habeis", "haber", "habia", "habiais", "habian",
    "habias", "habida", "habidas", "habido", "habidos", "habiendo", "habla",
    "hablan", "hablar", "hablo", "habra", "habran", "habras", "habria",
    "habriais", "habrian", "habrias", "hace", "hacen", "hacer", "hacia", "hago",
    "han", "has", "hasta", "hay", "haya", "hayais", "hayan", "hayas", "he",
    "hemos", "hice", "hicieron", "hizo", "la", "las", "le", "les", "lo", "los",
    "mas", "me", "mi", "mia", "mias", "mio", "mios", "mis", "mucho", "muy", "nada",
    "ni", "no", "nos", "nosotras", "nosotros", "nuestra", "nuestras", "nuestro",
    "nuestros", "o", "os", "otra", "otras", "otro", "otros", "para", "pero",
    "poco", "por", "porque", "que", "quien", "quienes", "se", "sea", "seais",
    "sean", "seas", "ser", "sera", "seran", "seras", "seria", "seriais",
    "serian", "serias", "si", "sido", "siendo", "sin", "sobre", "sois", "solamente",
    "solo", "somos", "son", "soy", "su", "sus", "suya", "suyas", "suyo", "suyos",
    "tal", "tambien", "tanto", "te", "teneis", "tener", "tengo", "tenia",
    "teniais", "tenian", "tenias", "ti", "tiene", "tienen", "tienes", "todo",
    "todos", "tu", "tus", "tuya", "tuyas", "tuyo", "tuyos", "un", "una", "uno",
    "unos", "vosotras", "vosotros", "vuestra", "vuestras", "vuestro", "vuestros",
    "y", "ya", "yo",
}

PDF_STOPWORDS = {
    "asistente", "asignatura", "chat", "completado", "del", "estado",
    "estudiante", "evaluacion", "fecha", "finalizacion", "historial",
    "inicio", "instrucciones", "laboratorio", "mensajes", "pagina",
    "pdf", "progreso", "puntuacion", "respuesta", "resultado", "resultados",
    "tema", "titulo",
}

STOPWORDS = SPANISH_STOPWORDS | PDF_STOPWORDS

WORD_PATTERN = re.compile(r"\b[a-záéíóúüñ]{3,}\b", re.IGNORECASE)


def normalize_word(word: str) -> str:
    replacements = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}
    normalized = word.lower()
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized


def tokenize_text(text: str) -> list[str]:
    words = []
    for match in WORD_PATTERN.findall(text or ""):
        word = normalize_word(match)
        if word not in STOPWORDS and not word.isdigit():
            words.append(word)
    return words


def extract_text_from_pdfs(pdf_paths: list[str]) -> str:
    chunks = []
    for pdf_path in pdf_paths:
        if os.path.isfile(pdf_path):
            chunks.append(leer_pdf(pdf_path))
    return "\n".join(chunks)


def get_top_terms(text: str, limit: int = 30) -> list[dict]:
    counter = Counter(tokenize_text(text))
    return [
        {"word": word, "count": count}
        for word, count in counter.most_common(limit)
    ]


def generate_wordcloud_png(text: str) -> bytes:
    tokens = tokenize_text(text)
    if not tokens:
        raise ValueError("No se encontró texto útil para generar la nube de palabras.")

    processed_text = " ".join(tokens)
    wordcloud = WordCloud(
        width=1200,
        height=620,
        background_color="white",
        max_words=120,
        colormap="viridis",
        collocations=False,
        stopwords=STOPWORDS,
        random_state=42,
    ).generate(processed_text)

    figure, axis = plt.subplots(figsize=(12, 6.2))
    axis.imshow(wordcloud, interpolation="bilinear")
    axis.axis("off")

    buffer = BytesIO()
    figure.savefig(buffer, format="png", bbox_inches="tight", dpi=150)
    plt.close(figure)
    buffer.seek(0)
    return buffer.read()


def build_wordcloud_analysis(pdf_paths: list[str]) -> dict:
    text = extract_text_from_pdfs(pdf_paths)
    tokens = tokenize_text(text)

    if not tokens:
        raise ValueError(
            "No se extrajo texto utilizable de los PDFs seleccionados."
        )

    image_bytes = generate_wordcloud_png(text)
    return {
        "total_words": len(tokens),
        "unique_words": len(set(tokens)),
        "top_terms": get_top_terms(text),
        "image_base64": base64.b64encode(image_bytes).decode("ascii"),
    }
