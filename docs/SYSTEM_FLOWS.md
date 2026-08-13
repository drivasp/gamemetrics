# Flujos del sistema (Mermaid)

Diagramas alineados al código actual de GameMetrics.

## Registro desarrollador / partner

```mermaid
sequenceDiagram
  participant U as Usuario
  participant API as /partners
  participant Pinot as Kafka/Pinot
  U->>API: POST register company
  API->>Pinot: fact_partner_accounts
  API-->>U: partner activo + rol
```

## Publicación / claim

```mermaid
sequenceDiagram
  participant P as Partner
  participant API as /partners /admin
  participant L as Ledger
  P->>API: claim product_id
  API-->>P: pending
  Note over API: Admin aprueba
  API->>L: direct_fee (si PUBLICATION_FEE_USD>0)
  API-->>P: approved + fee asiento
```

## Compra + revenue share

```mermaid
flowchart TD
  A[Checkout] --> B[Tax Engine quote]
  B --> C[Payment sandbox/Stripe/wallet]
  C --> D[fulfill order]
  D --> E[fact_purchases]
  D --> F[sale ledger split]
  F --> G[platform_fee]
  F --> H[publisher_net]
  F --> I[maybe Direct fee recoup]
```

## Pago

```mermaid
flowchart LR
  Cart --> IdempotencyKey
  IdempotencyKey --> Provider{wallet|stripe|sandbox}
  Provider --> PaymentRecord
  PaymentRecord --> Fulfill
```

## Refund

```mermaid
sequenceDiagram
  participant U as Jugador
  participant R as /refunds
  participant L as Ledger
  participant W as Wallet
  U->>R: POST purchase_id
  R->>R: ventana 14d + no duplicado
  R->>L: refund entry
  R->>W: credit refund
  R-->>U: approved
```

## Chargeback

```mermaid
flowchart TD
  Dispute[Admin o webhook PSP futuro] --> CB[record_chargeback_ledger]
  CB --> AGR[Reduce AGR + publisher_net]
  CB --> Audit[financial_audit]
```

## Payout

```mermaid
sequenceDiagram
  participant A as Admin
  participant P as create_payout
  participant F as FraudService
  participant L as Ledger
  A->>P: amount + idempotency
  P->>F: evaluate
  alt sandbox_fail
    P-->>A: status=failed sin debitar
  else ok
    P->>L: payout entry negativo
    P-->>A: status=paid
  end
```

## Wallet

```mermaid
flowchart TD
  TopUp[topup] --> Tx[fact_wallet_transactions + idem key]
  Purchase[purchase debit] --> Tx
  Refund[refund credit] --> Tx
  Tx --> Bal[fact_user_wallets]
```

## Marketplace

```mermaid
sequenceDiagram
  participant S as Seller
  participant M as /marketplace
  participant B as Buyer
  participant W as Wallet
  S->>M: mint item
  S->>M: create listing
  B->>M: buy + Idempotency-Key
  M->>W: debit buyer / credit seller_net
  M->>M: ownership transfer + fees
```

## Impuestos

```mermaid
flowchart LR
  Country --> TaxRulesJSON
  TaxRulesJSON --> Calculate
  Calculate --> Quote
  Quote --> OrderTaxes
  Calculate --> TaxAudit
```

## Promoción / Featured

```mermaid
flowchart TD
  Partner --> SaaSPlan
  SaaSPlan --> FeaturedPlacement
  FeaturedPlacement --> StoreHome
```

## Fraud detection

```mermaid
flowchart TD
  Action --> Rules[RuleBasedFraudDetector]
  Rules --> Score
  Score -->|>=70| Block
  Score -->|40-69| Review
  Score -->|<40| Allow
  Score --> AuditLog
```

## Auditoría financiera

```mermaid
flowchart TD
  FinancialOp --> audit_event
  audit_event --> MemoryLog
  audit_event --> fact_audit_log
```

## Compra in-game (diseño / futuro DLC)

```mermaid
flowchart TD
  GameClient --> IAP_SKU
  IAP_SKU --> CheckoutSamePipeline
  CheckoutSamePipeline --> LedgerSameSplit
```
