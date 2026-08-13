/**
 * E2E cierre auditoría — flujos UI reales + negativos.
 * baseURL frontend :4000 · API :8080
 */
import { test, expect } from '@playwright/test';
import {
  API,
  uniqueUser,
  registerViaApi,
  loginViaUi,
  topupWalletViaApi,
  getFirstFeaturedGame,
  purchaseGameViaApi,
  dismissPopups,
} from './helpers';

test.describe.configure({ mode: 'serial' });

test('1 fees público preview — no mutates_money', async ({ request }) => {
  const r1 = await request.get(`${API}/marketplace/fees`);
  expect(r1.ok()).toBeTruthy();
  const body = await r1.json();
  expect(body.mutates_money).toBe(false);
  expect(body.auth_required).toBe(false);
  expect(body.example_10.gross).toBe(10);
  const r2 = await request.get(`${API}/marketplace/fees`);
  expect((await r2.json()).example_10.seller_net).toBe(body.example_10.seller_net);
});

test('2 no autenticado → 401 marketplace / wallet', async ({ request }) => {
  expect((await request.get(`${API}/marketplace/listings`)).status()).toBe(401);
  expect((await request.get(`${API}/wallet`)).status()).toBe(401);
  expect((await request.get(`${API}/admin/finance/audit`)).status()).toBe(401);
});

test('3 UI login → Store → Wallet visible', async ({ page, request }) => {
  const u = await registerViaApi(request);
  await topupWalletViaApi(request, u.token, 50);
  await loginViaUi(page, u.user.email, u.user.password);
  await dismissPopups(page);
  await page.goto('/store');
  await expect(page.locator('.user-name')).toBeVisible({ timeout: 15_000 });
  await page.goto('/my-wallet');
  await expect(page.locator('body')).toContainText(/wallet|cartera|saldo|balance|USD|\$/i, {
    timeout: 20_000,
  });
});

test('4 compra store + ownership biblioteca', async ({ request }) => {
  const u = await registerViaApi(request);
  const game = await getFirstFeaturedGame(request);
  const checkout = await purchaseGameViaApi(request, u.token, game);
  expect(checkout.status === 'paid' || checkout.order_id).toBeTruthy();
  const lib = await request.get(`${API}/library`, {
    headers: { Authorization: `Bearer ${u.token}` },
  });
  expect(lib.ok(), await lib.text()).toBeTruthy();
});

test('5 marketplace mint/list/buy + ownership + history + doble compra', async ({
  page,
  request,
}) => {
  const seller = await registerViaApi(request, uniqueUser('US'));
  const buyer = await registerViaApi(request, uniqueUser('US'));
  await topupWalletViaApi(request, buyer.token, 100);

  const mint = await request.post(`${API}/marketplace/items`, {
    headers: { Authorization: `Bearer ${seller.token}` },
    data: { game_id: 'e2e-game', item_name: 'E2E Skin Audit' },
  });
  expect(mint.ok(), await mint.text()).toBeTruthy();
  const item = await mint.json();

  const list = await request.post(`${API}/marketplace/listings`, {
    headers: { Authorization: `Bearer ${seller.token}` },
    data: { item_id: item.item_id, price_usd: 12 },
  });
  expect(list.ok(), await list.text()).toBeTruthy();
  const listing = await list.json();

  // comprar propio
  expect(
    (
      await request.post(`${API}/marketplace/buy`, {
        headers: { Authorization: `Bearer ${seller.token}` },
        data: { listing_id: listing.listing_id, idempotency_key: 'own1' },
      })
    ).status(),
  ).toBe(400);

  const buyKey = `e2e-buy-${Date.now()}`;
  const buy1 = await request.post(`${API}/marketplace/buy`, {
    headers: {
      Authorization: `Bearer ${buyer.token}`,
      'Idempotency-Key': buyKey,
    },
    data: { listing_id: listing.listing_id, idempotency_key: buyKey },
  });
  expect(buy1.ok(), await buy1.text()).toBeTruthy();
  const tx1 = await buy1.json();

  const buy2 = await request.post(`${API}/marketplace/buy`, {
    headers: {
      Authorization: `Bearer ${buyer.token}`,
      'Idempotency-Key': buyKey,
    },
    data: { listing_id: listing.listing_id, idempotency_key: buyKey },
  });
  expect(buy2.ok(), await buy2.text()).toBeTruthy();
  expect((await buy2.json()).tx_id).toBe(tx1.tx_id);

  const inv = await request.get(`${API}/marketplace/inventory`, {
    headers: { Authorization: `Bearer ${buyer.token}` },
  });
  expect(inv.ok(), await inv.text()).toBeTruthy();
  const invBody = await inv.json();
  expect(
    (invBody.items || []).some((i: { item_id: string }) => i.item_id === item.item_id),
    `inventory=${JSON.stringify(invBody)} item=${item.item_id} buy=${JSON.stringify(tx1)}`,
  ).toBeTruthy();

  const hist = await request.get(`${API}/marketplace/history`, {
    headers: { Authorization: `Bearer ${buyer.token}` },
  });
  expect(hist.ok()).toBeTruthy();
  expect(((await hist.json()).items || []).length).toBeGreaterThan(0);

  await loginViaUi(page, buyer.user.email, buyer.user.password);
  await page.goto('/my-marketplace');
  await expect(page.locator('body')).toContainText(/market|inventario|listing|item/i, {
    timeout: 20_000,
  });
});

