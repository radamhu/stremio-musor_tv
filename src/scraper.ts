import { chromium, Browser, Page } from "playwright";
import { LiveMovieRaw } from "./types.js";

let browserPromise: Promise<Browser> | null = null;
let lastFetchAt = 0;
let inFlight: Promise<LiveMovieRaw[]> | null = null;

const RATE_MS = Number(process.env.SCRAPE_RATE_MS ?? "30000");

// target pages – adjust as needed if markup changes
const PAGES = [
  "https://musor.tv/most/tvben",
  "https://musor.tv/filmek"
];

export async function fetchLiveMovies(force = false): Promise<LiveMovieRaw[]> {
  const now = Date.now();
  if (!force && inFlight) return inFlight;
  if (!force && now - lastFetchAt < RATE_MS && inFlight) return inFlight;

  inFlight = (async () => {
    const browser = await getBrowser();
    const results: LiveMovieRaw[] = [];
    for (const url of PAGES) {
      const page = await browser.newPage({ userAgent: ua() });
      try {
        await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });

        // Accept cookie if present
        await safeClick(page, 'button:has-text("Elfogadom"), button:has-text("Accept")');

        // The selectors below are guesses that you’ll likely tweak quickly:
        const cards = page.locator(".card, .program, .grid-item");
        const count = await cards.count();

        for (let i = 0; i < count; i++) {
          const el = cards.nth(i);
          const title = (await el.locator("h3, .title, .program-title").first().textContent())?.trim() ?? "";
          if (!title) continue;

          const timeText = (await el.locator(".time, .program-time, time").first().textContent())?.trim() ?? "";
          const channel = (await el.locator(".channel, .station, [data-channel]").first().textContent())?.trim() ?? "";
          const category = (await el.locator(".category, .genre, .program-category").first().textContent())?.trim() ?? "";
          const img = await el.locator("img").first().getAttribute("src");

          const startISO = inferStartISO(timeText);
          results.push({
            title: cleanup(title),
            startISO,
            channel: cleanup(channel),
            category: cleanup(category),
            poster: absolutize(img)
          });
        }
      } catch (e) {
        console.error(`[scraper] failed ${url}:`, e);
      } finally {
        await page.close();
      }
    }
    lastFetchAt = Date.now();
    return dedupe(results);
  })();

  return inFlight.finally(() => (inFlight = null));
}

function cleanup(s?: string | null) { return (s ?? "").replace(/\s+/g, " ").trim(); }

function inferStartISO(timeText: string) {
  // crude: expects "HH:MM" somewhere
  const m = timeText.match(/(\d{1,2}):(\d{2})/);
  const d = new Date();
  if (m) {
    d.setHours(Number(m[1]), Number(m[2]), 0, 0);
  }
  return d.toISOString();
}

function absolutize(src?: string | null) {
  if (!src) return undefined;
  if (src.startsWith("http")) return src;
  return `https://musor.tv${src.startsWith("/") ? src : `/${src}`}`;
}

async function getBrowser() {
  if (!browserPromise) {
    browserPromise = chromium.launch({ args: ["--no-sandbox"], headless: true });
  }
  return browserPromise;
}

async function safeClick(page: Page, selector: string) {
  const el = page.locator(selector).first();
  if (await el.count()) await el.click({ timeout: 2000 }).catch(() => {});
}

function dedupe(items: LiveMovieRaw[]) {
  const seen = new Set<string>();
  return items.filter(x => {
    const key = `${x.title}|${x.channel}|${x.startISO.slice(0,16)}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function ua() {
  return "Mozilla/5.0 (compatible; StremioHU/1.0; +https://example.invalid)";
}
