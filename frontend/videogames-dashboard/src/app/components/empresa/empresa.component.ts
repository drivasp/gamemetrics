import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { EmpresaService, PbPage } from '../../services/empresa.service';

export interface FieldDef {
  name: string;
  label: string;
  type: 'text' | 'number' | 'bool' | 'email';
  required?: boolean;
  placeholder?: string;
}

interface TableDef {
  key: string;
  label: string;
  icon: string;
  desc: string;
  fields: FieldDef[];
}

@Component({
  selector: 'app-empresa',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './empresa.component.html',
  styleUrl: './empresa.component.scss',
})
export class EmpresaComponent implements OnInit {
  private svc = inject(EmpresaService);

  readonly tables: TableDef[] = [
    {
      key: 'plataformas', label: 'Plataformas', icon: '🖥️',
      desc: 'Plataformas de videojuegos disponibles en el catálogo.',
      fields: [
        { name: 'nombre',           label: 'Nombre',           type: 'text',   required: true },
        { name: 'fabricante',       label: 'Fabricante',       type: 'text',   placeholder: 'Sony, Microsoft, Nintendo…' },
        { name: 'tipo',             label: 'Tipo',             type: 'text',   placeholder: 'consola, PC, mobile, handheld' },
        { name: 'anno_lanzamiento', label: 'Año lanzamiento',  type: 'number' },
        { name: 'activa',           label: 'Activa',           type: 'bool' },
      ],
    },
    {
      key: 'generos', label: 'Géneros', icon: '🎭',
      desc: 'Géneros de videojuegos y su popularidad en el dataset.',
      fields: [
        { name: 'nombre',      label: 'Nombre',      type: 'text',   required: true },
        { name: 'descripcion', label: 'Descripción', type: 'text' },
        { name: 'popularidad', label: 'Popularidad', type: 'number', placeholder: 'Nº de juegos en este género' },
      ],
    },
    {
      key: 'clasificaciones_esrb', label: 'Clasificaciones ESRB', icon: '🔞',
      desc: 'Clasificaciones de contenido por edad de la ESRB.',
      fields: [
        { name: 'codigo',      label: 'Código',      type: 'text',   required: true, placeholder: 'E, E10+, T, M, AO, RP' },
        { name: 'nombre',      label: 'Nombre',      type: 'text' },
        { name: 'descripcion', label: 'Descripción', type: 'text' },
        { name: 'edad_minima', label: 'Edad mínima', type: 'number' },
      ],
    },
    {
      key: 'desarrolladores', label: 'Desarrolladores', icon: '💻',
      desc: 'Top 300 estudios desarrolladores extraídos del dataset.',
      fields: [
        { name: 'nombre',    label: 'Nombre',    type: 'text',  required: true },
        { name: 'pais',      label: 'País',      type: 'text' },
        { name: 'tipo',      label: 'Tipo',      type: 'text',  placeholder: 'indie, AAA, mid-size' },
        { name: 'sitio_web', label: 'Sitio web', type: 'text' },
        { name: 'activo',    label: 'Activo',    type: 'bool' },
      ],
    },
    {
      key: 'publicadores', label: 'Publicadores', icon: '📦',
      desc: 'Top 200 empresas publicadoras extraídas del dataset.',
      fields: [
        { name: 'nombre',    label: 'Nombre',    type: 'text',  required: true },
        { name: 'pais',      label: 'País',      type: 'text' },
        { name: 'tipo',      label: 'Tipo',      type: 'text',  placeholder: 'indie, AAA, mid-size' },
        { name: 'sitio_web', label: 'Sitio web', type: 'text' },
        { name: 'activo',    label: 'Activo',    type: 'bool' },
      ],
    },
    {
      key: 'empleados', label: 'Empleados', icon: '👤',
      desc: 'Personal de GameMetrics S.A. por departamento.',
      fields: [
        { name: 'nombre',        label: 'Nombre',        type: 'text',   required: true },
        { name: 'apellido',      label: 'Apellido',      type: 'text',   required: true },
        { name: 'cargo',         label: 'Cargo',         type: 'text' },
        { name: 'departamento',  label: 'Departamento',  type: 'text' },
        { name: 'email',         label: 'Email',         type: 'email' },
        { name: 'fecha_ingreso', label: 'Fecha ingreso', type: 'text',   placeholder: 'YYYY-MM-DD' },
        { name: 'salario',       label: 'Salario',       type: 'number' },
      ],
    },
    {
      key: 'contratos', label: 'Contratos', icon: '📄',
      desc: 'Contratos activos y vencidos con publicadores.',
      fields: [
        { name: 'publicador_nombre', label: 'Publicador',     type: 'text' },
        { name: 'tipo_contrato',     label: 'Tipo contrato',  type: 'text',   placeholder: 'exclusividad, licencia, distribución' },
        { name: 'fecha_inicio',      label: 'Fecha inicio',   type: 'text',   placeholder: 'YYYY-MM-DD' },
        { name: 'fecha_fin',         label: 'Fecha fin',      type: 'text',   placeholder: 'YYYY-MM-DD' },
        { name: 'valor',             label: 'Valor ($)',      type: 'number' },
        { name: 'estado',            label: 'Estado',         type: 'text',   placeholder: 'activo, vencido, cancelado' },
        { name: 'descripcion',       label: 'Descripción',    type: 'text' },
      ],
    },
    {
      key: 'catalogo_distribucion', label: 'Catálogo de Distribución', icon: '🛒',
      desc: 'Top 500 juegos por rating en el catálogo de GameMetrics.',
      fields: [
        { name: 'juego_nombre',        label: 'Juego',          type: 'text',   required: true },
        { name: 'juego_id',            label: 'ID juego',       type: 'text' },
        { name: 'plataforma_nombre',   label: 'Plataforma',     type: 'text' },
        { name: 'precio',              label: 'Precio ($)',      type: 'number' },
        { name: 'fecha_incorporacion', label: 'Fecha',          type: 'text',   placeholder: 'YYYY-MM-DD' },
        { name: 'region',              label: 'Región',         type: 'text',   placeholder: 'NA, EU, LATAM, Global' },
        { name: 'estado',              label: 'Estado',         type: 'text',   placeholder: 'activo, descontinuado, preventa' },
      ],
    },
    {
      key: 'campanas_marketing', label: 'Campañas de Marketing', icon: '📣',
      desc: 'Campañas de marketing por juego y canal.',
      fields: [
        { name: 'nombre',       label: 'Nombre campaña', type: 'text',   required: true },
        { name: 'juego_nombre', label: 'Juego',          type: 'text' },
        { name: 'genero_nombre',label: 'Género',         type: 'text' },
        { name: 'presupuesto',  label: 'Presupuesto ($)',type: 'number' },
        { name: 'gasto_real',   label: 'Gasto real ($)', type: 'number' },
        { name: 'fecha_inicio', label: 'Fecha inicio',   type: 'text',   placeholder: 'YYYY-MM-DD' },
        { name: 'fecha_fin',    label: 'Fecha fin',      type: 'text',   placeholder: 'YYYY-MM-DD' },
        { name: 'canal',        label: 'Canal',          type: 'text',   placeholder: 'redes, TV, influencers, email' },
        { name: 'estado',       label: 'Estado',         type: 'text',   placeholder: 'planificada, activa, finalizada' },
      ],
    },
    {
      key: 'evaluaciones_analiticas', label: 'Evaluaciones Analíticas', icon: '📊',
      desc: 'Evaluaciones internas de analistas sobre juegos clave.',
      fields: [
        { name: 'juego_nombre',         label: 'Juego',           type: 'text',   required: true },
        { name: 'empleado_nombre',      label: 'Analista',        type: 'text' },
        { name: 'puntuacion_comercial', label: 'Punt. comercial', type: 'number', placeholder: '1-10' },
        { name: 'puntuacion_tecnica',   label: 'Punt. técnica',   type: 'number', placeholder: '1-10' },
        { name: 'recomendacion',        label: 'Recomendación',   type: 'text',   placeholder: 'adquirir, rechazar, revisar' },
        { name: 'fecha_evaluacion',     label: 'Fecha',           type: 'text',   placeholder: 'YYYY-MM-DD' },
        { name: 'notas',                label: 'Notas',           type: 'text' },
      ],
    },
  ];

