import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { DimensionService, DimRecord } from '../../services/dimension.service';

interface DimDef {
  key: string;
  label: string;
  icon: string;
  desc: string;
  hasEsrb?: boolean;
}

@Component({
  selector: 'app-dimensiones',
  standalone: true,
  imports: [CommonModule, FormsModule, MatIconModule],
  templateUrl: './dimensiones.component.html',
  styleUrl: './dimensiones.component.scss',
})
export class DimensionesComponent implements OnInit {
  private svc = inject(DimensionService);
  private cdr = inject(ChangeDetectorRef);

  readonly dims: DimDef[] = [
    { key: 'plataformas',     label: 'Plataformas',      icon: 'devices',  desc: 'Plataformas únicas extraídas del dataset de videojuegos.' },
    { key: 'generos',         label: 'Géneros',           icon: 'category',  desc: 'Géneros únicos de videojuegos.' },
    { key: 'desarrolladores', label: 'Desarrolladores',   icon: 'code',  desc: 'Estudios desarrolladores únicos del dataset.' },
    { key: 'publicadores',    label: 'Publicadores',      icon: 'inventory_2',  desc: 'Empresas publicadoras únicas del dataset.' },
    { key: 'esrb',            label: 'Clasificaciones ESRB', icon: 'eighteen_up_rating', desc: 'Clasificaciones de contenido ESRB.', hasEsrb: true },
  ];

  selected: DimDef = this.dims[0];
  records: DimRecord[] = [];
  loading = false;
  searchText = '';
  page = 0;
  pageSize = 100;

  ngOnInit(): void {
    this.loadDim(this.dims[0]);
  }

  loadDim(dim: DimDef): void {
    this.selected = dim;
    this.page = 0;
    this.searchText = '';
    this.fetch();
  }

  fetch(): void {
    this.loading = true;
    this.records = [];
    const obs = this.getObs();
    obs.subscribe({
      next: (data) => { this.records = data; this.loading = false; this.cdr.detectChanges(); },
      error: () => { this.loading = false; this.cdr.detectChanges(); },
    });
  }

  private getObs() {
    switch (this.selected.key) {
      case 'plataformas':     return this.svc.getPlataformas(this.page, this.pageSize);
      case 'generos':         return this.svc.getGeneros(this.page, this.pageSize);
      case 'desarrolladores': return this.svc.getDesarrolladores(this.page, this.pageSize);
      case 'publicadores':    return this.svc.getPublicadores(this.page, this.pageSize);
      default:                return this.svc.getEsrb(this.page, this.pageSize);
    }
  }

  prevPage(): void { if (this.page > 0) { this.page--; this.fetch(); } }
  nextPage(): void { if (this.records.length === this.pageSize) { this.page++; this.fetch(); } }

  get filtered(): DimRecord[] {
    if (!this.searchText.trim()) return this.records;
    const q = this.searchText.toLowerCase();
    return this.records.filter(r =>
      r.nombre.toLowerCase().includes(q) ||
      (r.codigo?.toLowerCase().includes(q) ?? false)
    );
  }
}
