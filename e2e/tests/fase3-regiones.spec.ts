import { test, expect } from '@playwright/test';
import {
  API,
  getFirstFeaturedGame,
  registerViaApi,
  addToCartViaApi,
  uniqueUser,
  registerViaUi,
} from './helpers';

/**
 * Fase 3 — regiones de precio + impuestos por país.
 * País de residencia se fija al registrarse (estilo Steam).
 */

function waitMs(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

async function waitPinot<T>(fn: () => Promise<T | null>, maxMs = 25_000): Promise<T> {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    const v = await fn();
    if (v) return v;
    await waitMs(1000);
  }
  throw new Error('timeout waiting for Pinot lag');
}

test.describe('Fase 3 · regiones e impuestos', () => {
  test('catálogo público: LATAM más barato que US; EU distinto', async ({ request }) => {
    const us = await request.get(`${API}/store/featured?country=US`);
    const mx = await request.get(`${API}/store/featured?country=MX`);
    const es = await request.get(`${API}/store/featured?country=ES`);
    expect(us.ok()).toBeTruthy();
    expect(mx.ok()).toBeTruthy();
    expect(es.ok()).toBeTruthy();

    const usGames = await us.json();
    const mxGames = await mx.json();
    const esGames = await es.json();
    expect(usGames.length).toBeGreaterThan(0);

    const paidUs = usGames.find((g: { price: number }) => g.price > 0);
    expect(paidUs).toBeTruthy();
    const paidMx = mxGames.find((g: { product_id: string }) => g.product_id === paidUs.product_id);
    const paidEs = esGames.find((g: { product_id: string }) => g.product_id === paidUs.product_id);
    expect(paidMx).toBeTruthy();
    expect(paidEs).toBeTruthy();

    expect(paidMx.price).toBeLessThan(paidUs.price);
    expect(paidMx.pricing_region).toBe('LATAM');
    expect(paidEs.pricing_region).toBe('EU');
    expect(paidEs.currency).toBe('EUR');
    expect(Math.abs(paidMx.price / paidUs.price - 0.85)).toBeLessThan(0.03);
  });

  test('registro MX fija IVA 16% en carrito (sin cambio libre)', async ({ request }) => {
    const { token } = await registerViaApi(request, uniqueUser('MX'));

    const me = await request.get(`${API}/locale/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(me.ok()).toBeTruthy();
    const loc = await me.json();
    expect(loc.country_code).toBe('MX');
    expect(loc.tax_rate_pct).toBe(16);
    expect(loc.locked).toBeTruthy();

    // Intento de evasión: cambiar a US → 403
    const dodge = await request.put(`${API}/locale/me`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { country_code: 'US' },
    });
    expect(dodge.status()).toBe(403);

    const mxFeat = await request.get(`${API}/store/featured?country=MX`);
    const mxGames = await mxFeat.json();
    const regional = mxGames.find((g: { price: number }) => g.price > 0)
      || await getFirstFeaturedGame(request);

    await addToCartViaApi(request, token, {
      product_id: regional.product_id,
      slug: regional.slug,
      name: regional.name,
      background_image: regional.background_image,
      price: regional.price,
    });

    const cart = await waitPinot(async () => {
      const res = await request.get(`${API}/cart`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok()) return null;
      const body = await res.json();
      if (!body.items?.length) return null;
      if (body.country_code !== 'MX') return null;
      return body;
    });

    expect(cart.tax_rate_pct).toBe(16);
    expect(cart.tax_amount).toBeCloseTo(cart.total * 0.16, 1);
  });

  test('checkout sandbox MX cobra IVA del país de registro', async ({ request }) => {
    const { token } = await registerViaApi(request, uniqueUser('MX'));

    const mxFeat = await request.get(`${API}/store/featured?country=MX`);
    const games = await mxFeat.json();
    const game = games.find((g: { price: number }) => g.price > 1) || games[0];
    expect(game).toBeTruthy();

    await addToCartViaApi(request, token, {
      product_id: game.product_id,
      slug: game.slug,
      name: game.name,
      background_image: game.background_image,
      price: game.price,
    });

    await waitPinot(async () => {
      const res = await request.get(`${API}/cart`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok()) return null;
      const body = await res.json();
      return body.items?.length && body.country_code === 'MX' ? body : null;
    });

    const pay = await request.post(`${API}/checkout`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { payment_method: 'sandbox' },
    });
    expect(pay.ok(), await pay.text()).toBeTruthy();
    const result = await pay.json();
    expect(result.status).toBe('success');
    expect(result.country_code).toBe('MX');
    expect(result.tax_rate_pct).toBe(16);
    expect(result.tax_amount).toBeGreaterThan(0);
  });

  test('UI: registro pide país y queda bloqueado en navbar', async ({ page }) => {
    const user = uniqueUser('EC');
    await registerViaUi(page, user);
    await expect(page.locator('.region-trigger.locked')).toBeVisible({ timeout: 20_000 });
    await expect(page.locator('.region-trigger .region-label')).toHaveText(/Ecuador/i);
    await page.locator('.region-trigger').click();
    await expect(page.locator('.region-locked-panel')).toBeVisible();
    await expect(page.locator('.region-locked-msg')).toContainText(/no se puede cambiar/i);
    // No hay lista de países para cambiar
    await expect(page.locator('.region-option')).toHaveCount(0);
  });
});
