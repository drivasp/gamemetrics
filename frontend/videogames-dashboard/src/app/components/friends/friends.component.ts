import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { timeout, catchError, of } from 'rxjs';
import { SocialService } from '../../services/social.service';

@Component({
  selector: 'app-friends',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './friends.component.html',
  styleUrl: './friends.component.scss',
})
export class FriendsComponent implements OnInit {
  private social = inject(SocialService);
  private cdr = inject(ChangeDetectorRef);

  tab: 'friends' | 'requests' | 'activity' = 'friends';
  friends: any[] = [];
  incoming: any[] = [];
  outgoing: any[] = [];
  activity: any[] = [];
  email = '';
  loading = true;
  message = '';
  error = '';

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.loading = true;
    this.social.getFriends().pipe(
      timeout(10000),
      catchError(() => of({ friends: [], incoming: [], outgoing: [] })),
    ).subscribe({
      next: res => {
        this.friends = res.friends || [];
        this.incoming = res.incoming || [];
        this.outgoing = res.outgoing || [];
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
    this.social.activity().pipe(
      timeout(10000),
      catchError(() => of({ items: [] })),
    ).subscribe({
      next: res => {
        this.activity = res.items || [];
        this.cdr.detectChanges();
      },
    });
  }

  sendRequest(): void {
    if (!this.email.trim()) return;
    this.error = '';
    this.message = '';
    this.social.requestFriend(this.email.trim()).subscribe({
      next: res => {
        this.message = res.message || 'Solicitud enviada';
        this.email = '';
        this.reload();
      },
      error: err => {
        this.error = err?.error?.detail || 'No se pudo enviar';
        this.cdr.detectChanges();
      },
    });
  }

  accept(id: string): void {
    this.social.acceptFriend(id).subscribe({
      next: () => this.reload(),
      error: err => { this.error = err?.error?.detail || 'Error'; this.cdr.detectChanges(); },
    });
  }

  decline(id: string): void {
    this.social.declineFriend(id).subscribe({
      next: () => this.reload(),
      error: err => { this.error = err?.error?.detail || 'Error'; this.cdr.detectChanges(); },
    });
  }
}