  private cdr = inject(ChangeDetectorRef);

  selected: TableDef = this.tables[0];
  page: PbPage | null = null;
  loading = false;
  currentPage = 1;
  columns: string[] = [];
  searchText = '';

  // CRUD state
  modalMode: 'create' | 'edit' | null = null;
  formData: Record<string, any> = {};
  editingId: string | null = null;
  saving = false;
  showDeleteConfirm = false;
  deleteId: string | null = null;
  deleteName = '';
  deleting = false;
  crudError = '';

  ngOnInit(): void {
    this.loadTable(this.tables[0]);
  }

  get currentFields(): FieldDef[] {
    return this.selected.fields;
  }

  loadTable(table: TableDef): void {
    this.selected = table;
    this.currentPage = 1;
    this.searchText = '';
    this.closeModal();
    this.fetchPage();
  }

  fetchPage(): void {
    this.loading = true;
    this.page = null;
    this.svc.getRecords(this.selected.key, this.currentPage).subscribe({
      next: (p) => {
        this.page = p;
        this.columns = p.items.length > 0 ? EmpresaService.visibleColumns(p.items[0]) : [];
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loading = false; this.cdr.detectChanges(); },
    });
  }

  goPage(n: number): void {
    if (!this.page) return;
    if (n < 1 || n > this.page.totalPages) return;
    this.currentPage = n;
    this.fetchPage();
  }

