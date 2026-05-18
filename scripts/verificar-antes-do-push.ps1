# Verifica se arquivos sensíveis estao prestes a ir para o Git.
# Uso: .\scripts\verificar-antes-do-push.ps1
# Retorna codigo 0 = seguro | 1 = bloquear push

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$bloqueados = @(
    ".env",
    ".env.local",
    "data",
    "data\config",
    "data\database.sqlite",
    "ollama_data\id_ed25519",
    "n8n-ia-workflow.json"
)

$padroesProibidos = @(
    '[a-zA-Z0-9._%+-]+@gmail\.com',
    '\+55\d{10,13}',
    '"encryptionKey"\s*:\s*"[A-Za-z0-9]{20,}"'
)

# Valores sensiveis do .env local (arquivo nao vai pro Git)
$chavesSensiveis = @(
    "EMAIL_ADMIN_ALERTA",
    "WHATSAPP_DEST_NUMBER",
    "GOOGLE_SHEETS_LOG_ID",
    "GCS_BUCKET_NAME",
    "GOOGLE_SHEETS_SHEET_NAME"
)
$envFile = Join-Path $root ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
        $partes = $_ -split '=', 2
        $chave = $partes[0].Trim()
        if ($chavesSensiveis -notcontains $chave) { return }
        $valor = $partes[1].Trim().Trim('"').Trim("'")
        if ($valor.Length -ge 4) {
            $padroesProibidos += [regex]::Escape($valor)
        }
    }
}

$erros = @()

if (-not (Test-Path ".git")) {
    Write-Host "[AVISO] Repositorio Git ainda nao inicializado. Rode: git init" -ForegroundColor Yellow
}

$gitFiles = @()
if (Test-Path ".git") {
    $gitFiles = @(git ls-files 2>$null)
    $staged = @(git diff --cached --name-only 2>$null)
    if ($staged) { $gitFiles += $staged }
    $gitFiles = $gitFiles | Select-Object -Unique
}

foreach ($rel in $bloqueados) {
    $norm = ($rel -replace '\\', '/').TrimEnd('/')
    $isDir = $norm -eq "data" -or $norm -eq "ollama_data"
    if ($isDir) {
        $tracked = $gitFiles | Where-Object { $_ -eq $norm -or $_ -like "$norm/*" }
    } else {
        $tracked = $gitFiles | Where-Object { $_ -eq $norm }
    }
    if ($tracked) {
        $erros += "ARQUIVO/PASTA SENSIVEL NO GIT: $rel"
    }
}

foreach ($f in $gitFiles) {
    if ($f -eq "n8n-ia-workflow.json") {
        $erros += "Use n8n-ia-workflow.example.json no Git, nao o JSON de producao"
    }
    if ($f -eq ".env.example" -or $f -eq "PUBLICAR-NO-GITHUB.md") { continue }
    $path = Join-Path $root $f
    if (-not (Test-Path $path) -or (Test-Path $path -PathType Container)) { continue }
    $content = Get-Content $path -Raw -ErrorAction SilentlyContinue
    if (-not $content) { continue }
    foreach ($p in $padroesProibidos) {
        if ($content -match $p) {
            $erros += "Possivel segredo em '$f' (padrao: $p)"
            break
        }
    }
}

if (Test-Path ".git") {
    $envTracked = git ls-files ".env" 2>$null
    if ($envTracked) { $erros += ".env esta versionado. Remova com: git rm --cached .env" }
}

Write-Host ""
Write-Host "=== Verificacao pre-push AGIL.AI ===" -ForegroundColor Cyan
Write-Host "Diretorio: $root"
Write-Host ""

if ($erros.Count -eq 0) {
    Write-Host "OK: Nenhum problema detectado para publicar no GitHub." -ForegroundColor Green
    Write-Host ""
    Write-Host "Lembrete:" -ForegroundColor Yellow
    Write-Host "  - Commit: n8n-ia-workflow.example.json (nao o .json de producao)"
    Write-Host "  - Configure .env local a partir de .env.example"
    Write-Host "  - Credenciais OAuth sao recriadas na UI do n8n apos o clone"
    exit 0
}

Write-Host "BLOQUEADO: Corrija antes do git push:" -ForegroundColor Red
foreach ($e in $erros) { Write-Host "  - $e" -ForegroundColor Red }
Write-Host ""
Write-Host "Veja PUBLICAR-NO-GITHUB.md para o passo a passo." -ForegroundColor Yellow
exit 1
