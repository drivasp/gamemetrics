"""
Seed demo voluminoso para los 6 reportes del Centro de Reportes.
Envía JSON a Kafka → Pinot REALTIME (mismo patrón que promociones).

Uso:
  docker compose exec etl-api python 24_seed_reports_demo.py
"""
from __future__ import annotations

import json
import os
import random
import time
import uuid

from kafka import KafkaProducer

KAFKA_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
DAY_MS = 24 * 60 * 60 * 1000
SHARE = 70.0
TAKE = 30.0

# Partners ya registrados en la demo + estudios extra realistas
PARTNERS = [
    {
        "partner_id": "0221c3ed17be472",
        "company_name": "Mi Studio Demo",
        "contact_email": "studio@demo.com",
        "revenue_share_pct": 70.0,
    },
    {
        "partner_id": "b112e209e172485",
        "company_name": "Demo 2",
        "contact_email": "Yahir222@gmail.com",
        "revenue_share_pct": 70.0,
    },
    {
        "partner_id": "nebula9f2a1c3e7",
        "company_name": "Nebula Forge Studios",
        "contact_email": "finance@nebulafarge.games",
        "revenue_share_pct": 70.0,
    },
    {
        "partner_id": "pixelwave7b4d2",
        "company_name": "Pixelwave Interactive",
        "contact_email": "partners@pixelwave.io",
        "revenue_share_pct": 75.0,
    },
    {
        "partner_id": "aurora8c1e5f90a",
        "company_name": "Aurora Softworks",
        "contact_email": "billing@aurorasoft.gg",
        "revenue_share_pct": 70.0,
    },
]

GAMES_BY_PARTNER = {
    "0221c3ed17be472": [
        ("rwzxw2ux6b9au2k", "DEVICE 6", "approved"),
        ("bioshock-collection", "BioShock: The Collection", "approved"),
        ("hades-like-demo", "Tartarus Protocol", "pending"),
        ("neon-drift-racer", "Neon Drift", "pending"),
        ("shadow-quill-rpg", "Shadow Quill", "rejected"),
    ],
    "b112e209e172485": [
        ("shinobi-iii", "Shinobi III", "approved"),
        ("twewy-classic", "The World Ends with You", "approved"),
        ("orbit-garden", "Orbit Garden", "pending"),
        ("cargo-hauler-sim", "Cargo Hauler Sim", "pending"),
        ("void-chef", "Void Chef", "approved"),
    ],
    "nebula9f2a1c3e7": [
        ("starfall-odyssey", "Starfall Odyssey", "approved"),
        ("deep-station-9", "Deep Station Nine", "approved"),
        ("comet-runners", "Comet Runners", "pending"),
        ("orbital-siege", "Orbital Siege", "approved"),
        ("quiet-moons", "Quiet Moons", "pending"),
    ],
    "pixelwave7b4d2": [
        ("byte-brawler", "Byte Brawler", "approved"),
        ("chroma-dash", "Chroma Dash", "approved"),
        ("loot-loop", "Loot Loop", "pending"),
        ("gridlock-arena", "Gridlock Arena", "approved"),
        ("tape-deck-hero", "Tape Deck Hero", "rejected"),
    ],
    "aurora8c1e5f90a": [
        ("frostline-tactics", "Frostline Tactics", "approved"),
        ("ember-valley", "Ember Valley", "approved"),
        ("glass-harbor", "Glass Harbor", "pending"),
        ("midnight-atelier", "Midnight Atelier", "approved"),
        ("relay-runners", "Relay Runners", "pending"),
    ],
}

# Precios unitarios realistas (USD) por juego aprobado
UNIT_PRICES = {
    "DEVICE 6": 14.99,
    "BioShock: The Collection": 39.99,
    "Shinobi III": 9.99,
    "The World Ends with You": 19.99,
    "Void Chef": 24.99,
    "Starfall Odyssey": 49.99,
    "Deep Station Nine": 29.99,
    "Orbital Siege": 34.99,
    "Byte Brawler": 19.99,
    "Chroma Dash": 12.99,
    "Gridlock Arena": 27.99,
    "Frostline Tactics": 44.99,
    "Ember Valley": 22.99,
    "Midnight Atelier": 16.99,
}

