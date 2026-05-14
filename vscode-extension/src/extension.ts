import * as vscode from 'vscode';
import { VcmClient } from './vcmClient';
import { MemoryTreeProvider } from './memoryTreeProvider';
import { registerCommands } from './commands';
import { registerAutoIngest } from './autoIngest';

let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext) {
  const config = vscode.workspace.getConfiguration('vcm');
  const apiUrl = config.get<string>('apiUrl', 'http://localhost:8123');
  let projectId = config.get<string>('projectId', '');
  let sessionId = config.get<string>('sessionId', '');

  // Auto-detect project ID from workspace
  if (!projectId && vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length > 0) {
    const ws = vscode.workspace.workspaceFolders[0];
    projectId = `proj_${ws.name}`;
  }

  // Generate session ID if not set
  if (!sessionId) {
    sessionId = `sess_${Date.now().toString(36)}`;
    config.update('sessionId', sessionId, true);
  }

  const client = new VcmClient(apiUrl);
  const treeProvider = new MemoryTreeProvider(client, projectId);

  // Register tree view
  vscode.window.createTreeView('vcmMemoryPanel', {
    treeDataProvider: treeProvider,
  });

  // Register commands
  registerCommands(
    context,
    client,
    treeProvider,
    () => projectId,
    () => sessionId,
  );

  // Register auto-ingest
  registerAutoIngest(
    context,
    client,
    () => projectId,
    () => sessionId,
  );

  // Status bar
  statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.command = 'vcm.showState';
  context.subscriptions.push(statusBarItem);

  // Health check loop
  const updateStatus = async () => {
    try {
      const health = await client.health();
      const mems = health.basic?.memories || 0;
      statusBarItem.text = `$(database) VCM: ${mems}`;
      statusBarItem.tooltip = `VCM-OS connected\nMemories: ${mems}\nProjects: ${health.basic?.projects || 0}\nScore: ${health.score || '?'}`;
      statusBarItem.show();
      vscode.commands.executeCommand('setContext', 'vcm.enabled', true);
    } catch {
      statusBarItem.text = `$(database) VCM: off`;
      statusBarItem.tooltip = 'VCM-OS not connected. Run: vcm serve';
      statusBarItem.show();
      vscode.commands.executeCommand('setContext', 'vcm.enabled', false);
    }
  };

  updateStatus();
  const interval = setInterval(updateStatus, 10000);
  context.subscriptions.push({ dispose: () => clearInterval(interval) });

  // Watch config changes
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration(e => {
      if (e.affectsConfiguration('vcm.projectId')) {
        const newProjectId = vscode.workspace.getConfiguration('vcm').get<string>('projectId', '');
        if (newProjectId) {
          projectId = newProjectId;
          treeProvider.updateProjectId(projectId);
        }
      }
    })
  );

  vscode.window.showInformationMessage('VCM-OS extension activated.');
}

export function deactivate() {
  if (statusBarItem) {
    statusBarItem.dispose();
  }
}
