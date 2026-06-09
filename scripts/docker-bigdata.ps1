param(
    [ValidateSet("up-all", "down", "restart", "status", "logs", "build", "python", "beeline")]
    [string]$Action = "status"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Invoke-Compose {
    param([string[]]$ComposeArgs)

    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "Docker CLI not found. Install/start Docker Desktop first."
    }

    & docker compose @ComposeArgs
}

switch ($Action) {
    "up-all" {
        & (Join-Path $PSScriptRoot "prepare-docker-bigdata.ps1")
        Invoke-Compose @("--profile", "hadoop", "--profile", "hive", "--profile", "spark", "--profile", "tools", "up", "-d", "--no-build")
    }
    "down" {
        Invoke-Compose @("--profile", "hadoop", "--profile", "hive", "--profile", "spark", "--profile", "tools", "down")
    }
    "restart" {
        Invoke-Compose @("--profile", "hadoop", "--profile", "hive", "--profile", "spark", "--profile", "tools", "restart")
    }
    "status" {
        Invoke-Compose @("--profile", "hadoop", "--profile", "hive", "--profile", "spark", "--profile", "tools", "ps")
    }
    "logs" {
        Invoke-Compose @("--profile", "hadoop", "--profile", "hive", "--profile", "spark", "--profile", "tools", "logs", "--tail", "120", "-f")
    }
    "build" {
        & (Join-Path $PSScriptRoot "prepare-docker-bigdata.ps1")
        Invoke-Compose @("--profile", "hadoop", "--profile", "hive", "--profile", "spark", "--profile", "tools", "build")
    }
    "python" {
        Invoke-Compose @("exec", "python", "bash")
    }
    "beeline" {
        Invoke-Compose @("exec", "hiveserver2", "beeline", "-u", "jdbc:hive2://localhost:10000", "-n", "root")
    }
}
