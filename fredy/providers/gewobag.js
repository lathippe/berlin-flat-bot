/*
 * Gewobag. Their search renders the cards straight into the HTML as long as
 * the filters are in the query string:
 *   ?objekttyp[]=wohnung&gesamtmiete_bis=1200
 *
 * With no parameters the page returns the empty search form and nothing else,
 * so the job URL must already carry a filter. Page two is at /page/2/.
 * Verified 2026-09-24.
 */
import { load } from 'cheerio';
import { buildHash, isOneOf } from '../utils.js';
import { extractNumber } from '../utils/extract-number.js';
import { inServiceArea } from '../utils/never-areas.js';

const BASE_URL = 'https://www.gewobag.de';
const UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36';
const PAGES = 2;

function pageUrl(url, page) {
  if (page === 1) return url;
  const u = new URL(url);
  u.pathname = u.pathname.replace(/\/?$/, '/') + `page/${page}/`;
  return u.href;
}

function parse(html) {
  const $ = load(html);
  const out = [];
  $('.gw-offer, article.angebot, .angebot-big-layout').each((_, el) => {
    const card = $(el);
    const link = card.find('a[href*="/mietangebote/"]').filter((_, a) => /\d{3,}/.test($(a).attr('href') || '')).first().attr('href');
    const address = card.find('.angebot-address address').first().text().trim();
    if (!link || !address) return;
    const area = card.find('.angebot-area td').first().text().replace(/\s+/g, ' ').trim();
    if (!inServiceArea(address, card.find('.angebot-region td').first().text())) return;
    out.push({
      link: new URL(link, BASE_URL).href,
      address,
      title: card.find('.angebot-title').first().text().trim() || address,
      district: card.find('.angebot-region td').first().text().trim(),
      area,
      price: card.find('.angebot-kosten td').first().text().trim(),
      free: card.find('.availability td').first().text().trim(),
      wbs: card.find('.gw-pictogram--wbs title, .gw-pictogram--wbs').length > 0,
      image: card.find('img.swiper__image').first().attr('src') || null,
      features: card
        .find('.angebot-characteristics li')
        .map((_, li) => $(li).text().trim())
        .get()
        .join(', '),
    });
  });
  return out;
}

async function getListings(url) {
  const out = [];
  for (let page = 1; page <= PAGES; page += 1) {
    const res = await fetch(pageUrl(url, page), { headers: { 'User-Agent': UA } });
    if (!res.ok) break;
    const found = parse(await res.text());
    if (found.length === 0) break;
    out.push(...found);
  }
  return out;
}

/** @param {any} o */
function normalize(o) {
  const rooms = /([\d.,]+)\s*Zimmer/i.exec(o.area || '');
  const size = /([\d.,]+)\s*m/i.exec(o.area || '');
  return {
    id: buildHash(`gewobag-${o.link}`),
    link: o.link,
    title: o.title || null,
    // The price arrives as "ab 866,87€". extractNumber parses from the start
    // of the string and returns null when it hits letters, so trim everything
    // before the first digit.
    price: extractNumber(String(o.price ?? '').replace(/^[^\d]+/, '')),
    size: size ? extractNumber(size[1]) : null,
    rooms: rooms ? extractNumber(rooms[1]) : null,
    address: [o.address, o.district].filter(Boolean).join(', ') || null,
    image: o.image,
    description:
      [o.features, o.free ? `frei ab ${o.free}` : '', o.wbs ? 'WBS erforderlich' : '']
        .filter(Boolean)
        .join(' · ') || undefined,
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
  name: 'Gewobag',
  baseUrl: `${BASE_URL}/fuer-mietinteressentinnen/mietangebote/`,
  id: 'gewobag',
};

export { config };
