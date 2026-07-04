import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface DimRecord {
  dimId: number;
  nombre: string;
  codigo?: string;
  edadMinima?: number;
}

@Injectable({ providedIn: 'root' })
export class DimensionService {
  private http = inject(HttpClient);
  private base = '/api/dim';

  getPlataformas(page = 0, size = 100): Observable<DimRecord[]> {
    return this.http.get<DimRecord[]>(`${this.base}/plataformas`, { params: { page, size } });
  }

  getGeneros(page = 0, size = 100): Observable<DimRecord[]> {
    return this.http.get<DimRecord[]>(`${this.base}/generos`, { params: { page, size } });
  }

  getDesarrolladores(page = 0, size = 100): Observable<DimRecord[]> {
    return this.http.get<DimRecord[]>(`${this.base}/desarrolladores`, { params: { page, size } });
  }

  getPublicadores(page = 0, size = 100): Observable<DimRecord[]> {
    return this.http.get<DimRecord[]>(`${this.base}/publicadores`, { params: { page, size } });
  }

  getEsrb(page = 0, size = 50): Observable<DimRecord[]> {
    return this.http.get<DimRecord[]>(`${this.base}/esrb`, { params: { page, size } });
  }
}
