import * as vscode from 'vscode';
import { VcmClient } from './vcmClient';

export function registerAutoIngest(
  context: vscode.ExtensionContext,
  client: VcmClient,
  getProjectId: () => string,
  getSessionId: () => string,
): void {
  let lastIngestTime = 0;
  const COOLDOWN_MS = 5000;

  const shouldIngest = (): boolean => {
    const config = vscode.workspace.getConfiguration('vcm');
    return config.get<boolean>('autoIngest', true);
  };

  // Ingest on file save
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument(async (doc) => {
      if (!shouldIngest()) return;
      if (doc.uri.scheme !== 'file') return;

      const now = Date.now();
      if (now - lastIngestTime < COOLDOWN_MS) return;
      lastIngestTime = now;

      try {
        const content = doc.getText();
        const fileName = doc.fileName;
        await client.ingestEvent(
          getProjectId(),
          getSessionId(),
          'code_change',
          `Saved file: ${fileName}\n\n${content.slice(0, 2000)}`,
          { file_path: fileName, event_type: 'file_save' }
        );
      } catch {
        // Silently fail for auto-ingest
      }
    })
  );

  // Ingest on git commit (via Git extension API if available)
  const gitExtension = vscode.extensions.getExtension('vscode.git');
  if (gitExtension) {
    gitExtension.activate().then((git) => {
      const api = git.getAPI(1);
      context.subscriptions.push(
        api.onDidChangeState(async () => {
          if (!shouldIngest()) return;
          const repo = api.repositories[0];
          if (!repo) return;

          try {
            const diff = await repo.diff();
            if (diff && diff.length > 0) {
              await client.ingestEvent(
                getProjectId(),
                getSessionId(),
                'code_change',
                diff,
                { source: 'git_diff_auto' }
              );
            }
          } catch {
            // Silently fail
          }
        })
      );
    });
  }
}
