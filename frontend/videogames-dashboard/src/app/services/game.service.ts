import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface VideoGame {
  id: string;
  slug: string;
  name: string;
  released: string;
  rating: number;
  metacritic: number;
  genres: string;
  platforms: string;
  developers: string;
  publishers: string;
  esrbRating: string;
}

export interface CountDTO {
  label: string;
  count: number;
}

@Injectable({ providedIn: 'root' })
export class GameService {
  private http = inject(HttpClient);
  private baseUrl = '/api';

  getGames(page: number, size: number, semana = 1): Observable<VideoGame[]> {
    return this.http.get<VideoGame[]>(`${this.baseUrl}/games?page=${page}&size=${size}&semana=${semana}`);
  }

  getTopRated(semana = 1): Observable<VideoGame[]> {
    return this.http.get<VideoGame[]>(`${this.baseUrl}/dashboard/top-rated?semana=${semana}`);
  }

  getByGenre(semana = 17): Observable<CountDTO[]> {
    return this.http.get<CountDTO[]>(`${this.baseUrl}/dashboard/by-genre?semana=${semana}`);
  }

  getByPlatform(semana = 17): Observable<CountDTO[]> {
    return this.http.get<CountDTO[]>(`${this.baseUrl}/dashboard/by-platform?semana=${semana}`);
  }

  getByEsrb(semana = 17): Observable<CountDTO[]> {
    return this.http.get<CountDTO[]>(`${this.baseUrl}/dashboard/by-esrb?semana=${semana}`);
  }

  getByYear(semana = 17): Observable<CountDTO[]> {
    return this.http.get<CountDTO[]>(`${this.baseUrl}/dashboard/by-year?semana=${semana}`);
  }

  getCount(semana = 17): Observable<{ count: number }> {
    return this.http.get<{ count: number }>(`${this.baseUrl}/games/count?semana=${semana}`);
  }
}
