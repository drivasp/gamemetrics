import { test, expect } from '@playwright/test';
import {
  API,
  getFirstFeaturedGame,
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

/**
 * Ledger B2B: atribución partner + fee + neto en cada venta / reembolso.
 */
test.describe('Dinero · partner ledger', () => {
  test('venta atribuye gross/fee/neto; admin ve GMV; refund invierte', async ({
    request,
  }) => {
    const game = await getFirstFeaturedGame(request);
    expect(game.price).toBeGreaterThan(0);

    // Publisher
    const pub = await registerViaApi(request, uniqueUser('US'));
    const regPartner = await request.post(`${API}/partners/register`, {
      headers: { Authorization: `Bearer ${pub.token}` },
      data: { company_name: `Ledger Studio ${Date.now().toString(36)}` },
    });
    expect(regPartner.ok(), await regPartner.text()).toBeTruthy();
    expect((await regPartner.json()).role).toBe('publisher');

    const claimed = await getFirstUnclaimedFeaturedGame(request, pub.token);
    expect(claimed.price).toBeGreaterThan(0);

    // Esperar indexación partner_games (Pinot)
    let attributed = false;
    for (let i = 0; i < 20; i++) {
      const me = await request.get(`${API}/partners/me`, {
        headers: { Authorization: `Bearer ${pub.token}` },
      });
      const body = await me.json();
      if ((body.games || []).some((g: { product_id: string }) => g.product_id === claimed.product_id)) {
        attributed = true;
        break;
      }
      await new Promise((r) => setTimeout(r, 1000));
    }
    expect(attributed, 'partner_game no indexó a tiempo').toBeTruthy();

    // Buyer compra el juego del publisher
    const buyer = await registerViaApi(request, uniqueUser('US'));
    const checkout = await purchaseGameViaApi(request, buyer.token, claimed);
    expect(checkout.status === 'paid' || checkout.order_id).toBeTruthy();
    await waitForLibraryItem(request, buyer.token, claimed.product_id);

    // Earnings: la venta puede tener precio de checkout distinto al featured list price.
    let earningsOk = false;
    let earnings: any = null;
    let sale: any = null;
    const publicationFee = 100; // charged on claim approve (PUBLICATION_FEE_USD)
    for (let i = 0; i < 25; i++) {
      const me = await request.get(`${API}/partners/me`, {
        headers: { Authorization: `Bearer ${pub.token}` },
      });
      expect(me.ok(), await me.text()).toBeTruthy();
      const body = await me.json();
      earnings = body.earnings;
      sale = (body.ledger || []).find(
        (e: { entry_type: string; product_id: string }) =>
          e.entry_type === 'sale' && e.product_id === claimed.product_id,
      );
      if (sale && Number(sale.gross_amount) > 0) {
        earningsOk = true;
        const saleGross = money(Number(sale.gross_amount));
        const saleNet = money(saleGross * 0.7);
        const saleFee = money(saleGross - saleNet);
        expect(money(Number(sale.publisher_net_amount))).toBeCloseTo(saleNet, 1);
        expect(money(Number(sale.platform_fee_amount))).toBeCloseTo(saleFee, 1);
        const expectedNet = money(saleNet - publicationFee);
        expect(money(earnings.publisher_net)).toBeCloseTo(expectedNet, 1);
        expect(money(earnings.gross_revenue)).toBeCloseTo(saleGross, 1);
        expect((body.ledger || []).length).toBeGreaterThan(0);
        break;
      }
      await new Promise((r) => setTimeout(r, 1000));
    }
    expect(earningsOk, `earnings no reflejaron la venta: ${JSON.stringify({ earnings, sale })}`).toBeTruthy();
    const saleGross = money(Number(sale.gross_amount));
    const saleFee = money(saleGross - money(saleGross * 0.7));

    // Admin GMV
    const adminUser = uniqueUser('US');
    const boot = await request.post(`${API}/auth/bootstrap-admin`, {
      data: {
        email: adminUser.email,
        password: adminUser.password,
        display_name: 'Ledger Admin',
        secret: BOOTSTRAP_SECRET,
        country_code: 'US',
      },
    });
    expect(boot.ok(), await boot.text()).toBeTruthy();
    const adminToken = (await boot.json()).token as string;

    const gmvRes = await request.get(`${API}/admin/dashboard`, {
      headers: { Authorization: `Bearer ${adminToken}` },
    });
    expect(gmvRes.ok(), await gmvRes.text()).toBeTruthy();
    const gmv = await gmvRes.json();
    expect(gmv.ok).toBeTruthy();
    expect(Number(gmv.gmv)).toBeGreaterThanOrEqual(saleGross - 0.01);
    expect(Number(gmv.platform_revenue)).toBeGreaterThanOrEqual(saleFee - 0.01);
    expect(Array.isArray(gmv.partners)).toBeTruthy();
    const listed = (gmv.partners as Array<{ gross_revenue: number; company_name: string; publisher_share_pct: number; status: string }>)
      .find((p) => Number(p.gross_revenue) >= saleGross - 0.01);
    expect(listed, 'partner no aparece en dashboard admin').toBeTruthy();
    expect(listed!.company_name).toBeTruthy();
    expect(listed!.publisher_share_pct).toBe(70);
    expect(listed!.status).toBeTruthy();

    // Player no puede ver dashboard
    const denied = await request.get(`${API}/admin/dashboard`, {
      headers: { Authorization: `Bearer ${buyer.token}` },
    });
    expect(denied.status()).toBe(403);

    // Refund invierte neto
    const purchaseId = `${buyer.userId}_${claimed.product_id}`;
    const refund = await request.post(`${API}/refunds`, {
      headers: { Authorization: `Bearer ${buyer.token}` },
      data: { purchase_id: purchaseId, reason: 'E2E ledger refund' },
    });
    expect(refund.ok(), await refund.text()).toBeTruthy();

    let refundedOk = false;
    for (let i = 0; i < 20; i++) {
      const me = await request.get(`${API}/partners/me`, {
        headers: { Authorization: `Bearer ${pub.token}` },
      });
      const body = await me.json();
      const hasRefund = (body.ledger || []).some(
        (e: { entry_type: string }) => e.entry_type === 'refund',
      );
      if (hasRefund) {
        refundedOk = true;
        // Venta+refund se anulan; queda el direct_fee de publicación (-$100)
        expect(money(body.earnings.gross_revenue)).toBeCloseTo(0, 1);
        expect(money(body.earnings.publisher_net)).toBeCloseTo(-publicationFee, 1);
        expect(money(body.earnings.balance_available ?? 0)).toBe(0);
        break;
      }
      await new Promise((r) => setTimeout(r, 1000));
    }
    expect(refundedOk, 'refund no revirtió el saldo del publisher').toBeTruthy();
  });

  test('juego sin partner no genera earnings fantasma', async ({ request }) => {
    const game = await getFirstFeaturedGame(request);
    const buyer = await registerViaApi(request);
    await purchaseGameViaApi(request, buyer.token, game);
    await waitForLibraryItem(request, buyer.token, game.product_id);

    // Publisher nuevo sin claim de ese product_id
    const pub = await registerViaApi(request, uniqueUser('US'));
    await request.post(`${API}/partners/register`, {
      headers: { Authorization: `Bearer ${pub.token}` },
      data: { company_name: `Empty Studio ${Date.now().toString(36)}` },
    });
    const me = await request.get(`${API}/partners/me`, {
      headers: { Authorization: `Bearer ${pub.token}` },
    });
    const body = await me.json();
    expect(money(body.earnings?.gross_revenue ?? 0)).toBe(0);
    expect((body.ledger || []).length).toBe(0);
  });
});
