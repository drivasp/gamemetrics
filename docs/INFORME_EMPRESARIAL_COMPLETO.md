# -*- coding: utf-8 -*-
"""Informe empresarial completo GameMetrics (cierre checklist).

Usar junto a:
- docs/BUSINESS_MODEL_PLATFORM.md
- docs/COMPETITIVE_BENCHMARK.md
- docs/SYSTEM_FLOWS.md
- docs/OPEN_DEPENDENCIES.md
- finance/model_output.json (generado)

## 1. Qué es el negocio
Marketplace B2B2C de distribución digital de videojuegos: conecta developers/publishers con jugadores; monetiza take rate + publication fee + featured SaaS.

## 2. Participantes
Valve/Steam (benchmark), GameMetrics (plataforma), developers, publishers (segmento B2B, misma cuenta partner hoy), jugadores, PSP (Stripe adapter), bancos, autoridades fiscales, cloud/CDN, marketplace P2P users.

## 3–6. Steam research
Ver BUSINESS_MODEL_PLATFORM + fuentes oficiales Direct Fee, Payments, Pricing, Refunds. Tiers 30/25/20 = industria. Epic 100%/$1M = oficial.

## 7. Modelo recomendado
Take 30% flat; Direct fee $100/recoup $1k; featured SaaS; wallet; market sandbox; no Game Pass MVP.

## 8–12. Ingresos / costos / comisión / pagos / refunds
Comisión ventas, publication fee, featured. Costos: infra, personal, PSP, soporte (ver finance/). Pagos mensuales hold+min. Refunds 14d wallet. Chargebacks admin API.

## 13–17. Tax / market / wallet / payouts / arquitectura
Tax Engine JSON configurable. Marketplace mint/list/buy/fee/ownership. Wallet con tx idempotentes. Payouts paid|failed sandbox. Sistemas en main.py routers.

## 18–19. Datos
Pinot: ledger, payouts, wallets, taxes, market_*, fact_audit_log (migración 25_*).

## 20–26. Cambios esta entrega
Marketplace, tax, fraud, rate limit, finance model, frontend market+statement+audit, tests integration+smoke, docs benchmark+flows, migraciones schemas.

## 27. Pendientes REALES (solo externos)
Stripe live keys, legal ToS, tax counsel, KYC/AML market, CAC live attribution, consolas contract terms.

## 28. Riesgos
Fraude, liquidez, competencia Steam/Epic, eventual consistency Kafka/Pinot, refund abuse.

## 29. Unit economics
Definiciones + cómputo desde supuestos en finance/run_model.py → model_output.json.

## 30. Siguiente
PSP live + playtime refunds + DLC catalog + Redis rate limit prod.
"""
