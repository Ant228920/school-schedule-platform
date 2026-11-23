param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][ValidateSet("baseline", "step")][string]$Mode,
    [Parameter(Mandatory = $true)][string]$AppDir,
    [string]$RedisUrl = ""
)

$repo = (Get-Location).Path
$appDirFull = (Resolve-Path $AppDir).Path
$out = Join-Path $repo "loadtest\results\$Name"
$dbName = "school-schedule-lab7"
New-Item -ItemType Directory -Force $out | Out-Null

# 1. identical database state for every run
dropdb -U postgres -h localhost --if-exists --force $dbName
createdb -U postgres -h localhost $dbName
pg_restore -U postgres -h localhost -d $dbName (Join-Path $repo "lab7_data.dump")

# 2. clean cache
if ($RedisUrl) {
    docker exec lab7-redis redis-cli flushall | Out-Null
    docker exec lab7-redis redis-cli config resetstat | Out-Null
}

# 3. application: one uvicorn process, as in lab 4
$env:DB_NAME = $dbName
$env:REDIS_URL = $RedisUrl
$app = Start-Process python -ArgumentList "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "warning" -WorkingDirectory $appDirFull -PassThru -NoNewWindow
for ($i = 0; $i -lt 60; $i++) {
    try { Invoke-WebRequest http://127.0.0.1:8000/login -UseBasicParsing | Out-Null; break } catch { Start-Sleep -Milliseconds 500 }
}
for ($i = 0; $i -lt 20; $i++) { try { Invoke-WebRequest http://127.0.0.1:8000/login -UseBasicParsing | Out-Null } catch {} }

# 4. resource monitor + load test
$mon = Start-Process python -ArgumentList "loadtest\monitor.py", "--out", "$out\resources.csv" -PassThru -NoNewWindow
if ($Mode -eq "step") {
    locust -f "loadtest/locustfile.py,loadtest/step_shape.py" --headless --host http://127.0.0.1:8000 --csv "$out/locust" --html "$out/locust_report.html"
}
else {
    locust -f loadtest/locustfile.py --headless --host http://127.0.0.1:8000 -u 50 -r 2 -t 3m --csv "$out/locust" --html "$out/locust_report.html"
}

# 5. stop everything (with child processes)
if ($RedisUrl) {
    docker exec lab7-redis redis-cli info stats | Select-String "keyspace" | Tee-Object -FilePath "$out\redis_stats.txt"
}
taskkill /PID $mon.Id /T /F | Out-Null
taskkill /PID $app.Id /T /F | Out-Null
Start-Sleep -Seconds 3
Write-Host "DONE $Name"
