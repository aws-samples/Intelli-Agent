interface ResizeOptions {
  minWidth?: number;
  maxWidth?: number;
  direction: 'horizontal' | 'vertical';
}

export function initResize(elementId: string, options: ResizeOptions) {
  const element = document.getElementById(elementId);
  if (!element) return;

  let isResizing = false;
  let startX: number;
  let startY: number;
  let startWidth: number;
  let startHeight: number;

  // 创建调整手柄
  const resizeHandle = document.createElement('div');
  resizeHandle.className = `resize-handle ${options.direction}`;
  element.appendChild(resizeHandle);

  const startResize = (e: MouseEvent) => {
    isResizing = true;
    startX = e.clientX;
    startY = e.clientY;
    startWidth = element.offsetWidth;
    startHeight = element.offsetHeight;
    document.body.style.cursor =
      options.direction === 'horizontal' ? 'ew-resize' : 'ns-resize';
    document.body.style.userSelect = 'none';
  };

  const doResize = (e: MouseEvent) => {
    if (!isResizing) return;

    if (options.direction === 'horizontal') {
      const width = startWidth + (e.clientX - startX);
      if (
        (!options.minWidth || width >= options.minWidth) &&
        (!options.maxWidth || width <= options.maxWidth)
      ) {
        element.style.width = `${width}px`;
      }
    } else {
      const height = startHeight + (e.clientY - startY);
      if (height > 100 && height < window.innerHeight - 100) {
        element.style.height = `${height}px`;
      }
    }
  };

  const stopResize = () => {
    isResizing = false;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  };

  resizeHandle.addEventListener('mousedown', startResize);
  document.addEventListener('mousemove', doResize);
  document.addEventListener('mouseup', stopResize);

  // 清理函数
  return () => {
    resizeHandle.removeEventListener('mousedown', startResize);
    document.removeEventListener('mousemove', doResize);
    document.removeEventListener('mouseup', stopResize);
    element.removeChild(resizeHandle);
  };
}
