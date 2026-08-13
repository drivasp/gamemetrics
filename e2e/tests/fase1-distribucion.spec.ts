import { test, expect } from '@playwright/test';
import {
  API,
  addToCartViaApi,
  getFirstFeaturedGame,
  loginViaUi,
  purchaseGameViaApi,
  registerViaApi,
  waitForLibraryItem,
} from './helpers';
import * as crypto from 'crypto';

/**
 * Fase 1 — distribución digital:
 * builds ZIP reales, download con checksum, install verify, Stripe UI, idempotencia.
 */

test.describe('Fase 1 · API distribución', () => {
  test('install → download ZIP real → verify checksum', async ({ request }) => {
    const { token } = await registerViaApi(request);
    const game = await getFirstFeaturedGame(request);
    await purchaseGameViaApi(request, token, game);
    await waitForLibraryItem(request, token, game.product_id);

    const install = await request.post(
      `${API}/launcher/install/${game.product_id}?game_name=${encodeURIComponent(game.name)}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    expect(install.ok(), `install: ${await install.text()}`).toBeTruthy();
    const installBody = await install.json();
    expect(installBody.download_token).toBeTruthy();
    expect(installBody.download_url).toContain('/launcher/download/');
    expect(installBody.build?.file_size_bytes).toBeGreaterThan(100);
    expect(installBody.build?.checksum).toBeTruthy();
    expect(installBody.build?.checksum.length).toBeGreaterThanOrEqual(16);

    const dl = await request.get(`${API}${installBody.download_url}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(dl.ok(), `download: ${dl.status()} ${await dl.text()}`).toBeTruthy();
    expect(dl.headers()['content-type'] || '').toContain('zip');
    const bytes = Buffer.from(await dl.body());
    expect(bytes.length).toBeGreaterThan(100);
    // ZIP magic bytes PK
    expect(bytes[0]).toBe(0x50);
    expect(bytes[1]).toBe(0x4b);

    const headerChecksum = dl.headers()['x-checksum-sha256'] || '';
    const localChecksum = crypto.createHash('sha256').update(bytes).digest('hex');
    if (headerChecksum) {
      expect(headerChecksum).toBe(localChecksum);
    }

    const verify = await request.post(`${API}/launcher/install/${game.product_id}/verify`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { checksum: localChecksum },
    });
    expect(verify.ok(), `verify: ${await verify.text()}`).toBeTruthy();
    const verified = await verify.json();
    expect(verified.install.status).toBe('installed');
    expect(verified.install.progress_pct).toBe(100);

    // Play requires installed
    const play = await request.post(`${API}/launcher/play/start`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { product_id: game.product_id, game_name: game.name },
    });
    expect(play.ok(), `play: ${await play.text()}`).toBeTruthy();
  });

  test('verify rechaza checksum incorrecto', async ({ request }) => {
    const { token } = await registerViaApi(request);
    const game = await getFirstFeaturedGame(request);
    await purchaseGameViaApi(request, token, game);
    await waitForLibraryItem(request, token, game.product_id);

    await request.post(
      `${API}/launcher/install/${game.product_id}?game_name=${encodeURIComponent(game.name)}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );

    const bad = await request.post(`${API}/launcher/install/${game.product_id}/verify`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { checksum: '0'.repeat(64) },
    });
    expect(bad.status()).toBe(400);
  });

  test('checkout respeta Idempotency-Key', async ({ request }) => {
    const { token } = await registerViaApi(request);
    const game = await getFirstFeaturedGame(request);

    await addToCartViaApi(request, token, game);

    const key = `e2e-idem-${Date.now()}`;
    const first = await request.post(`${API}/checkout`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Idempotency-Key': key,
      },
      data: { payment_method: 'sandbox' },
    });
    expect(first.ok(), `first checkout: ${await first.text()}`).toBeTruthy();

    // Same key again → empty cart (owned/cleared) or 409 idempotent
    const second = await request.post(`${API}/checkout`, {
      headers: {
        Authorization: `Bearer ${token}`,
        'Idempotency-Key': key,
      },
      data: { payment_method: 'sandbox' },
    });
    expect([400, 409]).toContain(second.status());
  });
});

test.describe('Fase 1 · UI', () => {
  test('pago muestra opción Stripe Checkout', async ({ page, request }) => {
    const { user, token } = await registerViaApi(request);
    const game = await getFirstFeaturedGame(request);
    await addToCartViaApi(request, token, game);

    await loginViaUi(page, user.email, user.password);
    await page.goto('/payment');
    await expect(page.getByRole('heading', { name: 'Continuar al pago' })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText('Stripe Checkout')).toBeVisible();
    await expect(page.getByLabel('Pago inmediato (sandbox)')).toBeVisible();
    await expect(page.getByLabel('Cartera GameMetrics')).toBeVisible();
  });

  test('biblioteca Instalar descarga y marca instalado', async ({ page, request }) => {
    const { user, token } = await registerViaApi(request);
    const game = await getFirstFeaturedGame(request);
    await purchaseGameViaApi(request, token, game);
    await waitForLibraryItem(request, token, game.product_id);

    await loginViaUi(page, user.email, user.password);
    await page.goto('/my-library');
    await expect(page.locator('body')).toContainText(game.name, { timeout: 20_000 });

    const card = page.locator('.lib-card').filter({ hasText: game.name });
    await card.getByRole('button', { name: 'Instalar' }).click();

    // Real download may take a few seconds
    await expect(card.getByRole('button', { name: 'Jugar' })).toBeVisible({ timeout: 60_000 });

    // Optional success popup
    const continueBtn = page.getByRole('button', { name: 'Continuar' });
    if (await continueBtn.isVisible().catch(() => false)) {
      await continueBtn.click();
    }

    await card.getByRole('button', { name: 'Jugar' }).click();
    await expect(page.locator('.play-overlay')).toBeVisible({ timeout: 15_000 });
    await page.getByRole('button', { name: 'Finalizar sesión' }).click();
    await expect(page.locator('.play-overlay')).toBeHidden({ timeout: 10_000 });
  });
});
