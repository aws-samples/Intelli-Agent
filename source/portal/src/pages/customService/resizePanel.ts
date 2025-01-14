export function initResizePanel() {
  const panel = document.getElementById('resizable-panel');
  if (!panel) return;

  let isResizing = false;
  let startX: number;
  let startWidth: number;

  panel.addEventListener('mousedown', (e) => {
    const rect = panel.getBoundingClientRect();
    if (e.clientX < rect.left + 8) {
      isResizing = true;
      startX = e.clientX;
      startWidth = rect.width;
    }
  });

  document.addEventListener('mousemove', (e) => {
    if (!isResizing) return;

    const width = startWidth - (e.clientX - startX);
    if (width > 200 && width < 600) {
      panel.style.width = `${width}px`;
    }
  });

  document.addEventListener('mouseup', () => {
    isResizing = false;
  });
}
