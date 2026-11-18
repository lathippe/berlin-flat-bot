/*
 * BUWOG. German rentals are not on buwog.de, they are on
 * buwog-immobilientreuhand.de. The front end fetches JSON from /property-search
 * (the address sits in <script id="apiUrl">).
 *
 * Without result_count_only=false the endpoint returns only a counter and an
 * empty list. There is no city filter, only a list of postcodes, so: take the
 * counter first, read filter_result.locations.Berlin.value for the postcodes
 * that currently have something, then page through 20 at a time via
 * pagination.next.
 *
 * Both prices come back: rent_price is warm, base_rent_price is cold. Both go
 * into description so the price parser does not multiply warm by 1.3 a second
 * time. Verified 2026-09-30: 31 flats in Berlin, no overlap with Vonovia.
 */
import { buildHash, isOneOf } from '../utils.js';
import { inServiceArea } from '../utils/never-areas.js';

const BASE_URL = 'https://www.buwog-immobilientreuhand.de';
const UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36';
const HEADERS = { 'User-Agent': UA, Accept: 'application/json', Referer: `${BASE_URL}/immobilien` };
const MAX_PAGES = 5;

/** City comes from the job URL (?city=Berlin), Berlin by default. */
function cityFrom(url) {
  try {
    return new URL(url).searchParams.get('city') || 'Berlin';
  } catch {
    return 'Berlin';
  }
}

function searchUrl(params) {
  const q = new URLSearchParams({
    'property_search[marketing_type]': 'rent',
    'property_search[property_type]': 'flat',
    ...params,
  });
  return `${BASE_URL}/property-search?${q}`;
}

async function getJson(url) {
  const res = await fetch(url, { headers: HEADERS });
  if (!res.ok) return null;
  return res.json().catch(() => null);
}

async function getListings(url) {
  const city = cityFrom(url);
  const count = await getJson(searchUrl({ 'property_search[result_count_only]': 'true' }));
  const zips = count?.filter_result?.locations?.distinct_values?.[city]?.value;
  if (!zips) return [];

  const out = new Map();
  let next = searchUrl({
    'property_search[result_count_only]': 'false',
    // date_updated is null on every record. Sorting by it shuffles the pages,
    // so one flat arrives twice and another never arrives at all. Price is the
    // only field that gives a stable order.
    'property_search[sort_by]': 'rent_price',
    'property_search[sort_direction]': 'asc',
    'property_search[zip_code]': zips,
    'property_search[page]': '1',
  });
  for (let page = 0; next && page < MAX_PAGES; page++) {
    const data = await getJson(next);
    const result = data?.real_estate_result;
    const items = Array.isArray(result) ? result : Object.values(result ?? {});
    if (items.length === 0) break;
    for (const o of items) if (o.real_estate_id) out.set(o.real_estate_id, o);
    const n = data?.pagination?.next;
    next = n && data.pagination.current < data.pagination.pages.length ? `${BASE_URL}${n}` : null;
  }
  return [...out.values()].filter(
    (o) =>
      o.marketing_type === 'rent' &&
      Number(o.total_size) > 0 &&
      Number(o.total_rooms) > 0 &&
      inServiceArea(o.street, o.zip_code, o.city, o.title),
  );
}

const ENTITIES = { amp: '&', lt: '<', gt: '>', quot: '"', nbsp: ' ', szlig: 'ß', euro: '€',
  auml: 'ä', ouml: 'ö', uuml: 'ü', Auml: 'Ä', Ouml: 'Ö', Uuml: 'Ü' };
const plain = (html) =>
  String(html ?? '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&(#\d+|\w+);/g, (m, e) => (e[0] === '#' ? String.fromCharCode(Number(e.slice(1))) : ENTITIES[e] ?? m))
    .replace(/\s+/g, ' ')
    .trim();

const euro = (n) => `${Number(n).toFixed(2).replace('.', ',')} €`;

/** @param {any} o */
function normalize(o) {
  const street = [o.street, o.house_number].filter(Boolean).join(' ');
  const address = [street, [o.zip_code, o.city].filter(Boolean).join(' ')].filter(Boolean).join(', ');
  const facts = [
    o.base_rent_price ? `Kaltmiete: ${euro(o.base_rent_price)}` : '',
    o.rent_price ? `Warmmiete: ${euro(o.rent_price)}` : '',
    o.floor ? `Etage ${o.floor}` : '',
    o.balcony === 'yes' ? 'Balkon' : '',
    o.kitchen === 'yes' ? 'Einbauküche' : '',
    o.elevator === 'yes' ? 'Aufzug' : '',
    o.available_from ? `frei ab ${o.available_from === 'now' ? 'sofort' : o.available_from}` : '',
  ];
  const text = plain(o.description);
  return {
    id: o.real_estate_id ? buildHash(`buwog-${o.real_estate_id}`) : null,
    link: o.real_estate_id ? `${BASE_URL}/property-object/${o.real_estate_id}` : o.overlay_url || null,
    title: typeof o.title === 'string' && o.title.trim() ? o.title.trim() : null,
    price: o.rent_price == null ? null : Math.round(Number(o.rent_price)),
    size: o.total_size == null ? null : Number(o.total_size),
    rooms: o.total_rooms == null ? null : Number(o.total_rooms),
    address: address || null,
    image: Array.isArray(o.images) && o.images.length ? o.images[0] : null,
    description: [facts.filter(Boolean).join(' · '), text].filter(Boolean).join('\n') || undefined,
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
  name: 'BUWOG',
  baseUrl: `${BASE_URL}/immobilien`,
  id: 'buwog',
};

export { config };
