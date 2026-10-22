import test from 'node:test';
import assert from 'node:assert/strict';
import { areas, views, selectedArea, selectedView, dashboardUrl, checkDashboard } from '../src/dashboard.js';

test('una vista desconocida usa Gerencial; los enlaces conservan la vista', () => {
  assert.equal(selectedView('?vista=invalida').id, 'gerencial');
  assert.equal(selectedView('?vista=analitica').id, 'analitica');
  assert.equal(dashboardUrl('decisiones'), '/dashboard/?area=ventas&vista=decisiones&embed=1');
  assert.equal(dashboardUrl('analitica', false), '/dashboard/?area=ventas&vista=analitica');
});

test('cada enlace conserva su área y vista; áreas inválidas vuelven a Ventas', () => {
  for (const area of areas) {
    for (const view of views) {
      const url = new URL(dashboardUrl(view.id, true, area.id), 'http://localhost');
      assert.equal(selectedArea(url.search).id, area.id);
      assert.equal(selectedView(url.search).id, view.id);
      assert.equal(url.searchParams.get('embed'), '1');
    }
  }
  assert.equal(selectedArea('?area=desconocida').id, 'ventas');
  assert.equal(selectedArea('?area=pagos').id, 'pagos');
});
test('el HTML del fallback de una SPA no cuenta como un backend saludable', async (t) => {
  t.mock.method(globalThis, 'fetch', async () => new Response('<html></html>'));
  await assert.rejects(checkDashboard());
});

test('rechaza HTTP 503 y servicios ajenos, acepta la salud del dashboard', async (t) => {
  const mock = t.mock.method(globalThis, 'fetch', async () => new Response('', { status: 503 }));
  await assert.rejects(checkDashboard());
  mock.mock.mockImplementation(async () => Response.json({ status: 'ok' }));
  await assert.rejects(checkDashboard());
  mock.mock.mockImplementation(async () => Response.json({ status: 'ok', service: 'olist-dashboard' }));
  await assert.doesNotReject(checkDashboard());
});
