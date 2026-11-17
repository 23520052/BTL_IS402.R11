param(
    [string]$Server = 'sqlsrv-sales-gr03-tram01.database.windows.net',
    [string]$Database = 'salesdb',
    [string]$User = 'pbi_reader',
    [string]$RunId = 'integration-261113',
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '../evidence/local-check')
)
# TV4 only: SELECT/metadata queries. No writes, seed, DDL or permission changes.
$ErrorActionPreference = 'Stop'
if (-not $env:PBI_SQL_PASSWORD) { throw 'Set PBI_SQL_PASSWORD for this process or use a secure local prompt; never commit it.' }
$builder = New-Object System.Data.SqlClient.SqlConnectionStringBuilder
$builder['Data Source'] = "tcp:$Server,1433"
$builder['Initial Catalog'] = $Database
$builder['User ID'] = $User
$builder['Password'] = $env:PBI_SQL_PASSWORD
$builder['Encrypt'] = $true
$builder['TrustServerCertificate'] = $false
$builder['Connect Timeout'] = 20
$connection = New-Object System.Data.SqlClient.SqlConnection $builder.ConnectionString
$results = [ordered]@{ checked_at_utc = [DateTime]::UtcNow.ToString('o'); server = $Server; database = $Database; user = $User; selected_run = $RunId; status = 'not_connected' }
$queryLog = [System.Collections.Generic.List[object]]::new()
$results.operation = 'open_sql_connection'
function Read-Query([string]$Sql) {
    $results.operation = 'execute_sql_select'
    $results.active_sql = $Sql
    $entry = [pscustomobject]@{ started_at_utc=[DateTime]::UtcNow.ToString('o'); sql=$Sql; status='running'; rows=$null }
    $queryLog.Add($entry)
    $command = $connection.CreateCommand()
    $command.CommandTimeout = 30
    $command.CommandText = $Sql
    [void]$command.Parameters.AddWithValue('@run', $RunId)
    $reader = $null
    $rows = [System.Collections.Generic.List[object]]::new()
    try {
        $reader = $command.ExecuteReader()
        while ($reader.Read()) {
            $row = [ordered]@{}
            for ($i = 0; $i -lt $reader.FieldCount; $i++) {
                $value = $reader.GetValue($i)
                if ($value -is [DBNull]) { $value = $null }
                elseif ($value -is [DateTime]) { $value = $value.ToString('yyyy-MM-ddTHH:mm:ss.fffffff') + 'Z' }
                $row[$reader.GetName($i)] = $value
            }
            $rows.Add([pscustomobject]$row)
        }
        $entry.status = 'pass'
        $entry.rows = $rows.Count
    } finally { if ($reader) { $reader.Dispose() }; $command.Dispose() }
    return ,($rows.ToArray())
}
try {
    $connection.Open()
    $results.status = 'connected'
    $results.permissions = Read-Query "SELECT USER_NAME() AS database_user, source_table, HAS_PERMS_BY_NAME(source_table,'OBJECT','SELECT') AS can_select, HAS_PERMS_BY_NAME(source_table,'OBJECT','INSERT') AS can_insert, HAS_PERMS_BY_NAME(source_table,'OBJECT','UPDATE') AS can_update, HAS_PERMS_BY_NAME(source_table,'OBJECT','DELETE') AS can_delete FROM (VALUES ('dbo.event_metrics_30s'),('dbo.brand_sales_1m')) AS sources(source_table)"
    $results.schema = Read-Query "SELECT TABLE_NAME,COLUMN_NAME,DATA_TYPE,IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME IN ('event_metrics_30s','brand_sales_1m') ORDER BY TABLE_NAME,ORDINAL_POSITION"
    $results.runs = Read-Query 'SELECT run_id,COUNT_BIG(*) AS aggregate_rows,SUM(event_count) AS total_events,MIN(window_end) AS first_window_utc,MAX(window_end) AS last_window_utc FROM dbo.event_metrics_30s GROUP BY run_id ORDER BY run_id'
    $results.events_by_type = Read-Query 'SELECT event_type,SUM(event_count) AS event_count,SUM(revenue) AS purchase_value FROM dbo.event_metrics_30s WHERE run_id=@run GROUP BY event_type ORDER BY event_type'
    $results.kpis = Read-Query "SELECT COALESCE(SUM(event_count),0) AS total_events,COALESCE(SUM(CASE WHEN event_type='purchase' THEN event_count ELSE 0 END),0) AS purchase_events,COALESCE(SUM(CASE WHEN event_type='view' THEN event_count ELSE 0 END),0) AS view_events,COALESCE(SUM(CASE WHEN event_type='cart' THEN event_count ELSE 0 END),0) AS cart_events,COALESCE(SUM(CASE WHEN event_type='remove_from_cart' THEN event_count ELSE 0 END),0) AS remove_events,COALESCE(SUM(CASE WHEN event_type='purchase' THEN revenue ELSE 0 END),0) AS purchase_value,1.0*SUM(CASE WHEN event_type='purchase' THEN event_count ELSE 0 END)/NULLIF(SUM(CASE WHEN event_type='view' THEN event_count ELSE 0 END),0) AS purchase_to_view_ratio FROM dbo.event_metrics_30s WHERE run_id=@run"
    $results.brands = Read-Query 'SELECT brand,SUM(purchase_events) AS purchase_events,SUM(revenue) AS purchase_value FROM dbo.brand_sales_1m WHERE run_id=@run GROUP BY brand ORDER BY purchase_value DESC,brand'
    $results.integrity = Read-Query "SELECT 'events_duplicate_keys' AS check_name,COUNT_BIG(*) AS issues FROM (SELECT window_end,run_id,event_type FROM dbo.event_metrics_30s WHERE run_id=@run GROUP BY window_end,run_id,event_type HAVING COUNT_BIG(*)>1) d UNION ALL SELECT 'brands_duplicate_keys',COUNT_BIG(*) FROM (SELECT window_end,run_id,brand FROM dbo.brand_sales_1m WHERE run_id=@run GROUP BY window_end,run_id,brand HAVING COUNT_BIG(*)>1) d UNION ALL SELECT 'events_invalid_values',COUNT_BIG(*) FROM dbo.event_metrics_30s WHERE run_id=@run AND (event_count<0 OR revenue<0 OR event_type NOT IN ('view','cart','remove_from_cart','purchase') OR (event_type<>'purchase' AND ABS(revenue)>0.01)) UNION ALL SELECT 'brands_invalid_values',COUNT_BIG(*) FROM dbo.brand_sales_1m WHERE run_id=@run AND (purchase_events<0 OR revenue<0 OR brand='')"
    $results.event_windows = Read-Query 'SELECT window_end,run_id,event_type,event_count,revenue FROM dbo.event_metrics_30s WHERE run_id=@run ORDER BY window_end,event_type'
    $results.brand_windows = Read-Query 'SELECT window_end,run_id,brand,purchase_events,revenue FROM dbo.brand_sales_1m WHERE run_id=@run ORDER BY window_end,brand'
    $results.mock_kpis = Read-Query "SELECT SUM(event_count) AS total_events,SUM(CASE WHEN event_type='purchase' THEN event_count ELSE 0 END) AS purchase_events,SUM(CASE WHEN event_type='view' THEN event_count ELSE 0 END) AS view_events,SUM(CASE WHEN event_type='purchase' THEN revenue ELSE 0 END) AS purchase_value FROM dbo.event_metrics_30s WHERE run_id='mock-seed'"
    $results.mock_brand_kpis = Read-Query "SELECT SUM(purchase_events) AS purchase_events,SUM(revenue) AS purchase_value FROM dbo.brand_sales_1m WHERE run_id='mock-seed'"
    $results.operation = 'validate_kpi_results'
    if (@($results.permissions).Count -ne 2 -or @($results.permissions | Where-Object { $_.can_select -ne 1 -or $_.can_insert -ne 0 -or $_.can_update -ne 0 -or $_.can_delete -ne 0 }).Count -gt 0) {
        throw 'BI credentials must have SELECT and no INSERT/UPDATE/DELETE on both fact tables.'
    }
    $brandCount = [long]($results.brands | Measure-Object purchase_events -Sum).Sum
    $brandValue = [double]($results.brands | Measure-Object purchase_value -Sum).Sum
    $issues = ($results.integrity | Measure-Object issues -Sum).Sum
    if ($results.kpis.Count -eq 0 -or $results.kpis[0].total_events -le 0) { throw 'Selected run has no event data.' }
    $crossTableMismatch = $RunId -ne 'mock-seed' -and ($brandCount -ne $results.kpis[0].purchase_events -or [Math]::Abs($brandValue-$results.kpis[0].purchase_value) -gt 0.01)
    if ($crossTableMismatch -or $issues -gt 0) {
        $results.status = 'validation_failed'
    } else { $results.status = 'pass' }
} catch {
    $results.error = $_.Exception.Message.Replace($env:PBI_SQL_PASSWORD, '[REDACTED]')
    $results.failed_operation = $results.operation
    if ($results.operation -eq 'execute_sql_select') {
        $results.failed_sql = $results.active_sql
        if ($queryLog.Count -gt 0) { $queryLog[$queryLog.Count-1].status = 'failed' }
    }
    $sqlException = $_.Exception
    while ($sqlException -and -not ($sqlException -is [System.Data.SqlClient.SqlException])) { $sqlException = $sqlException.InnerException }
    if ($sqlException) {
        $results.sql_errors = @($sqlException.Errors | ForEach-Object { [pscustomobject]@{ number=$_.Number; state=$_.State; severity=$_.Class; message=$_.Message } })
    }
    if ($results.error -match "IP address '([^']+)'") { $results.rejected_client_ip = $Matches[1] }
    if ($results.error -match 'is not allowed to access the server') { $results.failure_category = 'azure_sql_ip_firewall' }
    if ($results.status -eq 'connected') { $results.status = 'query_failed' }
} finally {
    $results.query_log = $queryLog.ToArray()
    $connection.Dispose()
    [void](New-Item -ItemType Directory -Path $OutputDirectory -Force)
    $json = $results | ConvertTo-Json -Depth 15
    [System.IO.File]::WriteAllText((Join-Path ([IO.Path]::GetFullPath($OutputDirectory)) 'sql_validation.json'), $json, [Text.UTF8Encoding]::new($false))
}
Write-Output "SQL QA status: $($results.status)"
if ($results.kpis) { $results.kpis | Format-Table -AutoSize }
if ($results.error) { Write-Output $results.error }
if ($results.status -ne 'pass') { exit 1 }
