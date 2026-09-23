import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

/**
 * Win98-style taskbar, fixed to the bottom of the viewport. Takes a list
 * of menu items so new entries can be added here as the app grows, rather
 * than scattering links around the page.
 *
 * menuItems: [{ label, icon, href, external? }]
 *   - external: true opens href in a new tab (for things like API docs)
 *   - external: false/omitted uses React Router's <Link> (in-app routes)
 * 
 *  runningApp: { label, icon, onRestore } | null
 *   When set, renders a taskbar button for a minimized/closed window -
 *   clicking it calls onRestore. Pass null when nothing's minimized.
 */
export default function Taskbar({ menuItems, runningApp }) {
  const [open, setOpen] = useState(false);
  const [now, setNow] = useState(new Date());
  const menuRef = useRef(null);

  // Classic taskbar clock - updates once a minute, that's all it needs.
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);

  // Close the menu on an outside click, like a real Start Menu.
  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const timeLabel = now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

    return (
    <div ref={menuRef} style={{ position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 1000 }}>
      <style>{`
        .win98-menu-link:hover {
          background: #000080;
          color: white !important;
        }
      `}</style>

      {open && (
        <div
          className="window"
          style={{
            position: "absolute",
            bottom: "100%",
            left: 4,
            width: 220,
            marginBottom: 2,
            padding: 0,
          }}
        >
          <div style={{ display: "flex" }}>
            <div
              style={{
                writingMode: "vertical-rl",
                transform: "rotate(180deg)",
                background: "linear-gradient(#000080, #1084d0)",
                color: "white",
                fontWeight: "bold",
                fontSize: 18,
                padding: "8px 4px",
                letterSpacing: 1,
              }}
            >
              HOROSCOPE 98
            </div>
            <ul style={{ listStyle: "none", margin: 0, padding: 4, flex: 1 }}>
              {menuItems.map((item) => (
                <li key={item.label}>
                  <StartMenuLink item={item} onNavigate={() => setOpen(false)} />
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <div
        style={{
          display: "flex",
          alignItems: "center",
          height: 34,
          padding: "0 4px",
          background: "#c0c0c0",
          borderTop: "2px solid #dfdfdf",
          gap: 6,
        }}
      >
        <button
          onClick={() => setOpen((o) => !o)}
          style={{
            fontWeight: "bold",
            display: "flex",
            alignItems: "center",
            gap: 4,
            padding: "4px 8px",
          }}
        >
          🪟 Start
        </button>

        {runningApp && (
          <button
            onClick={runningApp.onRestore}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              padding: "4px 8px",
              minWidth: 120,
              // Pressed-in look, like a real taskbar button for a
              // minimized (unfocused) window.
              boxShadow: "inset -1px -1px #dfdfdf, inset 1px 1px #0a0a0a, inset -2px -2px #808080, inset 2px 2px #fff",
            }}
          >
            {runningApp.icon} {runningApp.label}
          </button>
        )}

        <div style={{ flex: 1 }} />

        <div
          className="window"
          style={{ padding: "3px 8px", margin: 0, fontSize: 13 }}
        >
          {timeLabel}
        </div>
      </div>
    </div>
  );
}

function StartMenuLink({ item, onNavigate }) {
  const linkStyle = {
    display: "block",
    padding: "6px 8px",
    textDecoration: "none",
    color: "black",
  };

  if (item.external) {
    return (
      <a
        href={item.href}
        target="_blank"
        rel="noreferrer"
        className="win98-menu-link"
        style={linkStyle}
        onClick={onNavigate}
      >
        {item.icon} {item.label}
      </a>
    );
  }

  return (
    <Link
      to={item.href}
      className="win98-menu-link"
      style={linkStyle}
      onClick={onNavigate}
    >
      {item.icon} {item.label}
    </Link>
  );
}
