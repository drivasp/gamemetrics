import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { timeout, catchError, of } from 'rxjs';
import { CommunityService } from '../../services/community.service';
import { LibraryService } from '../../services/library.service';

@Component({
  selector: 'app-family',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './family.component.html',
  styleUrl: './family.component.scss',
})
export class FamilyComponent implements OnInit {
  private community = inject(CommunityService);
  private library = inject(LibraryService);
  private cdr = inject(ChangeDetectorRef);

  group: any = null;
  members: any[] = [];
  shares: any[] = [];
  purchases: any[] = [];
  loading = true;
  groupName = '';
  inviteEmail = '';
  sharePurchaseId = '';
  shareWith = '';
  message = '';
  error = '';

  ngOnInit(): void {
    this.reload();
    this.library.getLibrary().subscribe({
      next: items => {
        this.purchases = items.filter(i => !i.refunded);
        this.cdr.detectChanges();
      },
    });
  }

  reload(): void {
    this.loading = true;
    this.community.getFamily().pipe(
      timeout(10000),
      catchError(() => of({ group: null, members: [], shares: [] })),
    ).subscribe({
      next: res => {
        this.group = res.group;
        this.members = res.members || [];
        this.shares = res.shares || [];
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  create(): void {
    if (!this.groupName.trim()) return;
    this.community.createFamily(this.groupName.trim()).subscribe({
      next: res => { this.message = res.message; this.reload(); },
      error: err => { this.error = err?.error?.detail || 'Error'; this.cdr.detectChanges(); },
    });
  }

  invite(): void {
    if (!this.inviteEmail.trim()) return;
    this.community.inviteFamily(this.inviteEmail.trim()).subscribe({
      next: res => { this.message = res.message; this.inviteEmail = ''; this.reload(); },
      error: err => { this.error = err?.error?.detail || 'Error'; this.cdr.detectChanges(); },
    });
  }

  share(): void {
    if (!this.sharePurchaseId || !this.shareWith) return;
    this.community.shareGame(this.sharePurchaseId, this.shareWith).subscribe({
      next: res => { this.message = res.message; this.reload(); },
      error: err => { this.error = err?.error?.detail || 'Error'; this.cdr.detectChanges(); },
    });
  }

  shareTargets(): any[] {
    // Compartir con cualquier miembro del grupo excepto uno mismo no aplica aquí:
    // el dueño comparte con miembros; un miembro puede compartir con el dueño u otros.
    return this.members;
  }
}
