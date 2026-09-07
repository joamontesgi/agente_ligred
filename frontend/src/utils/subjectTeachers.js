export function formatSubjectTeachers(subject) {
  const teachers = subject?.teachers || [];

  if (teachers.length === 0) {
    return subject?.teacher_name ? `Docente: ${subject.teacher_name}` : "";
  }

  if (teachers.length === 1) {
    return `Docente: ${teachers[0].nombre}`;
  }

  return teachers
    .map((teacher) => `${teacher.nombre}${teacher.is_primary ? " (principal)" : ""}`)
    .join(" · ");
}
