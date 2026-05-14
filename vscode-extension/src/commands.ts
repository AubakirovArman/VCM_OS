import * as vscode from 'vscode';
import { VcmClient } from './vcmClient';
import { MemoryTreeProvider } from './memoryTreeProvider';

export function registerCommands(
  context: vscode.ExtensionContext,
  client: VcmClient,
  treeProvider: MemoryTreeProvider,
  getProjectId: () => string,
  getSessionId: () => string,
): void {

  // Search Memory
  context.subscriptions.push(
    vscode.commands.registerCommand('vcm.search', async () => {
      const query = await vscode.window.showInputBox({
        prompt: 'Search project memory',
        placeHolder: 'e.g. "database config" or "auth middleware"',
      });
      if (!query) return;

      try {
        const results = await client.searchMemory(getProjectId(), query, 10);
        if (results.length === 0) {
          vscode.window.showInformationMessage('No memories found.');
          return;
        }

        const items = results.map(r => ({
          label: r.text.length > 60 ? r.text.slice(0, 60) + '...' : r.text,
          description: `${r.type} | score: ${(r.score || 0).toFixed(3)}`,
          detail: r.text,
          memoryId: r.memory_id,
        }));

        const selected = await vscode.window.showQuickPick(items, {
          placeHolder: `Found ${results.length} memories`,
        });

        if (selected?.memoryId) {
          vscode.window.showInformationMessage(`Memory: ${selected.detail}`);
        }
      } catch (err: any) {
        vscode.window.showErrorMessage(`Search failed: ${err.message}`);
      }
    })
  );

  // Ingest Git
  context.subscriptions.push(
    vscode.commands.registerCommand('vcm.ingestGit', async () => {
      try {
        const gitExtension = vscode.extensions.getExtension('vscode.git');
        if (!gitExtension) {
          vscode.window.showWarningMessage('Git extension not found.');
          return;
        }

        const git = gitExtension.exports.getAPI(1);
        const repo = git.repositories[0];
        if (!repo) {
          vscode.window.showWarningMessage('No Git repository found.');
          return;
        }

        const diff = await repo.diff();
        const status = repo.state.workingTreeChanges.map((c: any) => `${c.status} ${c.resourceUri.fsPath}`).join('\n');

        if (diff) {
          await client.ingestEvent(getProjectId(), getSessionId(), 'code_change', diff, { source: 'git_diff' });
        }
        if (status) {
          await client.ingestEvent(getProjectId(), getSessionId(), 'event', status, { source: 'git_status' });
        }

        vscode.window.showInformationMessage(`Ingested git: ${diff.length} chars diff, ${status.length} chars status.`);
        treeProvider.refresh();
      } catch (err: any) {
        vscode.window.showErrorMessage(`Git ingest failed: ${err.message}`);
      }
    })
  );

  // Show Project State
  context.subscriptions.push(
    vscode.commands.registerCommand('vcm.showState', async () => {
      try {
        const state = await client.getProjectState(getProjectId());
        const lines = [
          `Project: ${state.project_id}`,
          `Total memories: ${state.total_memories}`,
          ``,
          `Active Decisions (${state.active_decisions.length}):`,
          ...state.active_decisions.map(d => `  • ${d.text.slice(0, 80)}`),
          ``,
          `Recent Errors (${state.recent_errors.length}):`,
          ...state.recent_errors.map(e => `  • ${e.text.slice(0, 80)}`),
          ``,
          `Active Goals (${state.active_goals.length}):`,
          ...state.active_goals.map(g => `  • ${g.text.slice(0, 80)}`),
        ];

        const doc = await vscode.workspace.openTextDocument({
          content: lines.join('\n'),
          language: 'markdown',
        });
        await vscode.window.showTextDocument(doc, { preview: true });
      } catch (err: any) {
        vscode.window.showErrorMessage(`Failed to get state: ${err.message}`);
      }
    })
  );

  // Refresh
  context.subscriptions.push(
    vscode.commands.registerCommand('vcm.refresh', () => {
      treeProvider.refresh();
      vscode.window.showInformationMessage('VCM Memory panel refreshed.');
    })
  );

  // Correct Memory
  context.subscriptions.push(
    vscode.commands.registerCommand('vcm.correctMemory', async (item?: any) => {
      const memoryId = item?.memoryId;
      if (!memoryId) {
        vscode.window.showWarningMessage('No memory selected.');
        return;
      }

      const action = await vscode.window.showQuickPick(
        ['stale', 'incorrect', 'important', 'duplicate', 'pin', 'unpin', 'delete'],
        { placeHolder: 'Select correction action' }
      );
      if (!action) return;

      const reason = await vscode.window.showInputBox({
        prompt: 'Reason for correction (optional)',
      });

      try {
        await client.correctMemory(memoryId, action, reason || '');
        vscode.window.showInformationMessage(`Memory corrected: ${action}`);
        treeProvider.refresh();
      } catch (err: any) {
        vscode.window.showErrorMessage(`Correction failed: ${err.message}`);
      }
    })
  );

  // Enable/Disable Auto-Ingest
  context.subscriptions.push(
    vscode.commands.registerCommand('vcm.enableAutoIngest', () => {
      vscode.workspace.getConfiguration('vcm').update('autoIngest', true, true);
      vscode.window.showInformationMessage('VCM auto-ingest enabled.');
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('vcm.disableAutoIngest', () => {
      vscode.workspace.getConfiguration('vcm').update('autoIngest', false, true);
      vscode.window.showInformationMessage('VCM auto-ingest disabled.');
    })
  );

  // Open Settings
  context.subscriptions.push(
    vscode.commands.registerCommand('vcm.openSettings', () => {
      vscode.commands.executeCommand('workbench.action.openSettings', 'vcm');
    })
  );
}
