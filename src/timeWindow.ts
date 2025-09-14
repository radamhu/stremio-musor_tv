import { TimePreset } from "./types.js";

export function computeWindow(preset: TimePreset | undefined, now = new Date()) {
  const tzNow = new Date(now); // assume process TZ=Europe/Budapest
  const start = new Date(tzNow);
  const end = new Date(tzNow);

  switch (preset ?? "now") {
    case "now":
      end.setMinutes(end.getMinutes() + 90);
      break;
    case "next2h":
      end.setHours(end.getHours() + 2);
      break;
    case "tonight": {
      const tonightStart = new Date(tzNow);
      tonightStart.setHours(18, 0, 0, 0);
      const tonightEnd = new Date(tzNow);
      tonightEnd.setHours(23, 59, 59, 999);
      return { start: tonightStart, end: tonightEnd };
    }
  }
  return { start, end };
}

export function withinWindow(startISO: string, window: { start: Date; end: Date }) {
  const t = new Date(startISO);
  return t >= window.start && t <= window.end;
}
