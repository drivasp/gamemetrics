import { Component, OnDestroy, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { timeout, catchError, of, firstValueFrom } from 'rxjs';
import { LibraryService, LibraryItem } from '../../services/library.service';
import { WalletService } from '../../services/wallet.service';
import {
  LauncherService,
  LauncherLibraryItem,
  Achievement,
} from '../../services/launcher.service';
import { AchievementPopupService } from '../../services/achievement-popup.service';
import { AuthService } from '../../services/auth.service';
import { MatIconModule } from '@angular/material/icon';
import { GameCoverComponent } from '../../shared/game-cover/game-cover.component';

const REFUND_WINDOW_DAYS = 14;

export interface MyAchievement {
  achievement_id: string;
  product_id: string;
  game_name: string;
  game_image: string | null;
  name: string;
  description: string;
  points: number;
  unlocked_at: string;
}

@Component({
  selector: 'app-library',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, MatIconModule, GameCoverComponent],
  templateUrl: './library.component.html',
  styleUrl: './library.component.scss',
})
export class LibraryComponent implements OnInit, OnDestroy {
  private libSvc = inject(LibraryService);
  private launcher = inject(LauncherService);
  private walletSvc = inject(WalletService);
  private popup = inject(AchievementPopupService);
  private auth = inject(AuthService);
  private cdr = inject(ChangeDetectorRef);

  tab: 'games' | 'achievements' = 'games';
  items: LauncherLibraryItem[] = [];
  myAchievements: MyAchievement[] = [];
  loading = true;
  achievementsLoading = false;
  paidBanner = false;

  /** Instalación en curso */
  installingId: string | null = null;
  private installTimer: ReturnType<typeof setInterval> | null = null;

  /** Sesión de juego */
  playing: LauncherLibraryItem | null = null;
  playSessionId = '';
  playSeconds = 0;
  private playTimer: ReturnType<typeof setInterval> | null = null;

  /** Panel de detalles / logros */
  detailItem: LauncherLibraryItem | null = null;
  achievements: Achievement[] = [];
  detailLoading = false;
  buildInfo: { version: string; file_size_bytes: number; os: string } | null = null;
  cloudSaves: any[] = [];
  saveSlots = [0, 1, 2];

  /** Modal de reembolso */
  refundItem: LibraryItem | null = null;
  refundStep: 1 | 2 | 3 | 'done' = 1;
  refundReason = '';
  refundNote = '';
  refundConfirm = false;
  refundLoading = false;
  refundError = '';
  refundSuccessMsg = '';
  refundAmount = 0;

  reasons = [
    'No funciona en mi equipo',
    'No es lo que esperaba',
    'Lo compré por error',
    'Problemas de rendimiento',
    'Ya no lo quiero',
    'Otro motivo',
  ];

  /** Confirmación desinstalar */
  uninstallItem: LauncherLibraryItem | null = null;
  uninstalling = false;

  ngOnInit(): void {
    this.paidBanner = new URLSearchParams(location.search).get('paid') === '1';
    this.load();
  }

  setTab(tab: 'games' | 'achievements'): void {
    this.tab = tab;
    if (tab === 'achievements') this.loadAchievements();
  }

  loadAchievements(): void {
    this.achievementsLoading = true;
    this.launcher.myAchievements().pipe(
      timeout(10000),
      catchError(() => of({ items: [], total: 0 })),
    ).subscribe({
      next: res => {
        this.myAchievements = res.items || [];
        this.achievementsLoading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.achievementsLoading = false;
        this.cdr.detectChanges();
      },
    });
  }

  ngOnDestroy(): void {
    this.clearInstallTimer();
    this.clearPlayTimer();
  }

