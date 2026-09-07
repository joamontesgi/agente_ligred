import { useEffect, useState } from "react";

export default function ResponsiveNav({ items, activeId, onSelect }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const activeItem = items.find((item) => item.id === activeId) || items[0];

  useEffect(() => {
    setMenuOpen(false);
  }, [activeId]);

  const handleSelect = (id) => {
    onSelect(id);
    setMenuOpen(false);
  };

  return (
    <nav className="responsive-nav" aria-label="Navegación principal">
      <div className="responsive-nav-mobile">
        <button
          type="button"
          className="responsive-nav-toggle"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((current) => !current)}
        >
          <span>{activeItem?.label}</span>
          <span className="responsive-nav-caret" aria-hidden="true">
            {menuOpen ? "▲" : "▼"}
          </span>
        </button>
        {menuOpen && (
          <div className="responsive-nav-dropdown">
            {items.map((item) => (
              <button
                key={item.id}
                type="button"
                className={item.id === activeId ? "tab active" : "tab"}
                onClick={() => handleSelect(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="responsive-nav-desktop tabs">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            className={item.id === activeId ? "tab active" : "tab"}
            onClick={() => handleSelect(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
    </nav>
  );
}
