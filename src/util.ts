export function slugify(s: string) {
  return stripDiacritics(s)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

export function stripDiacritics(s: string) {
  return s.normalize("NFD").replace(/\p{Diacritic}/gu, "");
}

export function isProbablyFilm(category?: string) {
  if (!category) return false;
  const c = category.toLowerCase();
  if (c.includes("film")) return true;
  if (c.includes("sorozat")) return false;
  return false;
}
