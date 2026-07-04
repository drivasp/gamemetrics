import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';

export interface Review {
  review_id: string;
  user_id: string;
  product_id: string;
  game_slug: string;
  rating: number;
  comment: string;
  created_at: string;
  updated_at?: string | null;
  helpful_count?: number;
  not_helpful_count?: number;
  my_vote?: boolean | null;
}

export interface ReviewPage {
  reviews: Review[];
  avg_rating: number;
  total: number;
}

@Injectable({ providedIn: 'root' })
export class ReviewsService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private base = '/reviews';

  getReviews(slug: string): Observable<ReviewPage> {
    const token = this.auth.getToken();
    const opts = token
      ? { headers: new HttpHeaders({ Authorization: `Bearer ${token}` }) }
      : {};
    return this.http.get<ReviewPage>(`${this.base}/${slug}`, opts);
  }

  createReview(slug: string, data: { product_id: string; rating: number; comment: string }): Observable<Review> {
    return this.http.post<Review>(`${this.base}/${slug}`, data, {
      headers: new HttpHeaders({ Authorization: `Bearer ${this.auth.getToken()}` }),
    });
  }

  updateReview(slug: string, data: { rating?: number; comment?: string }): Observable<Review> {
    return this.http.put<Review>(`${this.base}/${slug}`, data, {
      headers: new HttpHeaders({ Authorization: `Bearer ${this.auth.getToken()}` }),
    });
  }

  deleteReview(slug: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/${slug}`, {
      headers: new HttpHeaders({ Authorization: `Bearer ${this.auth.getToken()}` }),
    });
  }

  vote(reviewId: string, helpful: boolean): Observable<{
    review_id: string;
    helpful_count: number;
    not_helpful_count: number;
    my_vote: boolean;
  }> {
    return this.http.post<{
      review_id: string;
      helpful_count: number;
      not_helpful_count: number;
      my_vote: boolean;
    }>(`${this.base}/votes/${reviewId}`, { helpful }, {
      headers: new HttpHeaders({ Authorization: `Bearer ${this.auth.getToken()}` }),
    });
  }
}
