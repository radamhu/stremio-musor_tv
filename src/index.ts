import fastify from "fastify";
import pino from "pino";
import { addonBuilder } from "stremio-addon-sdk";
import { computeWindow, withinWindow } from "./timeWindow.js";
import { createCache } from "./cache.js";
import { fetchLiveMovies } from "./scraper.js";
import { isProbablyFilm, slugify, stripDiacritics } from "./util.js";
import type { CatalogExtra, StremioMetaPreview } from "./types.js";

const PORT = Number(process.env.PORT ?? "7000");
const CACHE_TTL_MIN = Number(process.env.CACHE_TTL_MIN ?? "10") * 60_000;

const logger = pino({ level: process.env.LOG_LEVEL ?? "info" });

const manifest = {
  id: "hu.live.movies",
  version: "1.0.0",
  name: "HU Live Movies (musor.tv)",
  description: "Catalog: movies on Hungarian TV now/soon",
  logo: "https://stremio-logo.svg", // replace if you have one
  behaviorHints: { configurable: false },
  resources: ["catalog"],
  types: ["movie"],
  catalogs: [{
    type: "movie",
    id: "hu-live",
    name: "Live on TV (HU)",
    extra: [
      { name: "search", isRequired: false },
      { name: "time", options: ["now", "next2h", "tonight"], isRequired: false }
    ]
  }]
};

const builder = new addonBuilder(manifest as any);

// cache for meta previews derived from scraper
const cache = createCache<StremioMetaPreview[]>(CACHE_TTL_MIN);

builder.defineCatalogHandler(async ({ type, id, extra }) => {
  if (type !== "movie" || id !== "hu-live") return { metas: [] };

  const q = (extra ?? {}) as CatalogExtra;
  const timeWindow = computeWindow(q.time);
  const cacheKey = `catalog:${q.time ?? "now"}`;

  let metas = cache.get(cacheKey);
  if (!metas) {
    const raw = await fetchLiveMovies(false);
    const filtered = raw
      .filter(r => isProbablyFilm(r.category))
      .filter(r => withinWindow(r.startISO, timeWindow));

    metas = filtered.map(r => {
      const id = `musortv:${slugify(r.channel)}:${Math.floor(new Date(r.startISO).getTime()/1000)}:${slugify(r.title)}`;
      const genres = parseGenres(r.category);
      return {
        id,
        type: "movie",
        name: r.title,
        releaseInfo: `${fmtTime(r.startISO)} • ${r.channel}`,
        poster: r.poster,
        genres
      };
    });

    cache.set(cacheKey, metas);
  }

  // search filter (accent-insensitive)
  if (q.search && q.search.trim().length > 0) {
    const needle = stripDiacritics(q.search).toLowerCase();
    metas = metas.filter(m => stripDiacritics(m.name).toLowerCase().includes(needle));
  }

  return { metas };
});

// minimal HTTP server: /manifest.json and /catalog/* served by SDK + health
const app = fastify({ logger });

app.get("/healthz", async () => ({ ok: true, ts: Date.now() }));

// hook SDK interface onto Fastify
const iface = builder.getInterface();
app.get("/manifest.json", async (_req, reply) => reply.send(iface.manifest));
app.get("/catalog/:type/:id.json", async (req: any, reply) =>
  reply.send(await iface.get("catalog", req.params, req.query))
);

app.listen({ port: PORT, host: "0.0.0.0" })
  .then(() => logger.info(`addon up on :${PORT}`))
  .catch((e) => { logger.error(e, "server failed"); process.exit(1); });

function parseGenres(category?: string) {
  if (!category) return undefined;
  const base = category.split(",")[0] ?? category;
  // map Hungarian → generic
  const lc = base.toLowerCase();
  if (lc.includes("akció")) return ["Akció"];
  if (lc.includes("vígjáték")) return ["Vígjáté"];
  if (lc.includes("dráma")) return ["Dráma"];
  if (lc.includes("thriller")) return ["Thriller"];
  if (lc.includes("horror")) return ["Horror"];
  return [base.trim()];
}

function fmtTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleTimeString("hu-HU", { hour: "2-digit", minute: "2-digit" });
}
