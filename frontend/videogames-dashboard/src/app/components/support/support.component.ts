import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { timeout, catchError, of } from 'rxjs';
import { SocialService } from '../../services/social.service';

@Component({
  selector: 'app-support',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './support.component.html',
  styleUrl: './support.component.scss',
})
export class SupportComponent implements OnInit {
  private social = inject(SocialService);
  private cdr = inject(ChangeDetectorRef);

  tickets: any[] = [];
  loading = true;
  subject = '';
  body = '';
  priority = 'normal';
  message = '';
  error = '';
  sending = false;

  ngOnInit(): void { this.reload(); }

  reload(): void {
    this.loading = true;
    this.social.getTickets().pipe(
      timeout(10000),
      catchError(() => of({ items: [] })),
    ).subscribe({
      next: res => {
        this.tickets = res.items || [];
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  create(): void {
    if (!this.subject.trim() || !this.body.trim()) return;
    this.sending = true;
    this.error = '';
    this.social.createTicket(this.subject.trim(), this.body.trim(), this.priority).subscribe({
      next: res => {
        this.message = res.message || 'Ticket creado';
        this.subject = '';
        this.body = '';
        this.sending = false;
        this.reload();
      },
      error: err => {
        this.sending = false;
        this.error = err?.error?.detail || 'No se pudo crear el ticket';
        this.cdr.detectChanges();
      },
    });
  }

  close(id: string): void {
    this.social.closeTicket(id).subscribe({ next: () => this.reload() });
  }
}
