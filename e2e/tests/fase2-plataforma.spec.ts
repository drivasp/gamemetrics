import { test, expect } from '@playwright/test';
import {
  API,
  getFirstFeaturedGame,
  purchaseGameViaApi,
  registerViaApi,
  waitForLibraryItem,
} from './helpers';
import * as crypto from 'crypto';

/**
 * Fase 2 — updates, cloud saves, presence, publisher upload.
 */

function waitMs(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

async function waitPinot<T>(fn: () => Promise<T | null>, maxMs = 20_000): Promise<T> {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    const v = await fn();
    if (v) return v;
    await waitMs(1000);
  }
  throw new Error('timeout waiting for Pinot lag');
}

function makeTinyZip(extra = ''): Buffer {
  // Minimal valid ZIP with one file (store method)
  const name = Buffer.from('readme.txt');
  const data = Buffer.from(`GameMetrics build ${extra || Date.now()}\n`);
  const localHeader = Buffer.alloc(30 + name.length);
  localHeader.writeUInt32LE(0x04034b50, 0);
  localHeader.writeUInt16LE(20, 4);
  localHeader.writeUInt16LE(0, 6);
  localHeader.writeUInt16LE(0, 8); // store
  localHeader.writeUInt16LE(0, 10);
  localHeader.writeUInt16LE(0, 12);
  const crc = crc32(data);
  localHeader.writeUInt32LE(crc, 14);
  localHeader.writeUInt32LE(data.length, 18);
  localHeader.writeUInt32LE(data.length, 22);
  localHeader.writeUInt16LE(name.length, 26);
  localHeader.writeUInt16LE(0, 28);
  name.copy(localHeader, 30);

  const central = Buffer.alloc(46 + name.length);
  central.writeUInt32LE(0x02014b50, 0);
  central.writeUInt16LE(20, 4);
  central.writeUInt16LE(20, 6);
  central.writeUInt16LE(0, 8);
  central.writeUInt16LE(0, 10);
  central.writeUInt16LE(0, 12);
  central.writeUInt16LE(0, 14);
  central.writeUInt32LE(crc, 16);
  central.writeUInt32LE(data.length, 20);
  central.writeUInt32LE(data.length, 24);
  central.writeUInt16LE(name.length, 28);
  central.writeUInt16LE(0, 30);
  central.writeUInt16LE(0, 32);
  central.writeUInt16LE(0, 34);
  central.writeUInt16LE(0, 36);
  central.writeUInt32LE(0, 38);
  central.writeUInt32LE(0, 42);
  name.copy(central, 46);

  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(0, 4);
  end.writeUInt16LE(0, 6);
  end.writeUInt16LE(1, 8);
  end.writeUInt16LE(1, 10);
  end.writeUInt32LE(central.length, 12);
  end.writeUInt32LE(localHeader.length + data.length, 16);
  end.writeUInt16LE(0, 20);

  return Buffer.concat([localHeader, data, central, end]);
}

function crc32(buf: Buffer): number {
  let c = ~0;
  for (let i = 0; i < buf.length; i++) {
    c ^= buf[i];
    for (let k = 0; k < 8; k++) {
      c = (c >>> 1) ^ (0xedb88320 & -(c & 1));
    }
  }
  return ~c >>> 0;
}

