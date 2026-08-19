# Windows-native Yahoo chart fetch — no Python yfinance
$ErrorActionPreference = "Continue"
$tickers = @("CRAK","LITE","CAT","GEV","MU","RKLB","TSLA","NVDA","ETN","ZS","BE","DELL","MRVL")
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$out = Join-Path $repoRoot "data\dad_watchlist_live.csv"
$rows = New-Object System.Collections.Generic.List[string]
$rows.Add("ticker,return_score,risk_score,name") | Out-Null
Write-Host "[fetch] PowerShell Yahoo chart, 15s timeout each"
foreach ($t in $tickers) {
  Write-Host "  fetching $t..."
  try {
    $url = "https://query1.finance.yahoo.com/v8/finance/chart/${t}?range=6mo&interval=1d"
    $resp = Invoke-WebRequest -Uri $url -TimeoutSec 15 -UseBasicParsing -Headers @{ "User-Agent" = "Mozilla/5.0" }
    $j = $resp.Content | ConvertFrom-Json
    $closes = @($j.chart.result[0].indicators.quote[0].close | Where-Object { $_ -ne $null })
    if ($closes.Count -lt 10) { Write-Host "  $t FAIL short"; continue }
    $n = [Math]::Min(63, $closes.Count)
    $w = $closes[($closes.Count - $n)..($closes.Count - 1)]
    $ret = ([double]$w[-1] / [double]$w[0]) - 1.0
    $rets = @()
    for ($i = 1; $i -lt $w.Count; $i++) { $rets += (([double]$w[$i] / [double]$w[$i-1]) - 1.0) }
    $mean = ($rets | Measure-Object -Average).Average
    $var = 0.0
    foreach ($r in $rets) { $var += ($r - $mean) * ($r - $mean) }
    $std = [Math]::Sqrt($var / [Math]::Max(1, $rets.Count - 1))
    $vol = $std * [Math]::Sqrt(252)
    $rows.Add(("{0},{1:G6},{2:G6},{0}" -f $t, $ret, $vol)) | Out-Null
    Write-Host ("  {0}: ok ret={1:N4} vol={2:N4}" -f $t, $ret, $vol)
  } catch {
    Write-Host "  $t FAIL $($_.Exception.Message)"
  }
}
$dir = Split-Path $out -Parent
if (!(Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
$rows | Set-Content -Path $out -Encoding utf8
Write-Host "[fetch] wrote $out ($($rows.Count - 1) rows)"