TICKET_SUBJECTS = [
    ("No puedo activar mi clave de BioShock", "high"),
    ("Reembolso dentro de las 2 horas — compra duplicada", "high"),
    ("Error al descargar actualización de Starfall Odyssey", "normal"),
    ("Solicitud de factura fiscal para empresa", "normal"),
    ("Amigo no recibe regalo enviado", "high"),
    ("Cambio de región bloquea el carrito", "normal"),
    ("Cupón WEEKEND25 no aplica en checkout", "normal"),
    ("Cuenta bloqueada tras varios intentos de login", "high"),
    ("Consulta sobre revenue share 70/30", "low"),
    ("No aparece juego en biblioteca tras pago Stripe", "high"),
    ("Solicitud de cierre de cuenta GDPR", "normal"),
    ("Problema con autenticación en dos pasos", "low"),
    ("Review de claim de propiedad rechazado — apelación", "normal"),
    ("Payout pendiente más de 14 días", "high"),
    ("Bug visual en catálogo móvil (portadas)", "low"),
    ("No recibí correo de confirmación de orden", "normal"),
    ("Solicitud de acceso partner portal", "normal"),
    ("Cobro duplicado en tarjeta Visa ****4412", "high"),
]


def money(x: float) -> float:
    return round(float(x) + 1e-9, 2)


def split(gross: float, share_pct: float = SHARE) -> tuple[float, float, float, float]:
    g = money(gross)
    fee = money(g * (100.0 - share_pct) / 100.0)
    net = money(g - fee)
    take = money(100.0 - share_pct)
    return g, fee, net, take


def ms_ago(days: float) -> int:
    return int(time.time() * 1000) - int(days * DAY_MS)


def rid(n: int = 15) -> str:
    return uuid.uuid4().hex[:n]