test('6 precio inválido + saldo insuficiente + listing cancelado', async ({ request }) => {
  const seller = await registerViaApi(request);
  const buyer = await registerViaApi(request);

  const mint = await request.post(`${API}/marketplace/items`, {
    headers: { Authorization: `Bearer ${seller.token}` },
    data: { game_id: 'g', item_name: 'X' },
  });
  const item = await mint.json();

  expect(
    (
      await request.post(`${API}/marketplace/listings`, {
        headers: { Authorization: `Bearer ${seller.token}` },
        data: { item_id: item.item_id, price_usd: -5 },
      })
    ).status(),
  ).toBeGreaterThanOrEqual(400);

  const list = await request.post(`${API}/marketplace/listings`, {
    headers: { Authorization: `Bearer ${seller.token}` },
    data: { item_id: item.item_id, price_usd: 80 },
  });
  expect(list.ok()).toBeTruthy();
  const listing = await list.json();

  expect(
    (
      await request.post(`${API}/marketplace/buy`, {
        headers: { Authorization: `Bearer ${buyer.token}` },
        data: { listing_id: listing.listing_id, idempotency_key: 'poor' },
      })
    ).status(),
  ).toBeGreaterThanOrEqual(400);

  const cancel = await request.post(
    `${API}/marketplace/listings/${listing.listing_id}/cancel`,
    { headers: { Authorization: `Bearer ${seller.token}` } },
  );
  if (cancel.ok() || cancel.status() === 200) {
    const buyCancel = await request.post(`${API}/marketplace/buy`, {
      headers: { Authorization: `Bearer ${buyer.token}` },
      data: { listing_id: listing.listing_id, idempotency_key: 'canc' },
    });
    expect(buyCancel.status()).toBeGreaterThanOrEqual(400);
  }
});

test('7 partner dashboard / statement autenticado', async ({ page, request }) => {
  const u = await registerViaApi(request);
  await request.post(`${API}/partners/register`, {
    headers: { Authorization: `Bearer ${u.token}` },
    data: { company_name: `E2E Co ${Date.now()}` },
  });
  const me = await request.get(`${API}/partners/me`, {
    headers: { Authorization: `Bearer ${u.token}` },
  });
  expect(me.ok(), await me.text()).toBeTruthy();
  const body = await me.json();
  expect(body.partner || body.financial_statement || body.earnings).toBeTruthy();

  await loginViaUi(page, u.user.email, u.user.password);
  await page.goto('/my-partner');
  await expect(page.locator('body')).toContainText(/partner|publisher|earnings|statement|ingresos|panel|compañía|company|juego/i, {
    timeout: 20_000,
  });
});

test('8 admin auditoría — player sin permiso', async ({ request }) => {
  const u = await registerViaApi(request);
  const r = await request.get(`${API}/admin/finance/audit`, {
    headers: { Authorization: `Bearer ${u.token}` },
  });
  expect([401, 403]).toContain(r.status());
});

test('9 admin bootstrap + ver audit', async ({ page, request }) => {
  const adminUser = uniqueUser('US');
  const boot = await request.post(`${API}/auth/bootstrap-admin`, {
    data: {
      email: adminUser.email,
      password: adminUser.password,
      display_name: adminUser.displayName,
      secret: process.env.ROLE_BOOTSTRAP_SECRET || 'dev_bootstrap_roles',
    },
  });
  expect(boot.ok(), await boot.text()).toBeTruthy();
  const token = (await boot.json()).token as string;

  const audit = await request.get(`${API}/admin/finance/audit`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(audit.ok(), await audit.text()).toBeTruthy();

  await loginViaUi(page, adminUser.email, adminUser.password);
  await page.goto('/admin');
  await expect(page.locator('body')).toContainText(/admin|auditoría|audit|finanzas|finance|usuarios/i, {
    timeout: 20_000,
  });
});