test.describe('Fase 2 · API plataforma', () => {
  test('presence heartbeat marca amigo online', async ({ request }) => {
    const a = await registerViaApi(request);
    const b = await registerViaApi(request);

    const req = await request.post(`${API}/friends/request`, {
      headers: { Authorization: `Bearer ${a.token}` },
      data: { email: b.user.email },
    });
    expect(req.ok(), await req.text()).toBeTruthy();
    const body = await req.json();

    await waitPinot(async () => {
      const list = await request.get(`${API}/friends`, {
        headers: { Authorization: `Bearer ${b.token}` },
      });
      if (!list.ok()) return null;
      const j = await list.json();
      return (j.incoming || []).find((x: any) => x.friendship_id === body.friendship_id) || null;
    });

    const accept = await request.post(`${API}/friends/${body.friendship_id}/accept`, {
      headers: { Authorization: `Bearer ${b.token}` },
    });
    expect(accept.ok(), await accept.text()).toBeTruthy();

    await request.post(`${API}/friends/presence`, {
      headers: { Authorization: `Bearer ${a.token}` },
      data: { status: 'online' },
    });

    const online = await waitPinot(async () => {
      const list = await request.get(`${API}/friends`, {
        headers: { Authorization: `Bearer ${b.token}` },
      });
      if (!list.ok()) return null;
      const j = await list.json();
      const f = (j.friends || []).find(
        (x: any) => x.user?.email === a.user.email || x.user?.user_id,
      );
      if (f?.online || f?.presence === 'online' || f?.presence === 'playing') return f;
      return null;
    }, 25_000);

    expect(online.online || online.presence === 'online').toBeTruthy();
  });

  test('cloud save PUT/GET roundtrip', async ({ request }) => {
    const { token } = await registerViaApi(request);
    const game = await getFirstFeaturedGame(request);
    await purchaseGameViaApi(request, token, game);
    await waitForLibraryItem(request, token, game.product_id);

    const put = await request.put(`${API}/saves/${game.product_id}`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { slot: 0, label: 'E2E', data: { score: 42, level: 3 } },
    });
    expect(put.ok(), `put save: ${await put.text()}`).toBeTruthy();

    const got = await waitPinot(async () => {
      const g = await request.get(`${API}/saves/${game.product_id}/0`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!g.ok()) return null;
      const j = await g.json();
      return j?.data?.score === 42 ? j : null;
    });

    expect(got.data.score).toBe(42);
    expect(got.checksum).toBeTruthy();
  });

  test('partner upload → update available → install update', async ({ request }) => {
    const { token } = await registerViaApi(request);
    const game = await getFirstFeaturedGame(request);
    await purchaseGameViaApi(request, token, game);
    await waitForLibraryItem(request, token, game.product_id);

    // Install baseline
    const install = await request.post(
      `${API}/launcher/install/${game.product_id}?game_name=${encodeURIComponent(game.name)}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    expect(install.ok(), await install.text()).toBeTruthy();
    const ib = await install.json();
    const dl = await request.get(`${API}${ib.download_url}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(dl.ok()).toBeTruthy();
    const bytes = Buffer.from(await dl.body());
    const checksum = crypto.createHash('sha256').update(bytes).digest('hex');
    const verify = await request.post(`${API}/launcher/install/${game.product_id}/verify`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { checksum },
    });
    expect(verify.ok(), await verify.text()).toBeTruthy();

    // Become publisher and attach this product
    const reg = await request.post(`${API}/partners/register`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { company_name: `E2E Studio ${Date.now()}` },
    });
    expect(reg.ok() || reg.status() === 409, await reg.text()).toBeTruthy();

    const add = await request.post(`${API}/partners/games`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { product_id: game.product_id, game_name: game.name },
    });
    expect(add.ok() || add.status() === 409, await add.text()).toBeTruthy();

    await waitMs(1500);

    const zip = makeTinyZip('v2');
    const version = `2.${Date.now() % 10000}.0`;
    const upload = await request.post(`${API}/partners/games/${game.product_id}/builds`, {
      headers: { Authorization: `Bearer ${token}` },
      multipart: {
        version,
        file: {
          name: 'build.zip',
          mimeType: 'application/zip',
          buffer: zip,
        },
      },
    });
    expect(upload.ok(), `upload: ${await upload.text()}`).toBeTruthy();

    const upd = await waitPinot(async () => {
      const r = await request.get(
        `${API}/launcher/updates/${game.product_id}?game_name=${encodeURIComponent(game.name)}`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!r.ok()) return null;
      const j = await r.json();
      return j.update_available ? j : null;
    }, 30_000);

    expect(upd.update_available).toBeTruthy();
    expect(upd.latest_build?.version).toBeTruthy();

    const startUpd = await request.post(
      `${API}/launcher/install/${game.product_id}/update?game_name=${encodeURIComponent(game.name)}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    expect(startUpd.ok(), await startUpd.text()).toBeTruthy();
    const ub = await startUpd.json();
    expect(ub.download_url).toBeTruthy();

    const dl2 = await request.get(`${API}${ub.download_url}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(dl2.ok()).toBeTruthy();
    const bytes2 = Buffer.from(await dl2.body());
    expect(bytes2[0]).toBe(0x50);
    expect(bytes2[1]).toBe(0x4b);
    const cs2 = crypto.createHash('sha256').update(bytes2).digest('hex');
    const v2 = await request.post(`${API}/launcher/install/${game.product_id}/verify`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { checksum: cs2 },
    });
    expect(v2.ok(), await v2.text()).toBeTruthy();
  });
});

test.describe('Fase 2 · UI', () => {
  test('amigos muestra indicador de presencia', async ({ page, request }) => {
    const a = await registerViaApi(request);
    const b = await registerViaApi(request);

    const req = await request.post(`${API}/friends/request`, {
      headers: { Authorization: `Bearer ${a.token}` },
      data: { email: b.user.email },
    });
    const body = await req.json();
    await waitPinot(async () => {
      const list = await request.get(`${API}/friends`, {
        headers: { Authorization: `Bearer ${b.token}` },
      });
      const j = await list.json();
      return (j.incoming || []).length ? true : null;
    });
    await request.post(`${API}/friends/${body.friendship_id}/accept`, {
      headers: { Authorization: `Bearer ${b.token}` },
    });
    await request.post(`${API}/friends/presence`, {
      headers: { Authorization: `Bearer ${a.token}` },
      data: { status: 'online' },
    });

    // Login as B in UI
    await page.goto('/store');
    await page.getByRole('button', { name: 'Iniciar sesión', exact: true }).click();
    const form = page.locator('form.modal-form').filter({ has: page.locator('input[name="loginEmail"]') });
    await form.locator('input[name="loginEmail"]').fill(b.user.email);
    await form.locator('input[name="loginPassword"]').fill(b.user.password);
    await form.locator('button[type="submit"]').click();
    await expect(page.locator('.user-name')).toBeVisible({ timeout: 20_000 });

    await page.goto('/my-friends');
    await expect(page.locator('body')).toContainText(a.user.displayName.slice(0, 8), { timeout: 20_000 });
    await expect(page.locator('.dot').first()).toBeVisible({ timeout: 15_000 });
  });
});
