/*
 * HOWOGE. Flats straight from howoge.de, no portal in between.
 * The listing comes from a TYPO3 endpoint their own filter calls:
 *   POST /?type=999&tx_howrealestate_json_list[action]=immoList
 * The `rent` field in the list is the Gesamtmiete, i.e. warm. On the detail
 * page the same flat shows Kaltmiete 1134 and Warmmiete 1498.50, and the JSON
 * carries 1498.5. Verified 2026-09-24.
 */
import { buildHash, isOneOf } from '../utils.js';
import { extractNumber } from '../utils/extract-number.js';
import { inServiceArea } from '../utils/never-areas.js';

const BASE_URL = 'https://www.howoge.de';
const LIST_URL = `${BASE_URL}/?type=999&tx_howrealestate_json_list%5Baction%5D=immoList`;
const UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36';

async function getListings() {
  const res = await fetch(LIST_URL, {
    method: 'POST',
    headers: { 'User-Agent': UA, 'Content-Type': 'application/x-www-form-urlencoded' },
    body: 'tx_howrealestate_json_list[page]=1&tx_howrealestate_json_list[limit]=100&tx_howrealestate_json_list[lang]=0',
  });
  if (!res.ok) return [];
  const data = await res.json().catch(() => ({}));
  return (Array.isArray(data.immoobjects) ? data.immoobjects : []).filter((o) =>
    inServiceArea(o.title, o.district),
  );
}

/** @param {any} o */
function normalize(o) {
  const title = typeof o.title === 'string' ? o.title.trim() : null;
  const features = Array.isArray(o.features) ? o.features.filter((f) => typeof f === 'string').join(', ') : '';
  const wbs = String(o.wbs ?? '').toLowerCase().startsWith('ja') ? 'WBS erforderlich' : '';
  return {
    id: o.uid == null ? null : buildHash(`howoge-${o.uid}`),
    link: o.link ? new URL(o.link, BASE_URL).href : null,
    title,
    price: extractNumber(o.rent),
    size: extractNumber(o.area),
    rooms: extractNumber(o.rooms),
    address: [title, o.district].filter(Boolean).join(', ') || null,
    image: o.image ? new URL(o.image, BASE_URL).href : null,
    description: [o.notice, features, wbs].filter(Boolean).join(' · ') || undefined,
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
  name: 'HOWOGE',
  baseUrl: `${BASE_URL}/immobiliensuche/wohnungssuche.html`,
  id: 'howoge',
};

export { config };
