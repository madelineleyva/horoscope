import { useEffect, useRef, useState } from "react";

/**
 * A draggable, resizable-by-maximize Win98 "window" chrome. Handles its
 * own drag and maximize state internally; visibility (minimize/close) is
 * a controlled prop, so the parent decides what to show in place of the
 * window when it's hidden (e.g. a taskbar button vs. a desktop icon).
 */
export default function Win98Window({ title, children, footer, defaultWidth = 520, hidden, onMinimize, onClose }) {
  const [maximized, setMaximized] = useState(false);
  const [position, setPosition] = useState({ x: null, y: null }); // null = let the parent center it
  const [dragging, setDragging] = useState(false);
  const dragOffset = useRef({ x: 0, y: 0 });
  const windowRef = useRef(null);

  useEffect(() => {
    if (!dragging) return;

    function handleMouseMove(e) {
      setPosition({
        x: e.clientX - dragOffset.current.x,
        y: e.clientY - dragOffset.current.y,
      });
    }
    function handleMouseUp() {
      setDragging(false);
    }

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [dragging]);

  function handleTitleBarMouseDown(e) {
    if (maximized) return; // matches most OSes: can't drag a maximized window
    if (e.target.closest("button")) return; // don't start a drag from the control buttons
    const rect = windowRef.current.getBoundingClientRect();
    dragOffset.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    setDragging(true);
  }

  if (hidden) return null;

  const style = maximized
    ? { position: "fixed", top: 0, left: 0, right: 0, bottom: 34, width: "auto", margin: 0 }
    : position.x === null
      ? { width: defaultWidth }
      : { position: "fixed", left: position.x, top: position.y, width: defaultWidth, margin: 0 };

  return (
    <div className="window" style={style} ref={windowRef}>
      <div
        className="title-bar"
        style={{ cursor: maximized ? "default" : "move" }}
        onMouseDown={handleTitleBarMouseDown}
      >
        <div className="title-bar-text">{title}</div>
        <div className="title-bar-controls">
          <button aria-label="Minimize" onClick={onMinimize}></button>
          <button
            aria-label={maximized ? "Restore" : "Maximize"}
            onClick={() => setMaximized((m) => !m)}
          ></button>
          <button aria-label="Close" onClick={onClose}></button>
        </div>
      </div>

      <div className="window-body" style={maximized ? { height: "calc(100% - 33px)", overflow: "auto" } : undefined}>
        {children}
      </div>

      {footer}
    </div>
  );
}