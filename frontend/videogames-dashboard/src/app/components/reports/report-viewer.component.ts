import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule, CurrencyPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { timeout, catchError, of } from 'rxjs';
import { ReportsService, ReportPayload } from '../../services/reports.service';

@Component({
  selector: 'app-report-viewer',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, MatIconModule, CurrencyPipe],
  templateUrl: './report-viewer.component.html',
  styleUrl: './report-viewer.component.scss',
})
export class ReportViewerComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private reports = inject(ReportsService);
  private cdr = inject(ChangeDetectorRef);

  code = '';
  payload: ReportPayload | null = null;
  loading = true;
  error = '';
  statusFilter = '';
  partnerId = '';
  csvBusy = false;

  ngOnInit(): void {
    this.route.paramMap.subscribe((pm) => {
      this.code = (pm.get('code') || '').toUpperCase();
      this.statusFilter = this.code === 'GM-S03' ? 'open' : this.code === 'GM-S01' ? 'pending' : '';
      this.partnerId = '';
      this.reload();
    });
  }

  reload(): void {
    if (!this.code) return;
    this.loading = true;
    this.error = '';
    this.payload = null;
    this.cdr.detectChanges();

    const opts: { status?: string; partner_id?: string } = {};
    if (this.code === 'GM-S01') opts.status = this.statusFilter || 'pending';
    if (this.code === 'GM-S03') opts.status = this.statusFilter || 'open';
    if (this.code === 'GM-C02' && this.partnerId) opts.partner_id = this.partnerId;

    this.reports.getReport(this.code, opts).pipe(
      timeout(20000),
      catchError((err) => {
        this.error = err?.error?.detail || 'No se pudo generar el informe.';
        this.loading = false;
        this.cdr.detectChanges();
        return of(null);
      }),
    ).subscribe((res) => {
      if (!res) return;
      this.payload = res;
      if (res.filters?.['status']) this.statusFilter = String(res.filters['status']);
      if (res.filters?.['partner_id'] !== undefined) {
        this.partnerId = String(res.filters['partner_id'] || '');
      }
      this.loading = false;
      this.cdr.detectChanges();
    });
  }

  exportPdf(): void {
    window.print();
  }

  exportCsv(): void {
    if (!this.code || this.csvBusy) return;
    this.csvBusy = true;
    const opts: { status?: string; partner_id?: string } = {};
    if (this.code === 'GM-S01') opts.status = this.statusFilter || 'pending';
    if (this.code === 'GM-S03') opts.status = this.statusFilter || 'open';
    if (this.code === 'GM-C02' && this.partnerId) opts.partner_id = this.partnerId;

    this.reports.downloadCsv(this.code, opts).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${this.code}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        this.csvBusy = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.csvBusy = false;
        this.error = 'No se pudo exportar el CSV.';
        this.cdr.detectChanges();
      },
    });
  }

  cellValue(row: Record<string, unknown>, key: string): string | number {
    const v = row[key];
    if (typeof v === 'number' || typeof v === 'string') return v;
    if (v == null) return '';
    return String(v);
  }

  cellKind(key: string, row: Record<string, unknown>): 'money' | 'pill' | 'text' {
    if (this.isMoneyKey(key) || (key === 'value' && row['unit'] === 'USD')) return 'money';
    if (key === 'status' || key === 'submission_status' || key === 'priority') return 'pill';
    return 'text';
  }

  isMoneyKey(key: string): boolean {
    return /amount|revenue|fee|net|gross/i.test(key);
  }

  formatKpi(value: string | number, format: string): string {
    if (format === 'text') return String(value ?? '—');
    if (format === 'currency') {
      const n = Number(value);
      return Number.isFinite(n)
        ? n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
        : '—';
    }
    const n = Number(value);
    return Number.isFinite(n) ? n.toLocaleString('en-US') : String(value ?? '—');
  }
}
