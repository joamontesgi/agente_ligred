-- Profesor IA — Esquema MySQL (referencia)
-- El nombre de la base se toma de MYSQL_DATABASE en backend/.env (ej. tutor, profesor_ia).
-- Recomendado: python setup_mysql.py  (crea la BD y tablas automáticamente)
-- Alternativa manual: ajusta USE <nombre_bd> y ejecuta con el cliente mysql.

-- ─── Usuarios ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  email                 VARCHAR(255) NOT NULL UNIQUE,
  password_hash         VARCHAR(255) NOT NULL,
  nombre                VARCHAR(255) NOT NULL,
  role                  ENUM('teacher', 'student') NOT NULL,
  security_question     VARCHAR(255) NULL,
  security_answer_hash  VARCHAR(255) NULL,
  created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_users_role (role)
) ENGINE=InnoDB;

-- ─── Asignaturas ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subjects (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(255) NOT NULL,
  description TEXT,
  teacher_id  INT NOT NULL,
  llm_model   VARCHAR(255),
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX ix_subjects_teacher (teacher_id)
) ENGINE=InnoDB;

-- ─── Docentes por asignatura (varios docentes) ──────────────
CREATE TABLE IF NOT EXISTS subject_teachers (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  subject_id  INT NOT NULL,
  teacher_id  INT NOT NULL,
  is_primary  TINYINT(1) NOT NULL DEFAULT 0,
  assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_subject_teacher (subject_id, teacher_id),
  FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
  FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX ix_subject_teachers_teacher (teacher_id)
) ENGINE=InnoDB;

-- ─── Inscripciones ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS enrollments (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  student_id  INT NOT NULL,
  subject_id  INT NOT NULL,
  enrolled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_enrollment (student_id, subject_id),
  FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
  INDEX ix_enrollments_subject (subject_id)
) ENGINE=InnoDB;

-- ─── Documentos de asignatura ───────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  subject_id   INT NOT NULL,
  filename     VARCHAR(255) NOT NULL,
  storage_path VARCHAR(512) NOT NULL,
  uploaded_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  ingested     TINYINT DEFAULT 0,
  FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
  INDEX ix_documents_subject (subject_id)
) ENGINE=InnoDB;

-- ─── Evaluaciones ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS evaluations (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  subject_id     INT NOT NULL,
  title          VARCHAR(255) NOT NULL,
  topic          VARCHAR(255) NOT NULL,
  num_questions  INT NOT NULL DEFAULT 5,
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
  INDEX ix_evaluations_subject (subject_id)
) ENGINE=InnoDB;

-- ─── Intentos de evaluación ─────────────────────────────────
CREATE TABLE IF NOT EXISTS evaluation_attempts (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  evaluation_id    INT NOT NULL,
  student_id       INT NOT NULL,
  status           ENUM('in_progress', 'completed') NOT NULL DEFAULT 'in_progress',
  score            FLOAT,
  correct_count    INT,
  total_questions  INT,
  started_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
  completed_at     DATETIME,
  FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE CASCADE,
  FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX ix_eval_attempts_evaluation (evaluation_id),
  INDEX ix_eval_attempts_student (student_id),
  INDEX ix_eval_attempts_status (status)
) ENGINE=InnoDB;

-- ─── Respuestas de evaluación ───────────────────────────────
CREATE TABLE IF NOT EXISTS evaluation_answers (
  id                   INT AUTO_INCREMENT PRIMARY KEY,
  attempt_id           INT NOT NULL,
  question_number      INT NOT NULL,
  pregunta             TEXT NOT NULL,
  contexto             TEXT NOT NULL,
  respuesta_estudiante TEXT,
  evaluacion           TEXT,
  correcta             TINYINT DEFAULT 0,
  fuente               VARCHAR(255),
  FOREIGN KEY (attempt_id) REFERENCES evaluation_attempts(id) ON DELETE CASCADE,
  INDEX ix_eval_answers_attempt (attempt_id)
) ENGINE=InnoDB;

-- ─── Laboratorios ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS labs (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  subject_id   INT NOT NULL,
  title        VARCHAR(255) NOT NULL,
  instructions TEXT NOT NULL,
  topic        VARCHAR(255) NOT NULL,
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
  INDEX ix_labs_subject (subject_id)
) ENGINE=InnoDB;

-- ─── Documentos del laboratorio ─────────────────────────────
CREATE TABLE IF NOT EXISTS lab_documents (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  lab_id       INT NOT NULL,
  filename     VARCHAR(255) NOT NULL,
  storage_path VARCHAR(512) NOT NULL,
  uploaded_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  ingested     TINYINT DEFAULT 0,
  FOREIGN KEY (lab_id) REFERENCES labs(id) ON DELETE CASCADE,
  INDEX ix_lab_documents_lab (lab_id)
) ENGINE=InnoDB;

-- ─── Sesiones de laboratorio (estudiante × lab) ─────────────
CREATE TABLE IF NOT EXISTS lab_sessions (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  lab_id       INT NOT NULL,
  student_id   INT NOT NULL,
  status       ENUM('in_progress', 'completed') NOT NULL DEFAULT 'in_progress',
  started_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME,
  FOREIGN KEY (lab_id) REFERENCES labs(id) ON DELETE CASCADE,
  FOREIGN KEY (student_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX ix_lab_sessions_lab (lab_id),
  INDEX ix_lab_sessions_student (student_id),
  INDEX ix_lab_sessions_status (status)
) ENGINE=InnoDB;

-- ─── Mensajes del chat del laboratorio ──────────────────────
CREATE TABLE IF NOT EXISTS lab_chat_messages (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  session_id INT NOT NULL,
  role       ENUM('user', 'assistant') NOT NULL,
  content    TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES lab_sessions(id) ON DELETE CASCADE,
  INDEX ix_lab_messages_session (session_id),
  INDEX ix_lab_messages_created (created_at)
) ENGINE=InnoDB;

-- ─── Evidencias del laboratorio ─────────────────────────────
CREATE TABLE IF NOT EXISTS lab_evidence (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  session_id   INT NOT NULL,
  filename     VARCHAR(255) NOT NULL,
  storage_path VARCHAR(512) NOT NULL,
  note         TEXT,
  uploaded_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES lab_sessions(id) ON DELETE CASCADE,
  INDEX ix_lab_evidence_session (session_id)
) ENGINE=InnoDB;

-- ─── PDFs de conversaciones (nube de palabras) ──────────────
CREATE TABLE IF NOT EXISTS conversation_pdfs (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  subject_id   INT NOT NULL,
  filename     VARCHAR(255) NOT NULL,
  storage_path VARCHAR(512) NOT NULL,
  uploaded_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
  INDEX ix_conversation_pdfs_subject (subject_id)
) ENGINE=InnoDB;
