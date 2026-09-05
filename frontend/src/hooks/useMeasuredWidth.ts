import { useEffect, useRef, useState } from "react";

/** Tracks an element's rendered width via ResizeObserver, so SVG charts can
 * size themselves to fill their container instead of using a fixed pixel
 * width — width is 0 until the first layout pass/observation lands. */
export function useMeasuredWidth<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    setWidth(el.getBoundingClientRect().width);
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) setWidth(entry.contentRect.width);
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return { ref, width };
}
