import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { timeout, catchError, of } from 'rxjs';
import { ReportsService, ReportCatalogItem } from '../../services/reports.service';

@Component({
  selector: 'app-reports-catalog',
  standalone: true,
  imports: [CommonModule, RouterLink, MatIconModule],
  templateUrl: './reports-catalog.component.html',
  styleUrl: './reports-catalog.component.scss',
})
export class ReportsCatalogComponent implements OnInit {
  private reports = inject(ReportsService);
  private cdr = inject(ChangeDetectorRef);

  items: ReportCatalogItem[] = [];
  loading = true;
  error = '';
  generatedAt = '';

  ngOnInit(): void {
    this.reports.getCatalog().pipe(
      timeout(15000),
      catchError((err) => {
        this.error = err?.error?.detail || 'No se pudo cargar el catálogo de reportes.';
        this.loading = false;
        this.cdr.detectChanges();
        return of(null);
      }),
    ).subscribe((res) => {
      if (!res) return;
      this.items = res.items || [];
      this.generatedAt = res.generated_at || '';
      this.loading = false;
      this.cdr.detectChanges();
    });
  }

  get simples(): ReportCatalogItem[] {
    return this.items.filter((i) => i.type === 'simple');
  }

  get compounds(): ReportCatalogItem[] {
    return this.items.filter((i) => i.type === 'compound');
  }
}
