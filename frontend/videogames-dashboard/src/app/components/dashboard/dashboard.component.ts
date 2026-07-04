import { Component, OnInit, OnDestroy, inject, ElementRef, ViewChild, AfterViewInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration } from 'chart.js';
import { GameService, VideoGame, CountDTO } from '../../services/game.service';
import { EtlService, EtlStatus } from '../../services/etl.service';
import * as d3 from 'd3';

const NUM_SEMANAS = 17;
type EtlJobKey = 'dataset' | 'empresa' | 'dimensiones' | 'realtime' | 'catalogo' | 'promociones';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, BaseChartDirective],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit, AfterViewInit, OnDestroy {
  private gameService = inject(GameService);
  private etlService = inject(EtlService);
  private cdr = inject(ChangeDetectorRef);

  activeTab: 'etl' | 'analytics' = 'etl';

  // Semanas Analytics
  readonly numSemanas = NUM_SEMANAS;
  readonly semanasList = Array.from({ length: NUM_SEMANAS }, (_, i) => i + 1);
  selectedSemana = 1;

  // Semanas ETL
  selectedSemanaETL = 1;
  readonly semanasETLList = Array.from({ length: NUM_SEMANAS }, (_, i) => i + 1);
  semanasStatus: number[] = [];        // semanas ya cargadas en Pinot
  confirmSemana: number | null = null; // semana pendiente de confirmación para reemplazar

  // ETL
  etlStatus: EtlStatus = {
    dataset:     { status: 'idle', mensaje: '' },
    empresa:     { status: 'idle', mensaje: '' },
    dimensiones: { status: 'idle', mensaje: '' },
    realtime:    { status: 'idle', mensaje: '' },
    catalogo:    { status: 'idle', mensaje: '' },
    promociones: { status: 'idle', mensaje: '' },
  };
  etlLog: string[] = ['> Sistema listo. Esperando acciones ETL...'];
  private pollInterval: ReturnType<typeof setInterval> | null = null;
  private prevStatus: Record<EtlJobKey, string> = {
    dataset: '', empresa: '', dimensiones: '', realtime: '', catalogo: '', promociones: '',
  };

  @ViewChild('treemapContainer') treemapContainer!: ElementRef;

  // KPIs
  totalGames = 0;
  bestGame = '';
  topPlatform = '';
  topGenre = '';
  top10Games: VideoGame[] = [];
  genreData: CountDTO[] = [];

  scatterData: ChartConfiguration<'scatter'>['data'] = { datasets: [] };
  scatterOptions: ChartConfiguration<'scatter'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      title: { display: true, text: 'Rating vs Metacritic', color: '#e0e0e0', font: { size: 13 } },
    },
    scales: {
      x: { min: 0, max: 5, title: { display: true, text: 'Rating', color: '#aaa' }, ticks: { color: '#aaa' }, grid: { color: 'rgba(99,102,241,0.1)' } },
      y: { min: 0, max: 100, title: { display: true, text: 'Metacritic', color: '#aaa' }, ticks: { color: '#aaa' }, grid: { color: 'rgba(99,102,241,0.1)' } },
    },
  };

  timelineData: ChartConfiguration<'line'>['data'] = { labels: [], datasets: [] };
  timelineOptions: ChartConfiguration<'line'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      title: { display: true, text: 'Lanzamientos por Año', color: '#e0e0e0', font: { size: 13 } },
    },
    scales: {
      x: { ticks: { color: '#aaa' }, grid: { color: 'rgba(99,102,241,0.1)' } },
      y: { ticks: { color: '#aaa' }, grid: { color: 'rgba(99,102,241,0.1)' } },
    },
  };

  ngOnInit(): void {
    this.loadStaticData();
    this.loadSemanaData();
    this.loadEtlStatus();
    this.loadSemanasStatus();
  }

  ngAfterViewInit(): void {  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  setTab(tab: 'etl' | 'analytics'): void {
    this.activeTab = tab;
    if (tab === 'analytics') setTimeout(() => this.drawTreemap(), 150);
  }

  setSemana(semana: number): void {
    this.selectedSemana = semana;
    this.loadSemanaData();
  }

  setSelectedSemanaETL(n: number): void {
    this.selectedSemanaETL = n;
    this.confirmSemana = null;
  }

  semanaYaCargada(n: number): boolean {
    return this.semanasStatus.includes(n);
  }

  loadSemanasStatus(): void {
    this.etlService.getSemanasStatus().subscribe({
      next: (r) => { this.semanasStatus = r.semanas; this.cdr.detectChanges(); },
      error: () => {},
    });
  }

  // ─── Carga estática (no cambia con semana) ──────────────────────────────────

  private loadStaticData(): void {}

  // ─── Carga reactiva a semana ────────────────────────────────────────────────

  private loadSemanaData(): void {
    const s = this.selectedSemana;

    // Top rated + top10 (cambia por semana porque el rating varía)
    this.gameService.getTopRated(s).subscribe({
      next: (games) => {
        if (games?.length) this.bestGame = games[0]?.name ?? '';
        this.top10Games = games.slice(0, 10);
        this.cdr.detectChanges();
      },
      error: () => {},
    });

    // Scatter (muestra distribución rating vs metacritic de la semana)
    this.gameService.getGames(0, 500, s).subscribe({
      next: (games) => {
        const filtered = games.filter((g) => g.rating > 0);
        this.scatterData = {
          datasets: [{ data: filtered.map((g) => ({ x: g.rating, y: g.metacritic })), backgroundColor: 'rgba(99,102,241,0.55)', pointRadius: 3 }],
        };
        this.cdr.detectChanges();
      },
      error: () => {},
    });

    // Total count
    this.gameService.getCount(s).subscribe({
      next: (r) => { this.totalGames = r.count; this.cdr.detectChanges(); },
      error: () => {},
    });

    // Top platform
    this.gameService.getByPlatform(s).subscribe({
      next: (data) => { if (data?.length) this.topPlatform = data[0].label; this.cdr.detectChanges(); },
      error: () => {},
    });

    // Top genre + treemap
    this.gameService.getByGenre(s).subscribe({
      next: (data) => {
        if (data?.length) this.topGenre = data[0].label;
        this.genreData = data;
        if (this.activeTab === 'analytics') setTimeout(() => this.drawTreemap(), 100);
        this.cdr.detectChanges();
      },
      error: () => {},
    });

    // Timeline
    this.gameService.getByYear(s).subscribe({
      next: (data) => {
        const sorted = [...data].sort((a, b) => a.label.localeCompare(b.label));
        this.timelineData = {
          labels: sorted.map((d) => d.label),
          datasets: [{
            data: sorted.map((d) => d.count),
            fill: true,
            borderColor: '#a78bfa',
            backgroundColor: 'rgba(167,139,250,0.15)',
            tension: 0.4,
            pointRadius: 2,
          }],
        };
        this.cdr.detectChanges();
      },
      error: () => {},
    });
  }

  // ─── ETL ─────────────────────────────────────────────────────────────────────

  private logEntry(msg: string): void {
    const time = new Date().toTimeString().slice(0, 8);
    this.etlLog = [`[${time}] ${msg}`, ...this.etlLog].slice(0, 80);
  }

  loadEtlStatus(): void {
    this.etlService.getStatus().subscribe({
      next: (s) => {
        this.etlStatus = s;
        // Sync prevStatus so the polling baseline is correct from the start
        this.prevStatus.dataset     = s.dataset.status;
        this.prevStatus.empresa     = s.empresa.status;
        this.prevStatus.dimensiones = s.dimensiones.status;
        if (s.realtime) this.prevStatus.realtime = s.realtime.status;
        if (s.catalogo) this.prevStatus.catalogo = s.catalogo.status;
        if (s.promociones) this.prevStatus.promociones = s.promociones.status;
        this.cdr.detectChanges();
        // Auto-start polling when a job is already running (e.g. init script)
        const anyRunning =
          s.dataset.status === 'running' ||
          s.empresa.status === 'running' ||
          s.dimensiones.status === 'running' ||
          s.realtime?.status === 'running' ||
          s.catalogo?.status === 'running' ||
          s.promociones?.status === 'running';
        if (anyRunning) this.startPolling();
      },
      error: () => {},
    });
  }

  private startPolling(): void {
    if (this.pollInterval) return;
    this.pollInterval = setInterval(() => {
      this.etlService.getStatus().subscribe({
        next: (s) => {
          (['dataset', 'empresa', 'dimensiones', 'realtime', 'catalogo', 'promociones'] as EtlJobKey[]).forEach((key) => {
            if (!s[key]) return;
            const prev = this.prevStatus[key];
            const curr = s[key].status;
            const msg  = s[key].mensaje;
            if (prev === 'running' && curr === 'ok') {
              this.logEntry(`✓ ${key} completado.`);
              if (key === 'dataset') {
                this.loadStaticData();
                this.loadSemanaData();
                this.loadSemanasStatus(); // refrescar qué semanas están cargadas
              }
            } else if (prev === 'running' && curr === 'error') {
              this.logEntry(`✗ ${key} falló: ${msg}`);
            } else if (curr === 'running' && msg && msg !== this.etlStatus[key].mensaje) {
              this.logEntry(`  ${msg}`);
            }
            this.prevStatus[key] = curr;
          });
          this.etlStatus = s;
          this.cdr.detectChanges();
          if (
            s.dataset.status !== 'running' && s.empresa.status !== 'running' &&
            s.dimensiones.status !== 'running' &&
            s.realtime?.status !== 'running' && s.catalogo?.status !== 'running' &&
            s.promociones?.status !== 'running'
          ) this.stopPolling();
        },
        error: () => {},
      });
    }, 3000);
  }

  private stopPolling(): void {
    if (this.pollInterval) { clearInterval(this.pollInterval); this.pollInterval = null; }
  }

  reloadDataset(force = false): void {
    if (this.etlStatus.dataset.status === 'running') return;
    const semana = this.selectedSemanaETL;

    this.etlService.reloadDataset(semana, force).subscribe({
      next: (res) => {
        if (res.ya_existe && !force) {
          // Semana ya existe — pedir confirmación sin iniciar nada
          this.confirmSemana = semana;
          this.logEntry(`⚠ Semana ${semana} ya está cargada. Confirma para reemplazarla.`);
          this.cdr.detectChanges();
          return;
        }
        // Iniciar job — update optimista
        this.confirmSemana = null;
        this.etlStatus.dataset = { status: 'running', mensaje: `Cargando semana ${semana}...` };
        this.logEntry(`▶ Cargando semana ${semana} → Pinot...`);
        this.prevStatus.dataset = 'running';
        this.cdr.detectChanges();
        this.startPolling();
      },
      error: (err) => {
        if (err?.status !== 409) {
          this.etlStatus.dataset = { status: 'error', mensaje: 'Error al iniciar' };
          this.logEntry('✗ Error al iniciar Dataset.');
          this.cdr.detectChanges();
        }
      },
    });
  }

  confirmarReemplazar(): void {
    this.reloadDataset(true);
  }

  cancelarConfirmacion(): void {
    this.confirmSemana = null;
    this.cdr.detectChanges();
  }

  reloadEmpresa(): void {
    if (this.etlStatus.empresa.status === 'running') return;
    this.etlStatus.empresa = { status: 'running', mensaje: 'Iniciando...' };
    this.logEntry('▶ Iniciando recarga de Tablas Empresa → PocketBase...');
    this.prevStatus.empresa = 'running';
    this.cdr.detectChanges();
    this.startPolling();
    this.etlService.reloadEmpresa().subscribe({
      next: () => {},
      error: (err) => {
        if (err?.status !== 409) {
          this.etlStatus.empresa = { status: 'error', mensaje: 'Error al iniciar' };
          this.logEntry('✗ Error al iniciar Tablas Empresa.');
          this.cdr.detectChanges();
        }
      },
    });
  }

  reloadDimensions(): void {
    if (this.etlStatus.dimensiones.status === 'running') return;
    this.etlStatus.dimensiones = { status: 'running', mensaje: 'Iniciando...' };
    this.logEntry('▶ Iniciando creación de Dimensiones → Pinot...');
    this.prevStatus.dimensiones = 'running';
    this.cdr.detectChanges();
    this.startPolling();
    this.etlService.reloadDimensions().subscribe({
      next: () => {},
      error: (err) => {
        if (err?.status !== 409) {
          this.etlStatus.dimensiones = { status: 'error', mensaje: 'Error al iniciar' };
          this.logEntry('✗ Error al iniciar Dimensiones.');
          this.cdr.detectChanges();
        }
      },
    });
  }

  createRealtimeTables(): void {
    if (this.etlStatus.realtime?.status === 'running') return;
    this.etlStatus.realtime = { status: 'running', mensaje: 'Iniciando...' };
    this.logEntry('▶ Fase 1: Crear tablas REALTIME comercio...');
    this.prevStatus.realtime = 'running';
    this.cdr.detectChanges();
    this.startPolling();
    this.etlService.createRealtimeTables().subscribe({ next: () => {}, error: () => {} });
  }

  reloadCatalogo(): void {
    if (this.etlStatus.catalogo?.status === 'running') return;
    this.etlStatus.catalogo = { status: 'running', mensaje: 'Iniciando...' };
    this.logEntry('▶ Fase 1: Catálogo comercial OFFLINE...');
    this.prevStatus.catalogo = 'running';
    this.cdr.detectChanges();
    this.startPolling();
    this.etlService.reloadCatalogo(this.selectedSemanaETL).subscribe({ next: () => {}, error: () => {} });
  }

  seedPromociones(): void {
    if (this.etlStatus.promociones?.status === 'running') return;
    this.etlStatus.promociones = { status: 'running', mensaje: 'Iniciando...' };
    this.logEntry('▶ Fase 1: Promociones estilo Steam...');
    this.prevStatus.promociones = 'running';
    this.cdr.detectChanges();
    this.startPolling();
    this.etlService.seedPromociones().subscribe({ next: () => {}, error: () => {} });
  }

  clearLog(): void {
    this.etlLog = ['> Log limpiado.'];
  }

  getStatusLabel(status: string): string {
    return status === 'idle' ? 'En espera' : status === 'running' ? 'Ejecutando' : status === 'ok' ? 'Completado' : 'Error';
  }

  // ─── Treemap ────────────────────────────────────────────────────────────────

  private drawTreemap(): void {
    if (!this.treemapContainer || this.genreData.length === 0) return;
    const el = this.treemapContainer.nativeElement;
    const width = el.clientWidth || 600;
    const height = 280;

    d3.select(el).select('svg').remove();
    const svg = d3.select(el).append('svg').attr('width', width).attr('height', height);
    const root = d3.hierarchy({ children: this.genreData } as any).sum((d: any) => d.count || 0);
    d3.treemap().size([width, height]).padding(3)(root);

    const palette = ['#6366f1','#8b5cf6','#a78bfa','#c4b5fd','#7c3aed','#5b21b6','#4c1d95','#2563eb','#3b82f6','#60a5fa'];
    const color = d3.scaleOrdinal(palette);

    const nodes = svg.selectAll('g').data(root.leaves()).enter().append('g')
      .attr('transform', (d: any) => `translate(${d.x0},${d.y0})`);
    nodes.append('rect')
      .attr('width', (d: any) => d.x1 - d.x0).attr('height', (d: any) => d.y1 - d.y0)
      .attr('fill', (_d: any, i: number) => color(String(i))).attr('opacity', 0.88).attr('rx', 4);
    nodes.append('text').attr('x', 6).attr('y', 16)
      .text((d: any) => d.data.label).attr('font-size', '11px').attr('fill', '#fff').attr('font-weight', '600');
  }

  getRatingWidth(rating: number): string {
    return `${(rating / 5) * 100}%`;
  }
}
