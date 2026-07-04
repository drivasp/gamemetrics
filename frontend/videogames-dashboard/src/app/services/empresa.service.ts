import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface PbPage {
  items: Record<string, any>[];
  totalItems: number;
  totalPages: number;
  page: number;
  perPage: number;
}

const PB_SKIP = new Set(['collectionId', 'collectionName', 'expand']);

@Injectable({ providedIn: 'root' })
export class EmpresaService {
  private http = inject(HttpClient);
  private base = '/empresa';

  getRecords(collection: string, page = 1, perPage = 15): Observable<PbPage> {
    return this.http.get<PbPage>(`${this.base}/${collection}/records`, {
      params: { page: String(page), perPage: String(perPage) },
    });
  }

  createRecord(collection: string, data: Record<string, any>): Observable<any> {
    return this.http.post(`${this.base}/${collection}/records`, data);
  }

  updateRecord(collection: string, id: string, data: Record<string, any>): Observable<any> {
    return this.http.patch(`${this.base}/${collection}/records/${id}`, data);
  }

  deleteRecord(collection: string, id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/${collection}/records/${id}`);
  }

  static visibleColumns(item: Record<string, any>): string[] {
    return Object.keys(item).filter((k) => !PB_SKIP.has(k));
  }
}
