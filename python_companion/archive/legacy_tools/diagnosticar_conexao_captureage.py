"""Inventário local de processos/portas, sem conectar-se ao jogo ou ao CaptureAge."""
import json
import os
import subprocess
from pathlib import Path

PS_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$apps = @(Get-Process | Where-Object { $_.ProcessName -match '^(AoE2DE.*|CaptureAge)$' })
$appIds = @($apps | ForEach-Object { $_.Id })
$processes = @($apps | ForEach-Object {
    [pscustomobject]@{ Name = $_.ProcessName; PID = $_.Id }
})
$listeners = @()
$loopback = @()
$queryError = $null
try {
    $connections = @(Get-NetTCPConnection -ErrorAction Stop | Where-Object { $appIds -contains $_.OwningProcess })
    $listeners = @($connections | Where-Object { $_.State -eq 'Listen' } | ForEach-Object {
        [pscustomobject]@{ PID = $_.OwningProcess; Address = $_.LocalAddress; Port = $_.LocalPort }
    })
    $loopback = @($connections | Where-Object {
        $_.State -eq 'Established' -and
        $_.RemoteAddress -in @('127.0.0.1', '::1', '::ffff:127.0.0.1')
    } | ForEach-Object {
        [pscustomobject]@{ PID = $_.OwningProcess; LocalPort = $_.LocalPort; RemotePort = $_.RemotePort }
    })
} catch {
    $queryError = $_.Exception.GetType().FullName
}
[pscustomobject]@{
    SchemaVersion = 1
    Processes = $processes
    TCPListeners = $listeners
    EstablishedLoopbackConnections = $loopback
    SocketQueryError = $queryError
} | ConvertTo-Json -Depth 5 -Compress
'''


def main():
    if os.name != 'nt':
        raise RuntimeError('Execute este diagnóstico no Windows onde o AoE2 DE e o CaptureAge estão abertos.')
    result = subprocess.run(
        ['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', PS_SCRIPT],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', errors='replace',
        timeout=45, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError('O PowerShell não conseguiu consultar os processos/portas. Código: ' + str(result.returncode))
    data = json.loads(result.stdout.lstrip('\ufeff').strip())
    data['DiagnosticOnly'] = True
    data['GameServiceQueried'] = False
    data['Instructions'] = 'Gerado com replay em reprodução; inventário não confirma protocolo gRPC nem contagens de unidades.'
    path = Path(__file__).resolve().parent / 'diagnostico_conexao_captureage.json'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Diagnóstico salvo em:', path.name)
    print('Processos encontrados:', len(data.get('Processes', [])))
    print('Portas em escuta:', len(data.get('TCPListeners', [])))
    if data.get('SocketQueryError'):
        print('A consulta de portas não foi concluída. O tipo de erro está registrado no relatório.')
    print('Envie diagnostico_conexao_captureage.json. Não é necessário reenviar main.log.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print('ERRO:', error)
        raise SystemExit(1)
