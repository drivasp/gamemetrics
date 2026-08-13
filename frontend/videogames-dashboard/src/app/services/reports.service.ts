import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';

export interface ReportColumn {
  key: string;
  label: string;
  align: 'left' | 'right';
}

export interface ReportMeta {
  code: string;
  type: 'simple' | 'compound';
  title: string;
  area: string;
  question: string;
  description: string;
  source: string;
  columns: ReportColumn[];
}

export interface ReportKpi {
  key: string;
  label: string;
  value: string | number;
  format: 'currency' | 'number' | 'text';
}

export interface ReportPayload {
  meta: ReportMeta;
  filters: Record<string, string>;
  kpis: ReportKpi[];
  rows: Record<string, unknown>[];
  partners: Array<{ partner_id: string; company_name: string }>;
  generated_at: string;
  row_count: number;
  disclaimer: string;
}

export interface ReportCatalogItem {
  code: string;
  type: 'simple' | 'compound';
  title: string;
  area: string;
  question: string;
  description: string;
  source: string;
  columns: ReportColumn[];
  filters: string[];
}

@Injectable({ providedIn: 'root' })
export class ReportsService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private base = '/reports';

  private headers(): HttpHeaders {
    const token = this.auth.getToken();
    return new HttpHeaders(token ? { Authorization: `Bearer ${token}` } : {});
  }

  getCatalog(): Observable<{ items: ReportCatalogItem[]; generated_at: string; count: number }> {
    return this.http.get<{ items: ReportCatalogItem[]; generated_at: string; count: number }>(
      `${this.base}/catalog`,
      { headers: this.headers() },
    );
  }

  getReport(
    code: string,
    opts?: { status?: string; partner_id?: string; week?: number | string },
  ): Observable<ReportPayload> {
    let params = new HttpParams();
    if (opts?.status) params = params.set('status', opts.status);
    if (opts?.partner_id) params = params.set('partner_id', opts.partner_id);
    if (opts?.week !== undefined && opts?.week !== null && opts?.week !== '') {
      params = params.set('week', String(opts.week));
    }
    return this.http.get<ReportPayload>(`${this.base}/view/${code}`, {
      headers: this.headers(),
      params,
    });
  }

  downloadCsv(
    code: string,
    opts?: { status?: string; partner_id?: string; week?: number | string },
  ): Observable<Blob> {
    let params = new HttpParams();
    if (opts?.status) params = params.set('status', opts.status);
    if (opts?.partner_id) params = params.set('partner_id', opts.partner_id);
    if (opts?.week !== undefined && opts?.week !== null && opts?.week !== '') {
      params = params.set('week', String(opts.week));
    }
    return this.http.get(`${this.base}/view/${code}/export.csv`, {
      headers: this.headers(),
      params,
      responseType: 'blob',
    });
  }
}
