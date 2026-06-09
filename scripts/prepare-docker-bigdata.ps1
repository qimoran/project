param(
    [string]$PackageDir = "D:\bigdatashixun\安装包",
    [string]$DataRoot = "D:\docker\bigdata\data"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$assetDir = Join-Path $repoRoot "docker\build-context\assets"
$envExample = Join-Path $repoRoot ".env.example"
$envFile = Join-Path $repoRoot ".env"

function Get-Sha1Hex {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Get-Command Get-FileHash -ErrorAction SilentlyContinue) {
        return (Get-FileHash -LiteralPath $Path -Algorithm SHA1).Hash.ToLowerInvariant()
    }

    $sha1 = [System.Security.Cryptography.SHA1]::Create()
    try {
        $stream = [System.IO.File]::OpenRead($Path)
        try {
            $hash = $sha1.ComputeHash($stream)
            return ([System.BitConverter]::ToString($hash)).Replace("-", "").ToLowerInvariant()
        } finally {
            $stream.Dispose()
        }
    } finally {
        $sha1.Dispose()
    }
}

New-Item -ItemType Directory -Force -Path $assetDir | Out-Null
New-Item -ItemType Directory -Force -Path $DataRoot | Out-Null

$dataDirs = @(
    "mysql",
    "redis",
    "hdfs\namenode",
    "hdfs\datanode",
    "hadoop-tmp",
    "spark-events"
)

foreach ($dir in $dataDirs) {
    New-Item -ItemType Directory -Force -Path (Join-Path $DataRoot $dir) | Out-Null
}

$assets = @(
    @{ Source = "hadoop-3.3.6.tar.gz"; Target = "hadoop-3.3.6.tar.gz" },
    @{ Source = "hive-4.0.1-bin.tar.gz"; Target = "hive-4.0.1-bin.tar.gz" },
    @{ Source = "spark-3.5.1-bin-hadoop3.tgz"; Target = "spark-3.5.1-bin-hadoop3.tgz" }
)

foreach ($asset in $assets) {
    $src = Join-Path $PackageDir $asset.Source
    $dst = Join-Path $assetDir $asset.Target

    if (-not (Test-Path -LiteralPath $src)) {
        throw "Missing package: $src"
    }

    if (Test-Path -LiteralPath $dst) {
        continue
    }

    try {
        New-Item -ItemType HardLink -Path $dst -Target $src | Out-Null
        Write-Host "Linked $dst -> $src"
    } catch {
        Write-Warning "Hardlink failed for $($asset.Source); copying instead. $($_.Exception.Message)"
        Copy-Item -LiteralPath $src -Destination $dst -Force
    }
}

$mysqlConnector = Join-Path $assetDir "mysql-connector-j-8.0.33.jar"
$mysqlConnectorSha1 = Join-Path $assetDir "mysql-connector-j-8.0.33.jar.sha1"
if (-not (Test-Path -LiteralPath $mysqlConnector)) {
    $connectorUrl = "https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/8.0.33/mysql-connector-j-8.0.33.jar"
    Write-Host "Downloading MySQL Connector/J 8.0.33..."
    curl.exe -L --retry 5 --retry-delay 3 -x http://127.0.0.1:7897 -o $mysqlConnector $connectorUrl
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to download MySQL Connector/J"
    }
}
if (-not (Test-Path -LiteralPath $mysqlConnectorSha1)) {
    curl.exe -L --retry 5 --retry-delay 3 -x http://127.0.0.1:7897 -o $mysqlConnectorSha1 "https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/8.0.33/mysql-connector-j-8.0.33.jar.sha1"
}
$actualConnectorSha1 = Get-Sha1Hex -Path $mysqlConnector
$expectedConnectorSha1 = (Get-Content -LiteralPath $mysqlConnectorSha1 -Raw).Trim().Split()[0].ToLowerInvariant()
if ($actualConnectorSha1 -ne $expectedConnectorSha1) {
    throw "MySQL Connector/J SHA1 mismatch"
}

if (-not (Test-Path -LiteralPath $envFile)) {
    Copy-Item -LiteralPath $envExample -Destination $envFile
    Write-Host "Created .env from .env.example"
}

Write-Host "Docker bigdata workspace prepared."
Write-Host "Data root: $DataRoot"
Write-Host "Assets:    $assetDir"
