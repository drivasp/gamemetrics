import { test, expect } from '@playwright/test';
import {
  API,
  getFirstUnclaimedFeaturedGame,
  purchaseGameViaApi,
  registerViaApi,
  uniqueUser,
  waitForLibraryItem,
} from './helpers';

const BOOTSTRAP_SECRET = process.env.ROLE_BOOTSTRAP_SECRET ?? 'dev_bootstrap_roles';

function money(n: number) {
  return Math.round(n * 100) / 100;
}

test.describe('Fase 3–4 · payouts + SaaS', () => {
  test('admin liquida payout manual; SaaS pro + featured', async ({ request }) => {
    const pub = await registerViaApi(request, uniqueUser('US'));
    const reg = await request.post(`${API}/partners/register`, {
      headers: { Authorization: `Bearer ${pub.token}` },
      data: { company_name: `PayStudio ${Date.now().toString(36)}` },
    });
    expect(reg.ok(), await reg.text()).toBeTruthy();
    const partnerId = (await reg.json()).partner_id as string;

    const game = await getFirstUnclaimedFeaturedGame(request, pub.token);
    expect(game.price).toBeGreaterThan(0);

    for (let i = 0; i < 15; i++) {
      const me = await request.get(`${API}/partners/me`, {
        headers: { Authorization: `Bearer ${pub.token}` },
      });
      const body = await me.json();
      if ((body.games || []).some((g: { product_id: string }) => g.product_id === game.product_id)) break;
      await new Promise((r) => setTimeout(r, 800));
    }

    const buyer = await registerViaApi(request, uniqueUser('US'));
    await purchaseGameViaApi(request, buyer.token, game);
    await waitForLibraryItem(request, buyer.token, game.product_id);

    const net = money(Number(game.price) * 0.7);

    let available = 0;
    for (let i = 0; i < 20; i++) {
      const me = await request.get(`${API}/partners/me`, {
        headers: { Authorization: `Bearer ${pub.token}` },
      });
      const e = (await me.json()).earnings;
      available = money(e?.balance_available ?? 0);
      if (available >= net - 0.05) break;
      await new Promise((r) => setTimeout(r, 800));
    }
    expect(available).toBeGreaterThanOrEqual(net - 0.05);

    const adminUser = uniqueUser('US');
    const boot = await request.post(`${API}/auth/bootstrap-admin`, {
      data: {
        email: adminUser.email,
        password: adminUser.password,
        secret: BOOTSTRAP_SECRET,
        country_code: 'US',
      },
    });
    expect(boot.ok(), await boot.text()).toBeTruthy();
    const adminToken = (await boot.json()).token as string;

    const payout = await request.post(`${API}/admin/payouts`, {
      headers: { Authorization: `Bearer ${adminToken}` },
      data: {
        partner_id: partnerId,
        amount: available,
        method: 'manual',
        reference: `WIRE-E2E-${Date.now().toString(36)}`,
        notes: 'e2e',
      },
    });
    expect(payout.ok(), await payout.text()).toBeTruthy();

    const meAfter = await request.get(`${API}/partners/me`, {
      headers: { Authorization: `Bearer ${pub.token}` },
    });
    const after = await meAfter.json();
    expect(money(after.earnings.balance_available)).toBeLessThanOrEqual(0.05);
    expect((after.payouts || []).length).toBeGreaterThan(0);

    // SaaS Pro (sandbox sin Stripe)
    const sub = await request.post(`${API}/partners/saas/subscribe`, {
      headers: { Authorization: `Bearer ${pub.token}` },
      data: { plan_id: 'pro', pay_method: 'sandbox' },
    });
    expect(sub.ok(), await sub.text()).toBeTruthy();
    const subBody = await sub.json();
    expect(subBody.subscription?.plan_id || subBody.mode).toBeTruthy();

    const brand = await request.put(`${API}/partners/branding`, {
      headers: { Authorization: `Bearer ${pub.token}` },
      data: {
        store_name: 'E2E White Label Store',
        accent_color: '#66c0f4',
        tagline: 'Indie forever',
      },
    });
    expect(brand.ok(), await brand.text()).toBeTruthy();

    const feat = await request.post(`${API}/partners/featured/buy`, {
      headers: { Authorization: `Bearer ${pub.token}` },
      data: {
        product_id: game.product_id,
        game_name: game.name,
        pay_method: 'sandbox',
      },
    });
    expect(feat.ok(), await feat.text()).toBeTruthy();
    const featBody = await feat.json();
    expect(featBody.placement || featBody.mode === 'sandbox').toBeTruthy();
  });
});
