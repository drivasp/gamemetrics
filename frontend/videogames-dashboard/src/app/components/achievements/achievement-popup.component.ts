import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { AchievementPopupService } from '../../services/achievement-popup.service';

@Component({
  selector: 'app-achievement-popup',
  standalone: true,
  imports: [CommonModule, MatIconModule],
  templateUrl: './achievement-popup.component.html',
  styleUrl: './achievement-popup.component.scss',
})
export class AchievementPopupComponent {
  private popup = inject(AchievementPopupService);
  data$ = this.popup.data$;

  close(): void {
    this.popup.close();
  }
}
