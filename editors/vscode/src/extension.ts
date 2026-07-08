import * as vscode from 'vscode';
import { LanguageClient, LanguageClientOptions, ServerOptions, TransportKind } from 'vscode-languageclient/node';

let client: LanguageClient;

export function activate(context: vscode.ExtensionContext) {
    const config = vscode.workspace.getConfiguration('sage');
    const transport = config.get<string>('transport', 'stdio');
    const tcpPort = config.get<number>('tcpPort', 19473);

    let serverOptions: ServerOptions;

    if (transport === 'tcp') {
        serverOptions = () => {
            const net = require('net');
            return new Promise((resolve) => {
                const socket = net.connect({ port: tcpPort, host: '127.0.0.1' });
                resolve({ reader: socket, writer: socket });
            });
        };
    } else {
        serverOptions = {
            command: 'sage',
            args: ['lsp'],
            transport: TransportKind.stdio,
        };
    }

    const clientOptions: LanguageClientOptions = {
        documentSelector: [
            { scheme: 'file', language: 'shellscript' },
            { scheme: 'file', language: 'powershell' },
            { scheme: 'file', language: 'bat' },
        ],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/sage.toml'),
        },
    };

    client = new LanguageClient('sage-lsp', 'SAGE LSP', serverOptions, clientOptions);
    client.start();

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('sage.predict', async () => {
            const input = await vscode.window.showInputBox({ prompt: 'Command to predict' });
            if (!input) return;
            const result = await client.sendRequest('sage/predict', { command: input });
            const r = result as any;
            if (r.ok) {
                const icon = r.will_fail ? '⚠️' : '✅';
                vscode.window.showInformationMessage(
                    `${icon} ${r.will_fail ? 'Likely to fail' : 'Likely to succeed'} (${Math.round(r.confidence * 100)}%) — ${r.reason}`
                );
            }
        }),

        vscode.commands.registerCommand('sage.fix', async () => {
            const result = await client.sendRequest('sage/fix', {});
            const r = result as any;
            if (r.ok && r.fix) {
                const action = await vscode.window.showInformationMessage(
                    `Fix: ${r.fix.fix_command}\n${r.fix.explanation}`,
                    'Copy to Terminal', 'Dismiss'
                );
                if (action === 'Copy to Terminal') {
                    const terminal = vscode.window.activeTerminal || vscode.window.createTerminal('SAGE');
                    terminal.sendText(r.fix.fix_command);
                    terminal.show();
                }
            } else {
                vscode.window.showInformationMessage('No fix available for last error.');
            }
        }),

        vscode.commands.registerCommand('sage.explain', async () => {
            const result = await client.sendRequest('sage/explain', {});
            const r = result as any;
            if (r.ok) {
                vscode.window.showInformationMessage(`${r.command}: ${r.summary}`);
            }
        }),

        vscode.commands.registerCommand('sage.session', async () => {
            const result = await client.sendRequest('sage/session', {});
            const r = result as any;
            if (r.ok) {
                const items = r.recent_commands.map((c: any) =>
                    `${c.exit_code === 0 ? '✅' : '❌'} ${c.command}`
                );
                vscode.window.showQuickPick(items, { title: 'SAGE Session History' });
            }
        })
    );
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) return undefined;
    return client.stop();
}
