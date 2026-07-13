// SAGE Database - SQLite storage for command history
import BetterSqlite3 from 'better-sqlite3';
import { homedir } from 'os';
import { join } from 'path';
import { mkdirSync, existsSync } from 'fs';
import { SCHEMA, MIGRATIONS } from './schema.js';

export interface RunRecord {
  command: string;
  exitCode: number;
  stdout: string;
  stderr: string;
  compressed: string;
  originalTokens: number;
  compressedTokens: number;
  durationMs: number;
}

export interface SavedRun extends RunRecord {
  id: number;
  createdAt: string;
}

export class Database {
  private static instance: Database;
  private db: BetterSqlite3.Database;

  private constructor() {
    const dataDir = this.getDataDir();
    if (!existsSync(dataDir)) {
      mkdirSync(dataDir, { recursive: true });
    }

    const dbPath = join(dataDir, 'sage.db');
    this.db = new BetterSqlite3(dbPath);
    this.db.pragma('journal_mode = WAL');
    this.initSchema();
  }

  static getInstance(): Database {
    if (!Database.instance) {
      Database.instance = new Database();
    }
    return Database.instance;
  }

  private getDataDir(): string {
    const home = homedir();
    if (process.platform === 'win32') {
      return join(process.env.LOCALAPPDATA || join(home, 'AppData', 'Local'), 'SAGE');
    }
    return join(home, '.sage');
  }

  private initSchema(): void {
    this.db.exec(SCHEMA);
    this.runMigrations();
  }

  private runMigrations(): void {
    const currentVersion = this.getSchemaVersion();

    for (const migration of MIGRATIONS) {
      if (migration.version > currentVersion) {
        this.db.exec(migration.sql);
        this.setSchemaVersion(migration.version);
      }
    }
  }

  private getSchemaVersion(): number {
    try {
      const row = this.db.prepare('SELECT version FROM schema_version ORDER BY version DESC LIMIT 1').get() as { version: number } | undefined;
      return row?.version || 0;
    } catch {
      return 0;
    }
  }

  private setSchemaVersion(version: number): void {
    this.db.prepare('INSERT INTO schema_version (version) VALUES (?)').run(version);
  }

  saveRun(record: RunRecord): number {
    const stmt = this.db.prepare(`
      INSERT INTO runs (command, exit_code, stdout, stderr, compressed, original_tokens, compressed_tokens, duration_ms, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    `);

    const result = stmt.run(
      record.command,
      record.exitCode,
      record.stdout,
      record.stderr,
      record.compressed,
      record.originalTokens,
      record.compressedTokens,
      record.durationMs
    );

    return result.lastInsertRowid as number;
  }

  getLatestRun(): SavedRun | null {
    const row = this.db.prepare(`
      SELECT * FROM runs ORDER BY id DESC LIMIT 1
    `).get() as any;

    return row ? this.mapRow(row) : null;
  }

  getLatestFailedRun(): SavedRun | null {
    const row = this.db.prepare(`
      SELECT * FROM runs WHERE exit_code != 0 ORDER BY id DESC LIMIT 1
    `).get() as any;

    return row ? this.mapRow(row) : null;
  }

  getRecentRuns(limit: number = 10): SavedRun[] {
    const rows = this.db.prepare(`
      SELECT * FROM runs ORDER BY id DESC LIMIT ?
    `).all(limit) as any[];

    return rows.map(row => this.mapRow(row));
  }

  getRunById(id: number): SavedRun | null {
    const row = this.db.prepare(`
      SELECT * FROM runs WHERE id = ?
    `).get(id) as any;

    return row ? this.mapRow(row) : null;
  }

  findSimilarCommands(command: string, limit: number = 20): SavedRun[] {
    // Extract base command for matching
    const baseCmd = command.split(/\s+/)[0];

    const rows = this.db.prepare(`
      SELECT * FROM runs
      WHERE command LIKE ?
      ORDER BY id DESC
      LIMIT ?
    `).all(`${baseCmd}%`, limit) as any[];

    return rows.map(row => this.mapRow(row));
  }

  findExactCommand(command: string): SavedRun[] {
    const rows = this.db.prepare(`
      SELECT * FROM runs WHERE command = ? ORDER BY id DESC
    `).all(command) as any[];

    return rows.map(row => this.mapRow(row));
  }

  getTotalStats(): { runs: number; savedTokens: number; totalTime: number } {
    const row = this.db.prepare(`
      SELECT
        COUNT(*) as runs,
        COALESCE(SUM(original_tokens - compressed_tokens), 0) as saved_tokens,
        COALESCE(SUM(duration_ms), 0) as total_time
      FROM runs
    `).get() as any;

    return {
      runs: row.runs || 0,
      savedTokens: row.saved_tokens || 0,
      totalTime: row.total_time || 0
    };
  }

  private mapRow(row: any): SavedRun {
    return {
      id: row.id,
      command: row.command,
      exitCode: row.exit_code,
      stdout: row.stdout,
      stderr: row.stderr,
      compressed: row.compressed,
      originalTokens: row.original_tokens,
      compressedTokens: row.compressed_tokens,
      durationMs: row.duration_ms,
      createdAt: row.created_at
    };
  }

  close(): void {
    this.db.close();
  }
}
