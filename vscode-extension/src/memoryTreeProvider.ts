import * as vscode from 'vscode';
import { VcmClient, VcmMemory, VcmProjectState } from './vcmClient';

export class MemoryTreeItem extends vscode.TreeItem {
  constructor(
    public readonly id: string,
    public readonly label: string,
    public readonly collapsibleState: vscode.TreeItemCollapsibleState,
    public readonly contextValue: string = 'memory',
    public readonly memoryType?: string,
    public readonly memoryId?: string,
  ) {
    super(label, collapsibleState);
    this.id = id;
    this.tooltip = label;
    this.iconPath = this.getIcon();
  }

  private getIcon(): vscode.ThemeIcon {
    switch (this.memoryType) {
      case 'decision':
        return new vscode.ThemeIcon('git-commit', new vscode.ThemeColor('charts.green'));
      case 'error':
        return new vscode.ThemeIcon('warning', new vscode.ThemeColor('charts.red'));
      case 'goal':
        return new vscode.ThemeIcon('target', new vscode.ThemeColor('charts.blue'));
      case 'code_change':
        return new vscode.ThemeIcon('file-code', new vscode.ThemeColor('charts.yellow'));
      case 'stale':
        return new vscode.ThemeIcon('archive', new vscode.ThemeColor('disabledForeground'));
      default:
        return new vscode.ThemeIcon('circle-filled');
    }
  }
}

export class MemoryTreeProvider implements vscode.TreeDataProvider<MemoryTreeItem> {
  private _onDidChangeTreeData: vscode.EventEmitter<MemoryTreeItem | undefined | void> = new vscode.EventEmitter<MemoryTreeItem | undefined | void>();
  readonly onDidChangeTreeData: vscode.Event<MemoryTreeItem | undefined | void> = this._onDidChangeTreeData.event;

  private client: VcmClient;
  private projectId: string;
  private state: VcmProjectState | null = null;
  private memories: VcmMemory[] = [];

  constructor(client: VcmClient, projectId: string) {
    this.client = client;
    this.projectId = projectId;
  }

  refresh(): void {
    this._onDidChangeTreeData.fire();
  }

  updateProjectId(projectId: string): void {
    this.projectId = projectId;
    this.refresh();
  }

  getTreeItem(element: MemoryTreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(element?: MemoryTreeItem): Promise<MemoryTreeItem[]> {
    if (!element) {
      // Root level
      try {
        this.state = await this.client.getProjectState(this.projectId);
      } catch {
        this.state = null;
      }

      if (!this.state) {
        return [new MemoryTreeItem('no-data', 'No VCM data (server running?)', vscode.TreeItemCollapsibleState.None, 'info')];
      }

      const items: MemoryTreeItem[] = [];
      items.push(new MemoryTreeItem(
        'project',
        `Project: ${this.state.project_id} (${this.state.total_memories} memories)`,
        vscode.TreeItemCollapsibleState.None,
        'project'
      ));

      if (this.state.active_decisions?.length > 0) {
        items.push(new MemoryTreeItem(
          'decisions',
          `Decisions (${this.state.active_decisions.length})`,
          vscode.TreeItemCollapsibleState.Expanded,
          'category',
        ));
      }

      if (this.state.recent_errors?.length > 0) {
        items.push(new MemoryTreeItem(
          'errors',
          `Errors (${this.state.recent_errors.length})`,
          vscode.TreeItemCollapsibleState.Expanded,
          'category',
        ));
      }

      if (this.state.active_goals?.length > 0) {
        items.push(new MemoryTreeItem(
          'goals',
          `Goals (${this.state.active_goals.length})`,
          vscode.TreeItemCollapsibleState.Expanded,
          'category',
        ));
      }

      items.push(new MemoryTreeItem(
        'search',
        'Search Memory...',
        vscode.TreeItemCollapsibleState.None,
        'action',
      ));

      return items;
    }

    if (element.id === 'decisions' && this.state) {
      return this.state.active_decisions.map(d => new MemoryTreeItem(
        `dec-${d.id}`,
        d.text.length > 60 ? d.text.slice(0, 60) + '...' : d.text,
        vscode.TreeItemCollapsibleState.None,
        'memory',
        'decision',
        d.id,
      ));
    }

    if (element.id === 'errors' && this.state) {
      return this.state.recent_errors.map(e => new MemoryTreeItem(
        `err-${e.id}`,
        e.text.length > 60 ? e.text.slice(0, 60) + '...' : e.text,
        vscode.TreeItemCollapsibleState.None,
        'memory',
        'error',
        e.id,
      ));
    }

    if (element.id === 'goals' && this.state) {
      return this.state.active_goals.map(g => new MemoryTreeItem(
        `goal-${g.id}`,
        g.text.length > 60 ? g.text.slice(0, 60) + '...' : g.text,
        vscode.TreeItemCollapsibleState.None,
        'memory',
        'goal',
        g.id,
      ));
    }

    return [];
  }
}
