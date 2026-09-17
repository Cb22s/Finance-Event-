import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const fixture = JSON.parse(fs.readFileSync(0, 'utf8'));
const root = new URL('../../frontend/', import.meta.url);
const dashboard = fs.readFileSync(new URL('js/dashboard.js', root), 'utf8');
const familyOffers = fs.readFileSync(new URL('js/family-offers.js', root), 'utf8');
let confirmation;
const ctx = vm.createContext({
    document: { addEventListener() {} }, window: {}, console,
    confirm: message => { confirmation = message; return false; },
    setTimeout() {}, setInterval() {}, clearInterval() {},
});
vm.runInContext(dashboard, ctx);
vm.runInContext(familyOffers, ctx);
vm.runInContext(`currentCourtship = ${JSON.stringify(fixture.courtship)}`, ctx);
await ctx.window.proposeMarriage('saver');
assert.ok(confirmation.includes(fixture.courtship.wedding_cost.toLocaleString('en-IN')));
assert.equal(vm.runInContext("_formatRevealedTrait('saver', 'income')", ctx), 'Authoritative reveal');
assert.equal(vm.runInContext("_formatRevealedTrait('anchor', 'income')", ctx), '?');
assert.ok((dashboard + familyOffers).includes('formatINR(offers.wedding_cost)'));
assert.ok(!dashboard.includes('88,000'));

const elements = new Map();
const get = id => {
    if (!elements.has(id)) elements.set(id, {
        id, value: '0', innerText: '', innerHTML: '', textContent: '', disabled: false,
        style: { setProperty() {} }, classList: { toggle() {} },
        addEventListener() {},
    });
    return elements.get(id);
};
const html = fs.readFileSync(new URL('allocation.html', root), 'utf8');
for (const match of html.matchAll(/<input[^>]*id="([^"]+)"[^>]*value="([^"]+)"/g)) get(match[1]).value = match[2];
const userInputs = ['valFood', 'valFamily', 'valStocks', 'valGold', 'valEmergency', 'valMisc'].map(get);
let ready;
const allocationContext = vm.createContext({
    window: { supabase: { auth: {
        getSession: async () => ({ data: { session: { access_token: 'test' } } }),
        onAuthStateChange() {},
    } }, location: {} },
    document: {
        addEventListener: (name, fn) => { ready = fn; },
        getElementById: get,
        querySelectorAll: () => userInputs,
        querySelector: get,
    },
    API_BASE_URL: 'http://local-test', console,
    fetch: async url => url.endsWith('/case-study')
        ? { ok: true, json: async () => fixture.economy }
        : { ok: false },
    setTimeout() {}, alert: message => { throw Error(message); },
});
vm.runInContext(fs.readFileSync(new URL('js/allocation.js', root), 'utf8'), allocationContext);
await ready();
assert.equal(Number(get('valRent').value), fixture.economy.lifestyles.city.rent);
assert.equal(get('btnSubmit').disabled, false);
allocationContext.window.selectLifestyle('outer');
assert.equal(Number(get('valRent').value), fixture.economy.lifestyles.outer.rent);
assert.equal(Number(get('valTransport').value), fixture.economy.lifestyles.outer.transport);
assert.ok(get('#radioOuter .radio-desc').textContent.includes(fixture.economy.lifestyles.outer.total.toLocaleString('en-IN')));
console.log('Wedding, reveal, expense and lifestyle-selector contracts pass.');
