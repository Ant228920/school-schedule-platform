# Lab 8: soak / spike run. Usage (from project root, venv active):
#   .\run_soak.ps1 -Name soak_main -Mode soak -Users 250 -Duration 1h
#   .\run_soak.ps1 -Name spike -Mode spike
param(
    [Parameter(Mandatory = $true)][string]$Name,
    [ValidateSet("soak", "spike")][string]$Mode = "soak",
    [int]$Users = 250,
    [string]$Duration = "1h",
    [string]$RedisUrl = "redis://localhost:6379/0"
)

$root = (Get-Location).Path
$out = Join-Path $root "loadtest\results\$Name"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$db = "school-schedule-lab7"

function Get-EnvValue($file, $key, $default) {
    if (Test-Path $file) {
        $line = Get-Content $file | Where-Object { $_ -match "^\s*$key\s*=" } | Select-Object -First 1
        if ($line) { return ($line -split "=", 2)[1].Trim().Trim('"').Trim("'") }
    }
    return $default
}

$envFile = Join-Path $root ".env"
$dbUser = Get-EnvValue $envFile "DB_USER" "postgres"
$dbPass = Get-EnvValue $envFile "DB_PASSWORD" ""
$dbHost = Get-EnvValue $envFile "DB_HOST" "localhost"
$dbPort = Get-EnvValue $envFile "DB_PORT" "5432"

Write-Host "== 1/6 restore database $db"
$env:PGPASSWORD = $dbPass
dropdb -h $dbHost -p $dbPort -U $dbUser --if-exists --force $db
createdb -h $dbHost -p $dbPort -U $dbUser $db
pg_restore -h $dbHost -p $dbPort -U $dbUser -d $db --no-owner --no-privileges (Join-Path $root "lab7_data.dump")

Write-Host "== 2/6 reset redis"
if ($RedisUrl) {
    docker exec lab7-redis redis-cli flushall | Out-Null
    docker exec lab7-redis redis-cli config resetstat | Out-Null
}

# Settings for the run only (not changed in the repo):
# pool 40+10 >= 40 worker threads; token lifetime longer than the test (default is 60 min).
$env:DB_NAME = $db
$env:REDIS_URL = $RedisUrl
$env:DB_POOL_SIZE = "40"
$env:DB_MAX_OVERFLOW = "10"
$env:TOKEN_EXPIRE_MINUTES = "600"

$app = $null
$mon = $null
$probe = $null
try {
    Write-Host "== 3/6 start application"
    $app = Start-Process python -ArgumentList "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning" `
        -PassThru -NoNewWindow -RedirectStandardOutput "$out\app.log" -RedirectStandardError "$out\app_err.log"
    $ready = $false
    for ($i = 0; $i -lt 60; $i++) {
        try {
            Invoke-WebRequest -Uri "http://127.0.0.1:8000/login" -UseBasicParsing -TimeoutSec 2 | Out-Null
            $ready = $true
            break
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $ready) { throw "application did not start, see $out\app_err.log" }
    for ($i = 0; $i -lt 20; $i++) {
        Invoke-WebRequest -Uri "http://127.0.0.1:8000/login" -UseBasicParsing | Out-Null
    }

    Write-Host "== 4/6 start monitor and probe"
    $mon = Start-Process python -ArgumentList "loadtest\monitor.py", "--out", "$out\resources.csv" -PassThru -NoNewWindow
    $probe = Start-Process python -ArgumentList "loadtest\soak_probe.py", "--out", "$out\probe.csv", "--interval", "10" -PassThru -NoNewWindow
    Start-Sleep -Seconds 3

    Write-Host "== 5/6 locust ($Mode)"
    $env:SOAK_WINDOWS_CSV = "$out\soak_windows.csv"
    if ($Mode -eq "soak") {
        $env:SOAK_INTERVAL = "10"
        python -m locust -f "loadtest/locustfile.py,loadtest/soak_stats.py" --headless --host http://127.0.0.1:8000 `
            -u $Users -r 5 -t $Duration --csv "$out/locust" --html "$out/locust_report.html"
    } else {
        $env:SOAK_INTERVAL = "5"
        python -m locust -f "loadtest/locustfile.py,loadtest/spike_shape.py,loadtest/soak_stats.py" --headless --host http://127.0.0.1:8000 `
            --csv "$out/locust" --html "$out/locust_report.html"
    }

    if ($RedisUrl) {
        docker exec lab7-redis redis-cli info stats | Select-String "keyspace" | Out-File "$out\redis_stats.txt" -Encoding ascii
        docker exec lab7-redis redis-cli info memory | Select-String "used_memory_human" | Out-File "$out\redis_stats.txt" -Append -Encoding ascii
    }
}
finally {
    Write-Host "== 6/6 stop processes"
    foreach ($p in @($probe, $mon, $app)) {
        if ($p) { taskkill /PID $p.Id /T /F | Out-Null }
    }
    Write-Host "DONE $Name"
}
