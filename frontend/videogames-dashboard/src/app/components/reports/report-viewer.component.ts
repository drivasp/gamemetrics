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
  week = 1;
  dateFrom = '';
  dateTo = '';
  csvBusy = false;

  readonly partnerFilterCodes = new Set(['GM-C02', 'GM-S12', 'GM-S13']);
  readonly weekFilterCodes = new Set(['GM-C04', 'GM-C05', 'GM-C06', 'GM-C07']);
  readonly dateRangeFilterCodes = new Set(['GM-C08']);
  readonly weeks = Array.from({ length: 17 }, (_, i) => i + 1);

  ngOnInit(): void {
    this.route.paramMap.subscribe((pm) => {
      this.code = (pm.get('code') || '').toUpperCase();
      this.statusFilter = this.code === 'GM-S03' ? 'open' : this.code === 'GM-S01' ? 'pending' : '';
      this.partnerId = '';
      this.week = 1;
      this.dateFrom = '';
      this.dateTo = '';
      this.reload();
    });
  }

  private buildOpts(): { status?: string; partner_id?: string; week?: number; date_from?: string; date_to?: string } {
    const opts: { status?: string; partner_id?: string; week?: number; date_from?: string; date_to?: string } = {};
    if (this.code === 'GM-S01') opts.status = this.statusFilter || 'pending';
    if (this.code === 'GM-S03') opts.status = this.statusFilter || 'open';
    if (this.partnerFilterCodes.has(this.code) && this.partnerId) {
      opts.partner_id = this.partnerId;
    }
    if (this.weekFilterCodes.has(this.code)) opts.week = this.week || 1;
    if (this.dateRangeFilterCodes.has(this.code)) {
      if (this.dateFrom) opts.date_from = this.dateFrom;
      if (this.dateTo) opts.date_to = this.dateTo;
    }
    return opts;
  }

  reload(): void {
    if (!this.code) return;
    this.loading = true;
    this.error = '';
    this.payload = null;
    this.cdr.detectChanges();

    this.reports.getReport(this.code, this.buildOpts()).pipe(
      timeout(45000),
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
      if (res.filters?.['week'] !== undefined) {
        this.week = Number(res.filters['week']) || 1;
      }
      if (res.filters?.['date_from'] !== undefined) {
        this.dateFrom = String(res.filters['date_from'] || '');
      }
      if (res.filters?.['date_to'] !== undefined) {
        this.dateTo = String(res.filters['date_to'] || '');
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

    this.reports.downloadCsv(this.code, this.buildOpts()).subscribe({
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
