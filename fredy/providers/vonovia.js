/*
 * Vonovia. Their own search, the same API the vonovia.de front end uses.
 *
 * A token valid for 15 minutes comes from /api/real-estate/search-token, then
 * it is a plain GET, 15 per page. Page through with `offset`: the `page`
 * parameter silently returns the first page every time.
 *
 * Results mix in parking spaces and commercial units. Those have zeros in size
 * and rooms, which is how they are dropped. Coordinates in the list are always
 * 0,0, so Fredy geocodes the address itself. Verified 2026-09-24.
 */
import { buildHash, isOneOf } from '../utils.js';
import { extractNumber } from '../utils/extract-number.js';
import { inServiceArea } from '../utils/never-areas.js';

const BASE_URL = 'https://www.vonovia.de';
const REFERER = `${BASE_URL}/zuhause-finden/immobilien`;
const UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36';
const OFFSETS = [0, 15, 30, 45, 60];

/** City comes from the job URL (?city=Berlin), Berlin by default. */
function cityFrom(url) {
  try {
    return new URL(url).searchParams.get('city') || 'Berlin';
  } catch {
    return 'Berlin';
  }
}

async function getListings(url) {
  const tokenRes = await fetch(`${BASE_URL}/api/real-estate/search-token`, {
    headers: { 'User-Agent': UA, Referer: REFERER },
  });
  if (!tokenRes.ok) return [];
  const { token } = await tokenRes.json().catch(() => ({}));
  if (!token) return [];

  const headers = { 'User-Agent': UA, Referer: REFERER, 'X-VON-Search-Token': token };
  const city = cityFrom(url);
  const out = [];
  for (const offset of OFFSETS) {
    const res = await fetch(
      `${BASE_URL}/api/real-estate/list?city=${encodeURIComponent(city)}&offset=${offset}`,
      { headers },
    );
    if (!res.ok) break;
    const data = await res.json().catch(() => ({}));
    const results = Array.isArray(data.results) ? data.results : [];
    if (results.length === 0) break;
    out.push(...results);
    if (out.length >= (data?.paging?.info?.count ?? Infinity)) break;
  }
  return out.filter(
    (o) =>
      String(o.vermarktungsart_miete ?? '1') !== '0' &&
      Number(o.groesse) > 0 &&
      Number(o.anzahl_zimmer) > 0 &&
      inServiceArea(o.strasse, o.ort, o.titel),
  );
}

/** @param {any} o */
function normalize(o) {
  const address = [o.strasse, [o.plz, o.ort].filter(Boolean).join(' ')].filter(Boolean).join(', ');
  return {
    id: o.wrk_id == null ? null : buildHash(`vonovia-${o.wrk_id}`),
    link: o.slug ? `${BASE_URL}/zuhause-finden/immobilien/${o.slug}` : null,
    title: typeof o.titel === 'string' && o.titel.trim() ? o.titel.trim() : null,
    price: extractNumber(o.preis),
    size: extractNumber(o.groesse),
    rooms: extractNumber(o.anzahl_zimmer),
    address: address || null,
    image: typeof o.preview_img_url === 'string' ? o.preview_img_url : null,
    description: o.has_grundriss ? 'Grundriss vorhanden' : undefined,
  };
}

function applyBlacklist(o, appliedBlackList) {
  return (
    !isOneOf(o.title, appliedBlackList) &&
    !isOneOf(o.description, appliedBlackList) &&
    !isOneOf(o.address, appliedBlackList)
  );
}

/** @type {import('../types/providerConfig.js').ProviderConfig} */
const config = {
  requiredFieldNames: ['id', 'link', 'title', 'price', 'size', 'rooms', 'address', 'image', 'description'],
  url: null,
  crawlContainer: 'body',
  sortByDateParam: null,
  waitForSelector: 'body',
  crawlFields: { id: '@id' },
  normalize,
  getListings,
};

export const createConfig = (sourceConfig, blacklist = []) => ({
  ...config,
  enabled: sourceConfig.enabled,
  url: sourceConfig.url,
  filter: (listing) => applyBlacklist(listing, blacklist ?? []),
});

export const metaInformation = {
  countries: ['de'],
  name: 'Vonovia',
  baseUrl: `${BASE_URL}/zuhause-finden/immobilien`,
  id: 'vonovia',
};

export { config };