  load(): void {
    this.loading = true;
    this.launcher.libraryStatus().pipe(
      timeout(12000),
      catchError(() => this.libSvc.getLibrary().pipe(
        timeout(10000),
        catchError(() => of([] as LibraryItem[])),
      )),
    ).subscribe({
      next: res => {
        if (Array.isArray(res)) {
          this.items = res.filter(i => !i.refunded).map(i => ({
            product_id: i.product_id,
            game_slug: i.game_slug,
            game_name: i.game_name,
            game_image: i.game_image,
            amount: i.amount,
            purchased_at: i.purchased_at,
            install_status: 'not_installed',
            progress_pct: 0,
            build_id: '',
            playtime_minutes: 0,
            active_session_id: null,
          }));
        } else {
          this.items = res.items || [];
        }
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => { this.loading = false; this.cdr.detectChanges(); },
    });
  }

  formatDate(value: string): string {
    const ms = this.toMs(value);
    if (!ms) return value;
    return new Date(ms).toLocaleDateString('es-ES', {
      year: 'numeric', month: 'short', day: 'numeric',
    });
  }

  formatPlaytime(minutes: number): string {
    if (!minutes || minutes < 1) return 'Nunca jugado';
    if (minutes < 60) return `${Math.round(minutes)} min`;
    const h = Math.floor(minutes / 60);
    const m = Math.round(minutes % 60);
    return m > 0 ? `${h} h ${m} min` : `${h} h`;
  }

  formatSize(bytes: number): string {
    if (!bytes) return '—';
    const gb = bytes / (1024 ** 3);
    return gb >= 1 ? `${gb.toFixed(1)} GB` : `${(bytes / (1024 ** 2)).toFixed(0)} MB`;
  }

  statusLabel(status: string): string {
    const m: Record<string, string> = {
      not_installed: 'No instalado',
      downloading: 'Descargando',
      installed: 'Listo para jugar',
      updating: 'Actualizando',
    };
    return m[status] || status;
  }

  daysLeft(item: { purchased_at: string }): number {
    const purchased = this.toMs(item.purchased_at);
    if (!purchased) return 0;
    const left = REFUND_WINDOW_DAYS * 24 * 60 * 60 * 1000 - (Date.now() - purchased);
    return Math.max(0, Math.ceil(left / (24 * 60 * 60 * 1000)));
  }

  canRefund(item: { purchased_at: string }): boolean {
    return this.daysLeft(item) > 0;
  }

  install(item: LauncherLibraryItem): void {
    if (this.installingId) return;
    this.installingId = item.product_id;
    item.install_status = 'downloading';
    item.progress_pct = 0;
    this.launcher.startInstall(item.product_id, item.game_name).subscribe({
      next: res => {
        item.build_id = res.install.build_id;
        const url = res.download_url || `/launcher/download/${res.download_token}`;
        void this.runRealDownload(item, url);
      },
      error: err => {
        this.installingId = null;
        item.install_status = 'not_installed';
        this.popup.showInfo('Instalación fallida', err?.error?.detail || 'No se pudo iniciar la instalación');
      },
    });
  }

  update(item: LauncherLibraryItem): void {
    if (this.installingId) return;
    this.installingId = item.product_id;
    item.install_status = 'updating';
    item.progress_pct = 0;
    this.launcher.startUpdate(item.product_id, item.game_name).subscribe({
      next: res => {
        if (!res.update_available || !res.download_url) {
          this.installingId = null;
          item.install_status = 'installed';
          item.update_available = false;
          this.popup.showInfo('Sin updates', res.message || 'Ya tienes la última versión');
          this.cdr.detectChanges();
          return;
        }
        item.build_id = res.install?.build_id || item.build_id;
        void this.runRealDownload(item, res.download_url, true);
      },
      error: err => {
        this.installingId = null;
        item.install_status = 'installed';
        this.popup.showInfo('Update fallido', err?.error?.detail || 'No se pudo actualizar');
        this.cdr.detectChanges();
      },
    });
  }

  private async runRealDownload(
    item: LauncherLibraryItem,
    downloadUrl: string,
    isUpdate = false,
  ): Promise<void> {
    this.clearInstallTimer();
    try {
      const desktop = (window as any).gamemetricsDesktop;
      if (desktop?.downloadAndInstall) {
        await desktop.downloadAndInstall({
          productId: item.product_id,
          gameName: item.game_name,
          downloadUrl,
          token: this.auth.getToken(),
          onProgress: (pct: number) => {
            item.progress_pct = pct;
            this.cdr.detectChanges();
            if (pct % 10 === 0) {
              this.launcher.updateProgress(item.product_id, pct).subscribe();
            }
          },
        });
        await firstValueFrom(this.launcher.verifyInstall(item.product_id));
        item.install_status = 'installed';
        item.progress_pct = 100;
        item.update_available = false;
        this.installingId = null;
        this.popup.showSuccess(
          isUpdate ? 'Actualización completada' : 'Instalación completada',
          `“${item.game_name}” listo en el cliente de escritorio.`,
        );
        this.cdr.detectChanges();
        return;
      }

      const { checksum } = await this.launcher.downloadPackage(downloadUrl, pct => {
        item.progress_pct = pct;
        this.cdr.detectChanges();
        if (pct > 0 && pct < 100 && pct % 15 < 3) {
          this.launcher.updateProgress(item.product_id, pct).subscribe();
        }
      });
      this.launcher.verifyInstall(item.product_id, checksum || undefined).subscribe({
        next: () => {
          item.install_status = 'installed';
          item.progress_pct = 100;
          item.update_available = false;
          this.installingId = null;
          this.popup.showSuccess(
            isUpdate ? 'Actualización completada' : 'Instalación completada',
            `“${item.game_name}” descargado y verificado (checksum OK).`,
          );
          this.cdr.detectChanges();
        },
        error: err => {
          this.installingId = null;
          item.install_status = isUpdate ? 'installed' : 'not_installed';
          this.popup.showInfo('Verificación fallida', err?.error?.detail || 'Checksum inválido');
          this.cdr.detectChanges();
        },
      });
    } catch (e: any) {
      this.installingId = null;
      item.install_status = isUpdate ? 'installed' : 'not_installed';
      this.popup.showInfo('Descarga fallida', e?.message || 'No se pudo descargar el paquete');
      this.cdr.detectChanges();
    }
  }

  askUninstall(item: LauncherLibraryItem): void {
    this.uninstallItem = item;
  }

  cancelUninstall(): void {
    this.uninstallItem = null;
    this.uninstalling = false;
  }

  confirmUninstall(): void {
    if (!this.uninstallItem) return;
    const item = this.uninstallItem;
    this.uninstalling = true;
    this.launcher.uninstall(item.product_id).subscribe({
      next: () => {
        item.install_status = 'not_installed';
        item.progress_pct = 0;
        this.uninstallItem = null;
        this.uninstalling = false;
        this.popup.showSuccess(
          'Juego desinstalado',
          `“${item.game_name}” se eliminó de este equipo. Puedes instalarlo de nuevo cuando quieras.`,
        );
        this.cdr.detectChanges();
      },
      error: err => {
        this.uninstalling = false;
        this.popup.showInfo('No se pudo desinstalar', err?.error?.detail || 'Intenta de nuevo');
        this.cdr.detectChanges();
      },
    });
  }

  play(item: LauncherLibraryItem): void {
    if (item.install_status !== 'installed') return;
    const desktop = (window as any).gamemetricsDesktop;
    if (desktop?.launchGame) {
      desktop.launchGame({ productId: item.product_id, gameName: item.game_name });
    }
    this.launcher.playStart(item.product_id, item.game_name).subscribe({
      next: res => {
        this.playing = item;
        this.playSessionId = res.session.session_id;
        this.playSeconds = 0;
        // Guardar logros para mostrarlos al cerrar el overlay (más visible)
        (item as any)._pendingUnlocks = res.unlocked_achievements || [];
        this.clearPlayTimer();
        this.playTimer = setInterval(() => {
          this.playSeconds++;
          this.cdr.detectChanges();
        }, 1000);
        this.cdr.detectChanges();
      },
      error: err => this.popup.showInfo('No se pudo iniciar', err?.error?.detail || 'Error al jugar'),
    });
  }

  stopPlay(): void {
    if (!this.playing || !this.playSessionId) return;
    const item = this.playing;
    const sessionId = this.playSessionId;
    const pendingUnlocks: string[] = (item as any)._pendingUnlocks || [];
    this.clearPlayTimer();
    this.launcher.playEnd(sessionId, item.product_id, this.playSeconds).subscribe({
      next: res => {
        const added = res.duration_minutes || (this.playSeconds / 60);
        item.playtime_minutes = Math.max(
          item.playtime_minutes || 0,
          (item.playtime_minutes || 0) + added,
          res.playtime_minutes || 0,
        );
        item.active_session_id = null;
        this.playing = null;
        this.playSessionId = '';
        this.playSeconds = 0;
        const unlocks = [
          ...pendingUnlocks,
          ...(res.unlocked_achievements || []),
        ].filter((v, i, a) => a.indexOf(v) === i);
        if (unlocks.length) {
          this.popup.showUnlock(unlocks, item.game_name);
          this.loadAchievements();
        } else {
          this.popup.showSuccess(
            'Sesión finalizada',
            res.message || `Jugaste ${Math.max(1, Math.round(added))} min`,
          );
        }
        this.cdr.detectChanges();
      },
      error: err => {
        this.playing = null;
        this.playSessionId = '';
        // Aun si falla el cierre en Pinot, mostrar logros de inicio de sesión
        if (pendingUnlocks.length) {
          this.popup.showUnlock(pendingUnlocks, item.game_name);
        } else {
          this.popup.showInfo('Sesión cerrada', err?.error?.detail || 'No se pudo guardar el tiempo');
        }
        this.cdr.detectChanges();
      },
    });
  }

  openDetails(item: LauncherLibraryItem): void {
    this.detailItem = item;
    this.detailLoading = true;
    this.achievements = [];
    this.buildInfo = null;
    this.cloudSaves = [];
    this.launcher.gameDetail(item.product_id, item.game_name).subscribe({
      next: d => {
        this.achievements = d.achievements;
        this.buildInfo = {
          version: d.build.version,
          file_size_bytes: d.build.file_size_bytes,
          os: d.build.os,
        };
        item.install_status = d.install.status;
        item.progress_pct = d.install.progress_pct;
        item.playtime_minutes = d.playtime_minutes;
        this.detailLoading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.detailLoading = false;
        this.cdr.detectChanges();
      },
    });
    this.launcher.listSaves(item.product_id).pipe(
      catchError(() => of({ items: [], max_slot: 2 })),
    ).subscribe({
      next: res => {
        this.cloudSaves = res.items || [];
        this.cdr.detectChanges();
      },
    });
  }

  saveFor(slot: number): any | null {
    return this.cloudSaves.find(s => Number(s.slot) === slot) || null;
  }

  syncCloudSave(item: LauncherLibraryItem, slot: number): void {
    const payload = {
      score: Math.floor(Math.random() * 1000),
      playtime_minutes: item.playtime_minutes || 0,
      game_name: item.game_name,
      saved_at: new Date().toISOString(),
    };
    this.launcher.putSave(item.product_id, slot, payload, `Autosave ${slot}`).subscribe({
      next: () => {
        this.popup.showSuccess(
          'Nube',
          `Slot ${slot} guardado · score ${payload.score} (demo, no es partida real)`,
        );
        this.launcher.listSaves(item.product_id).subscribe({
          next: res => { this.cloudSaves = res.items || []; this.cdr.detectChanges(); },
        });
      },
      error: err => this.popup.showInfo('Nube', err?.error?.detail || 'No se pudo guardar'),
    });
  }

  loadCloudSave(item: LauncherLibraryItem, slot: number): void {
    this.launcher.getSave(item.product_id, slot).subscribe({
      next: res => {
        const data = res?.data || {};
        this.popup.showSuccess(
          `Slot ${slot}`,
          `Score ${data.score ?? '—'} · ${data.saved_at || res.updated_at || ''}`,
        );
      },
      error: err => this.popup.showInfo('Nube', err?.error?.detail || 'Slot vacío'),
    });
  }

  deleteCloudSave(item: LauncherLibraryItem, slot: number): void {
    this.launcher.deleteSave(item.product_id, slot).subscribe({
      next: () => {
        this.cloudSaves = this.cloudSaves.filter(s => Number(s.slot) !== slot);
        this.popup.showSuccess('Nube', `Slot ${slot} eliminado`);
        this.cdr.detectChanges();
      },
      error: err => this.popup.showInfo('Nube', err?.error?.detail || 'No se pudo borrar'),
    });
  }

  closeDetails(): void {
    this.detailItem = null;
    this.cloudSaves = [];
  }

  unlockedCount(): number {
    return this.achievements.filter(a => a.unlocked).length;
  }

  playClock(): string {
    const m = Math.floor(this.playSeconds / 60).toString().padStart(2, '0');
    const s = (this.playSeconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  }

  // ── Reembolso ─────────────────────────────────────────────

  openRefund(item: LauncherLibraryItem): void {
    if (!this.canRefund(item)) return;
    this.libSvc.getLibrary().subscribe({
      next: list => {
        const found = list.find(x => x.product_id === item.product_id && !x.refunded);
        if (!found) {
          this.popup.showInfo('Reembolso', 'No se encontró la compra para reembolsar');
          return;
        }
        this.refundItem = found;
        this.refundStep = 1;
        this.refundReason = '';
        this.refundNote = '';
        this.refundConfirm = false;
        this.refundLoading = false;
        this.refundError = '';
        this.refundSuccessMsg = '';
        this.refundAmount = found.amount;
        this.cdr.detectChanges();
      },
    });
  }

  closeRefund(): void {
    this.refundItem = null;
    this.refundLoading = false;
  }

  nextStep(): void {
    this.refundError = '';
    if (this.refundStep === 1) { this.refundStep = 2; return; }
    if (this.refundStep === 2) {
      if (!this.refundReason) {
        this.refundError = 'Selecciona un motivo para continuar.';
        return;
      }
      this.refundStep = 3;
    }
  }

  prevStep(): void {
    this.refundError = '';
    if (this.refundStep === 2) this.refundStep = 1;
    else if (this.refundStep === 3) this.refundStep = 2;
  }

  submitRefund(): void {
    if (!this.refundItem || !this.refundConfirm || !this.refundReason) return;
    this.refundLoading = true;
    this.refundError = '';
    const reason = this.refundNote.trim()
      ? `${this.refundReason}: ${this.refundNote.trim()}`
      : this.refundReason;

    this.libSvc.requestRefund(this.refundItem.purchase_id, reason).subscribe({
      next: res => {
        this.refundLoading = false;
        this.refundAmount = res.amount;
        this.refundSuccessMsg = res.message;
        this.refundStep = 'done';
        this.walletSvc.refresh();
        this.load();
        this.cdr.detectChanges();
      },
      error: err => {
        this.refundLoading = false;
        this.refundError = err?.error?.detail || 'No se pudo procesar el reembolso';
        this.cdr.detectChanges();
      },
    });
  }

  private clearInstallTimer(): void {
    if (this.installTimer) {
      clearInterval(this.installTimer);
      this.installTimer = null;
    }
  }

  private clearPlayTimer(): void {
    if (this.playTimer) {
      clearInterval(this.playTimer);
      this.playTimer = null;
    }
  }

  private toMs(value: string): number {
    const n = Number(value);
    if (Number.isFinite(n) && n > 0) return n;
    const d = Date.parse(value);
    return Number.isFinite(d) ? d : 0;
  }
}
