export default function Pagination({
  page,
  totalPages,
  totalItems,
  pageSize,
  onPageChange,
}) {
  if (totalPages <= 1) {
    return null;
  }

  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, totalItems);

  return (
    <div className="pagination">
      <span className="pagination-info muted">
        {start}-{end} de {totalItems}
      </span>
      <div className="pagination-controls">
        <button
          type="button"
          className="btn-secondary btn-sm"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
        >
          Anterior
        </button>
        <span className="pagination-page">
          Página {page} / {totalPages}
        </span>
        <button
          type="button"
          className="btn-secondary btn-sm"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
        >
          Siguiente
        </button>
      </div>
    </div>
  );
}
