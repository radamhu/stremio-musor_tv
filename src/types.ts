export type TimePreset = "now" | "next2h" | "tonight";

export interface CatalogExtra {
  search?: string;
  time?: TimePreset;
}

export interface LiveMovieRaw {
  title: string;
  startISO: string;  // local time ISO or yyyy-mm-ddThh:mm
  channel: string;
  category?: string; // e.g., "amerikai akciófilm, 2019"
  poster?: string;
}

export interface StremioMetaPreview {
  id: string;
  type: "movie";
  name: string;
  releaseInfo?: string;  // "21:00 • RTL"
  poster?: string;
  background?: string;
  genres?: string[];
}