  get pageNumbers(): number[] {
    if (!this.page) return [];
    const total = this.page.totalPages;
    const cur = this.currentPage;
    const range: number[] = [];
    for (let i = Math.max(1, cur - 2); i <= Math.min(total, cur + 2); i++) range.push(i);
    return range;
  }

  formatCell(val: any): string {
    if (val === null || val === undefined || val === '') return '—';
    if (typeof val === 'boolean') return val ? 'Sí' : 'No';
    if (typeof val === 'number') return val.toLocaleString('es');
    const s = String(val);
    return s.length > 60 ? s.slice(0, 57) + '...' : s;
  }

  formatHeader(col: string): string {
    return col.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }

  get filteredItems(): Record<string, any>[] {
    if (!this.page) return [];
    if (!this.searchText.trim()) return this.page.items;
    const q = this.searchText.toLowerCase();
    return this.page.items.filter((row) =>
      this.columns.some((c) => String(row[c] ?? '').toLowerCase().includes(q))
    );
  }

  // ── CRUD ──────────────────────────────────────────────

  openCreate(): void {
    this.crudError = '';
    this.editingId = null;
    this.formData = {};
    for (const f of this.currentFields) {
      if (f.type === 'number') this.formData[f.name] = 0;
      else if (f.type === 'bool') this.formData[f.name] = false;
      else this.formData[f.name] = '';
    }
    this.modalMode = 'create';
  }

  openEdit(row: Record<string, any>): void {
    this.crudError = '';
    this.editingId = row['id'];
    this.formData = {};
    for (const f of this.currentFields) {
      const v = row[f.name];
      this.formData[f.name] = v !== undefined && v !== null ? v : (f.type === 'number' ? 0 : f.type === 'bool' ? false : '');
    }
    this.modalMode = 'edit';
  }

  closeModal(): void {
    this.modalMode = null;
    this.editingId = null;
    this.formData = {};
    this.crudError = '';
    this.saving = false;
  }

  save(): void {
    if (this.saving) return;
    this.crudError = '';
    this.saving = true;

    const payload: Record<string, any> = {};
    for (const f of this.currentFields) {
      let v = this.formData[f.name];
      if (f.type === 'number') v = Number(v) || 0;
      else if (f.type === 'bool') v = v === true || v === 'true';
      payload[f.name] = v ?? '';
    }

    const obs = this.editingId
      ? this.svc.updateRecord(this.selected.key, this.editingId, payload)
      : this.svc.createRecord(this.selected.key, payload);

    obs.subscribe({
      next: () => { this.saving = false; this.closeModal(); this.fetchPage(); },
      error: (err) => {
        this.saving = false;
        this.crudError = err?.error?.message || 'Error al guardar. Verifica los datos.';
        this.cdr.detectChanges();
      },
    });
  }

  confirmDelete(row: Record<string, any>): void {
    this.deleteId = row['id'];
    this.deleteName = row['nombre'] || row['name'] || row['codigo'] || row['id']?.slice(0, 8) || 'este registro';
    this.showDeleteConfirm = true;
  }

  cancelDelete(): void {
    this.showDeleteConfirm = false;
    this.deleteId = null;
    this.deleting = false;
  }

  executeDelete(): void {
    if (!this.deleteId || this.deleting) return;
    this.deleting = true;
    this.svc.deleteRecord(this.selected.key, this.deleteId).subscribe({
      next: () => { this.deleting = false; this.showDeleteConfirm = false; this.deleteId = null; this.fetchPage(); },
      error: () => { this.deleting = false; this.cdr.detectChanges(); },
    });
  }
}