def main() -> None:
    print("=" * 60)
    print("  Seed reportes demo (claims, ledger, payouts, tickets)")
    print("=" * 60)

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_SERVERS,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8"),
        acks="all",
        retries=3,
    )

    # --- Partners ---
    for p in PARTNERS:
        row = {
            **p,
            "status": "active",
            "created_at": ms_ago(random.uniform(40, 120)),
            "deleted": False,
        }
        producer.send("fact_partner_accounts", key=p["partner_id"], value=row)
        print(f"  partner: {p['company_name']}")

    # --- Claims / juegos ---
    approved_games: list[tuple[str, str, str, float]] = []  # partner, product, name, share
    for partner in PARTNERS:
        pid = partner["partner_id"]
        share = float(partner["revenue_share_pct"])
        for product_id, game_name, status in GAMES_BY_PARTNER[pid]:
            pgid = f"pg_{rid(12)}"
            row = {
                "partner_game_id": pgid,
                "partner_id": pid,
                "product_id": product_id,
                "game_name": game_name,
                "submission_status": status,
                "created_at": ms_ago(random.uniform(2, 45)),
                "deleted": False,
            }
            producer.send("fact_partner_games", key=pgid, value=row)
            if status == "approved":
                approved_games.append((pid, product_id, game_name, share))
        print(f"  games: {partner['company_name']} ({len(GAMES_BY_PARTNER[pid])})")

    # --- Ledger: ventas + algunos reembolsos ---
    sale_count = 0
    refund_count = 0
    net_by_partner: dict[str, float] = {p["partner_id"]: 0.0 for p in PARTNERS}

    # ~8–14 ventas por juego aprobado (mezcla viejas / recientes)
    for partner_id, product_id, game_name, share in approved_games:
        unit = UNIT_PRICES.get(game_name, 19.99)
        n_sales = random.randint(8, 14)
        for i in range(n_sales):
            # 70% fuera de hold (>14 días), 30% recientes
            days = random.uniform(16, 55) if random.random() < 0.7 else random.uniform(0.5, 10)
            qty = 1 if random.random() < 0.85 else random.randint(2, 3)
            order_id = f"ord_{rid(10)}"
            entry_id = f"sale_{order_id}_{product_id}"
            g, fee, net, take = split(unit * qty, share)
            created = ms_ago(days)
            sale = {
                "ledger_entry_id": entry_id,
                "partner_id": partner_id,
                "order_id": order_id,
                "product_id": product_id,
                "game_name": game_name,
                "buyer_user_id": f"user_{rid(8)}",
                "entry_type": "sale",
                "currency": "USD",
                "status": "available",
                "related_entry_id": "",
                "quantity": qty,
                "gross_amount": g,
                "platform_fee_amount": fee,
                "publisher_net_amount": net,
                "publisher_share_pct": share,
                "platform_take_rate_pct": take,
                "created_at": created,
                "deleted": False,
            }
            producer.send("fact_partner_ledger", key=entry_id, value=sale)
            sale_count += 1
            net_by_partner[partner_id] = money(net_by_partner[partner_id] + net)

            # ~8% reembolsos
            if random.random() < 0.08:
                purchase_id = rid(12)
                refund_id = f"refund_{purchase_id}"
                refund = {
                    "ledger_entry_id": refund_id,
                    "partner_id": partner_id,
                    "order_id": order_id,
                    "product_id": product_id,
                    "game_name": game_name,
                    "buyer_user_id": sale["buyer_user_id"],
                    "entry_type": "refund",
                    "currency": "USD",
                    "status": "available",
                    "related_entry_id": entry_id,
                    "quantity": -qty,
                    "gross_amount": -g,
                    "platform_fee_amount": -fee,
                    "publisher_net_amount": -net,
                    "publisher_share_pct": share,
                    "platform_take_rate_pct": take,
                    "created_at": created + random.randint(1, 6) * 3600_000,
                    "deleted": False,
                }
                producer.send("fact_partner_ledger", key=refund_id, value=refund)
                refund_count += 1
                net_by_partner[partner_id] = money(net_by_partner[partner_id] - net)

    print(f"  ledger sales: {sale_count}  refunds: {refund_count}")

    # --- Payouts (parte del neto ya liquidado) ---
    payout_n = 0
    for partner in PARTNERS:
        pid = partner["partner_id"]
        available_like = max(0.0, net_by_partner[pid] * 0.55)  # liquidamos ~55%
        chunks = []
        remaining = available_like
        while remaining >= 80 and len(chunks) < 4:
            amt = money(min(remaining, random.uniform(120, min(900, remaining))))
            if amt < 80:
                break
            chunks.append(amt)
            remaining = money(remaining - amt)
        for amt in chunks:
            payout_id = rid(15)
            paid_at = ms_ago(random.uniform(3, 28))
            method = random.choice(["manual", "manual", "stripe_connect"])
            row = {
                "payout_id": payout_id,
                "partner_id": pid,
                "currency": "USD",
                "method": method,
                "status": "paid",
                "reference": f"PAY-{payout_id.upper()}" if method == "manual" else f"tr_{rid(14)}",
                "created_by": "admin@gamemetrics.demo",
                "stripe_transfer_id": f"tr_{rid(14)}" if method == "stripe_connect" else "",
                "notes": random.choice([
                    "Liquidación quincenal",
                    "Payout solicitado por partner portal",
                    "Cierre de ciclo mensual",
                    "Ajuste + liquidación ordinaria",
                ]),
                "amount": amt,
                "created_at": paid_at,
                "paid_at": paid_at,
                "deleted": False,
            }
            producer.send("fact_partner_payouts", key=payout_id, value=row)
            ledger_id = f"payout_{payout_id}"
            producer.send(
                "fact_partner_ledger",
                key=ledger_id,
                value={
                    "ledger_entry_id": ledger_id,
                    "partner_id": pid,
                    "order_id": "",
                    "product_id": "",
                    "game_name": "Payout",
                    "buyer_user_id": "admin@gamemetrics.demo",
                    "entry_type": "payout",
                    "currency": "USD",
                    "status": "paid",
                    "related_entry_id": payout_id,
                    "quantity": 0,
                    "gross_amount": 0.0,
                    "platform_fee_amount": 0.0,
                    "publisher_net_amount": -amt,
                    "publisher_share_pct": 0.0,
                    "platform_take_rate_pct": 0.0,
                    "created_at": paid_at,
                    "deleted": False,
                },
            )
            payout_n += 1
        print(f"  payouts: {partner['company_name']} x{len(chunks)}")

    # --- Support tickets ---
    for i, (subject, priority) in enumerate(TICKET_SUBJECTS):
        tid = f"tkt_{rid(12)}"
        status = "open" if i < 14 else "closed"
        row = {
            "ticket_id": tid,
            "user_id": f"player_{rid(8)}",
            "subject": subject,
            "body": (
                f"Hola equipo de soporte GameMetrics,\n\n"
                f"Detalle: {subject}.\n"
                f"Orden aproximada: ORD-{rid(6).upper()}.\n"
                f"Gracias."
            ),
            "status": status,
            "priority": priority,
            "created_at": ms_ago(random.uniform(0.2, 20)),
            "deleted": False,
        }
        producer.send("fact_support_tickets", key=tid, value=row)
    print(f"  tickets: {len(TICKET_SUBJECTS)} (14 open + closed)")

    producer.flush()
    producer.close()
    print("  Listo. Espera ~5–15s y recarga /reports.")
    print("=" * 60)


if __name__ == "__main__":
    random.seed(20260803)
    main()
