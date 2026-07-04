import { Component, OnInit, inject, ViewChild, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, MatPaginator, PageEvent } from '@angular/material/paginator';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { GameService, VideoGame } from '../../services/game.service';

@Component({
  selector: 'app-games-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatTableModule,
    MatPaginatorModule,
    MatFormFieldModule,
    MatInputModule,
  ],
  templateUrl: './games-list.component.html',
  styleUrl: './games-list.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GamesListComponent implements OnInit {
  private gameService = inject(GameService);
  private cdr = inject(ChangeDetectorRef);

  @ViewChild(MatPaginator) paginator!: MatPaginator;

  displayedColumns = ['name', 'released', 'rating', 'metacritic', 'genres', 'platforms', 'esrbRating'];
  games: VideoGame[] = [];
  filteredGames: VideoGame[] = [];
  totalGames = 0;
  pageSize = 20;
  pageIndex = 0;
  searchTerm = '';

  ngOnInit(): void {
    this.loadCount();
    this.loadGames();
  }

  private loadCount(): void {
    this.gameService.getCount().subscribe((res) => {
      this.totalGames = res.count;
      this.cdr.markForCheck();
    });
  }

  loadGames(): void {
    this.gameService.getGames(this.pageIndex, this.pageSize).subscribe((games) => {
      this.games = games;
      this.applyFilter();
      this.cdr.markForCheck();
    });
  }

  onPageChange(event: PageEvent): void {
    this.pageIndex = event.pageIndex;
    this.pageSize = event.pageSize;
    this.loadGames();
  }

  applyFilter(): void {
    const term = this.searchTerm.toLowerCase();
    if (!term) {
      this.filteredGames = [...this.games];
    } else {
      this.filteredGames = this.games.filter((g) =>
        g.name.toLowerCase().includes(term)
      );
    }
  }
}
