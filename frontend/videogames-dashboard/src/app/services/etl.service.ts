import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface EtlJobStatus {
  status: 'idle' | 'running' | 'ok' | 'error';
  mensaje: string;
}

export interface EtlStatus {
  dataset:     EtlJobStatus;
  empresa:     EtlJobStatus;
  dimensiones: EtlJobStatus;
  realtime:    EtlJobStatus;
  catalogo:    EtlJobStatus;
  promociones: EtlJobStatus;
}

export interface DatasetResponse {
  mensaje:    string;
  ya_existe?: boolean;
  semana?:    number;
}

@Injectable({ providedIn: 'root' })
export class EtlService {
  private http = inject(HttpClient);
  private base = '/etl';

  getStatus(): Observable<EtlStatus> {
    return this.http.get<EtlStatus>(`${this.base}/status`);
  }

  getSemanasStatus(): Observable<{ semanas: number[] }> {
    return this.http.get<{ semanas: number[] }>(`${this.base}/semanas-status`);
  }

  reloadDataset(semana: number, force = false): Observable<DatasetResponse> {
    return this.http.post<DatasetResponse>(
      `${this.base}/reload-dataset`,
      { semana, force }
    );
  }

  reloadEmpresa(): Observable<{ mensaje: string }> {
    return this.http.post<{ mensaje: string }>(`${this.base}/reload-empresa`, {});
  }

  reloadDimensions(): Observable<{ mensaje: string }> {
    return this.http.post<{ mensaje: string }>(`${this.base}/reload-dimensions`, {});
  }

  createRealtimeTables(): Observable<{ mensaje: string }> {
    return this.http.post<{ mensaje: string }>(`${this.base}/create-realtime-tables`, {});
  }

  reloadCatalogo(semana: number): Observable<{ mensaje: string }> {
    return this.http.post<{ mensaje: string }>(`${this.base}/reload-catalogo`, { semana });
  }

  seedPromociones(): Observable<{ mensaje: string }> {
    return this.http.post<{ mensaje: string }>(`${this.base}/seed-promociones`, {});
  }
}
