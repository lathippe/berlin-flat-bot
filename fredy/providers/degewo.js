/*
 * degewo. The old host immosuche.degewo.de is dead (DNS resolves, 443 never
 * answers); the search lives at www.degewo.de/immosuche.
 *
 * A plain GET returns results sorted by room count, and two-room flats never
 * reach the first page. So: fetch the form first for its cHash and hidden
 * fields, then POST a price filter sorted by publication date.
 *
 * Card markup is inverted from what you would expect: the label is in <dd> and
 * the value in <dt>, as in "45,52" / "m²". Verified 2026-09-24.
 */
import { load } from 'cheerio';
import { buildHash, isOneOf } from '../utils.js';
import { extractNumber } from '../utils/extract-number.js';
import { inServiceArea } from '../utils/never-areas.js';

const BASE_URL = 'https://www.degewo.de';
const SEARCH_URL = `${BASE_URL}/immosuche`;
const UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36';

function maxRentFrom(url) {
  try {
    return new URL(url).searchParams.get('warmmiete_end') || '';
  } catch {
    return '';
  }
}

function parse(html) {
  const $ = load(html);
  const out = [];
  $('.c-teaser__inner').each((_, el) => {
    const card = $(el);
    const anchor = card.find('a[href*="/immosuche/details/"]').first();
    const href = anchor.attr('href');
    if (!href) return;
    const facts = {};
    card.find('.c-definition-list__item').each((_, item) => {
      const label = $(item).find('dd').first().text().trim();
      const value = $(item).find('dt').first().text().trim();
      if (label) facts[label] = value;
    });
    const addressLine = card.find('h3').first().next('p').text().trim();
    const [street, kiez] = addressLine.split('|').map((s) => s.trim());
    if (!inServiceArea(street, kiez, anchor.text())) return;
    out.push({
      link: new URL(href, BASE_URL).href,
      title: anchor.text().trim(),
      street,
      kiez,
      rooms: facts['Zimmer'],
      size: facts['m²'] || facts['Wohnfläche'],
      price: facts['Warmmiete'] || facts['Gesamtmiete'],
      free: facts['frei ab'],
      tags: card
        .find('.c-tag__label')
        .map((_, t) => $(t).text().trim())
        .get()
        .join(', '),
      image: card.find('img.c-img').first().attr('src') || null,
    });
  });
  return out;
}

async function getListings(url) {
  const first = await fetch(SEARCH_URL, { headers: { 'User-Agent': UA } });
  if (!first.ok) return [];
  const html = await first.text();
  const $ = load(html);
  const form = $('#form-filter-immo-objects');
  let page = html;

  const action = form.attr('action');
  if (action) {
    const body = new URLSearchParams();
    form.find('input[type="hidden"]').each((_, input) => {
      const name = $(input).attr('name');
      if (name) body.append(name, $(input).attr('value') ?? '');
    });
    const maxRent = maxRentFrom(url);
    if (maxRent) body.set('tx_openimmo_immobilie[warmmiete_end]', maxRent);
    body.set('tx_openimmo_immobilie[sortBy]', 'immobilie_zeitpunkt_erstellt');
    body.set('tx_openimmo_immobilie[sortOrder]', 'desc');
    const posted = await fetch(new URL(action, BASE_URL).href, {
      method: 'POST',
      headers: { 'User-Agent': UA, 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString(),
    });
    if (posted.ok) {
      const text = await posted.text();
      if (text.includes('c-teaser__inner')) page = text;
    }
  }
  return parse(page);
}

/** @param {any} o */
function normalize(o) {
  return {
    id: buildHash(`degewo-${o.link}`),
    link: o.link,
    title: o.title || o.street || null,
    price: extractNumber(o.price),
    size: extractNumber(o.size),
    rooms: extractNumber(o.rooms),
    address: [o.street, o.kiez].filter(Boolean).join(', ') || null,
    image: o.image,
    description: [o.tags, o.free ? `frei ab ${o.free}` : ''].filter(Boolean).join(' · ') || undefined,
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
  name: 'degewo',
  baseUrl: SEARCH_URL,
  id: 'degewo',
};

export { config };
