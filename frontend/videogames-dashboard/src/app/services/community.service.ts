import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class CommunityService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);

  private headers(): HttpHeaders {
    return new HttpHeaders({ Authorization: `Bearer ${this.auth.getToken()}` });
  }

  // Forums
  listThreads(slug: string): Observable<any> {
    return this.http.get(`/forums/${encodeURIComponent(slug)}/threads`);
  }

  getThread(id: string): Observable<any> {
    return this.http.get(`/forums/threads/${id}`);
  }

  createThread(data: { product_id: string; game_slug: string; title: string; body: string }): Observable<any> {
    return this.http.post('/forums/threads', data, { headers: this.headers() });
  }

  addPost(threadId: string, body: string): Observable<any> {
    return this.http.post(`/forums/threads/${threadId}/posts`, { body }, { headers: this.headers() });
  }

  // Family
  getFamily(): Observable<any> {
    return this.http.get('/family', { headers: this.headers() });
  }

  createFamily(name: string): Observable<any> {
    return this.http.post('/family/create', { name }, { headers: this.headers() });
  }

  inviteFamily(email: string): Observable<any> {
    return this.http.post('/family/invite', { email }, { headers: this.headers() });
  }

  shareGame(purchase_id: string, shared_with: string): Observable<any> {
    return this.http.post('/family/share', { purchase_id, shared_with }, { headers: this.headers() });
  }

  // API keys
  listApiKeys(): Observable<any> {
    return this.http.get('/api-keys', { headers: this.headers() });
  }

  createApiKey(): Observable<any> {
    return this.http.post('/api-keys', {}, { headers: this.headers() });
  }

  revokeApiKey(id: string): Observable<any> {
    return this.http.delete(`/api-keys/${id}`, { headers: this.headers() });
  }

  // Search analytics
  logSearch(query_text: string, results_count: number): void {
    const opts = this.auth.getToken()
      ? { headers: this.headers() }
      : {};
    this.http.post('/search/log', { query_text, results_count }, opts).subscribe({ error: () => {} });
  }
}
