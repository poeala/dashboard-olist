import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const context = vm.createContext({ Intl });
vm.runInContext(readFileSync(new URL('../../assets/01_logistics_scale.js', import.meta.url), 'utf8'), context);
const { rateScale } = context.LogisticsMapScale;

test('regional delays below 20% span the palette instead of sharing one color', () => {
  const values = [3, 5, 7, 9, 11];
  const scale = rateScale(values);
  assert.equal(new Set(values.map(scale.colorFor)).size, 5);
  assert.equal(scale.colorFor(3), scale.bins[0].color);
  assert.equal(scale.colorFor(11), scale.bins.at(-1).color);
  assert.equal(scale.bins[0].label, '3–<4,6 %');
  assert.equal(scale.bins.at(-1).label, '9,4–11 %');
  assert.equal(scale.colorFor(4.6), scale.bins[1].color);
});

test('scale recalculates for the selected period and preserves narrow differences', () => {
  const broad = rateScale([0, 20]);
  const narrow = rateScale([5.1, 5.2, 5.3, 5.4, 5.5]);
  assert.notEqual(broad.colorFor(5.5), narrow.colorFor(5.5));
  assert.equal(new Set([5.1, 5.2, 5.3, 5.4, 5.5].map(narrow.colorFor)).size, 5);
});

test('equal rates and zero delays have one honest legend entry', () => {
  for (const value of [0, 8.33, 100]) {
    const scale = rateScale([value, value, null]);
    assert.equal(scale.bins.length, 1);
    assert.equal(scale.colorFor(value), scale.bins[0].color);
    assert.notEqual(scale.colorFor(null), scale.colorFor(value));
  }
});

test('missing rates do not set scale limits or masquerade as zero delays', () => {
  const scale = rateScale([null, undefined, NaN, 7, 10]);
  assert.equal(scale.bins[0].label.startsWith('7–'), true);
  for (const value of [null, undefined, NaN]) assert.equal(scale.colorFor(value), '#dce3eb');
  const empty = rateScale([null, null]);
  assert.equal(empty.bins.length, 0);
  assert.equal(empty.colorFor(null), '#dce3eb');
});
