param(
    [Parameter(Mandatory=$true)][int]$Port,
    [string]$RunId = 'integration-261113',
    [ValidateSet('DirectQuery','Snapshot')][string]$ModelKind = 'DirectQuery',
    [string]$DesktopBin = 'C:\Program Files\Microsoft Power BI Desktop\bin',
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '../evidence/local-check')
)
# Read-only ADOMD queries against the open Desktop semantic model. Its existing
# DirectQuery credentials query Azure SQL; no password is extracted or stored.
$ErrorActionPreference = 'Stop'
[void][Reflection.Assembly]::LoadFrom((Join-Path $DesktopBin 'Microsoft.PowerBI.AdomdClient.dll'))
$connection = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection "Data Source=localhost:$Port"
$runLiteral = '"' + $RunId.Replace('"','""') + '"'
$queryLog = [System.Collections.Generic.List[object]]::new()
function Read-Dax([string]$Dax) {
    $results.operation = 'execute_dax_in_desktop_model'
    $results.active_dax = $Dax
    $entry = [pscustomobject]@{ started_at_utc=[DateTime]::UtcNow.ToString('o'); dax=$Dax; status='running'; rows=$null }
    $queryLog.Add($entry)
    $command = $connection.CreateCommand()
    $command.CommandText = $Dax
    $command.CommandTimeout = 60
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
                $row[$reader.GetName($i).Trim('[',']')] = $value
            }
            $rows.Add([pscustomobject]$row)
        }
        $entry.status = 'pass'
        $entry.rows = $rows.Count
    } finally { if ($reader) { $reader.Dispose() }; $command.Dispose() }
    return ,($rows.ToArray())
}
$results = [ordered]@{ checked_at_utc=[DateTime]::UtcNow.ToString('o'); method="ADOMD / open Power BI Desktop / $ModelKind"; local_port=$Port; selected_run=$RunId; status='not_connected'; operation='open_local_desktop_engine' }
try {
    $connection.Open()
    $results.runs = Read-Dax 'EVALUATE SUMMARIZECOLUMNS(DimRun[run_id],"Events",[Total Events])'
    $results.kpis = Read-Dax "EVALUATE CALCULATETABLE(ROW(`"total_events`",[Total Events],`"view_events`",[View Events],`"cart_events`",[Cart Events],`"remove_events`",[Remove Events],`"purchase_events`",[Purchase Events],`"purchase_value`",[Purchase Value],`"purchase_to_view_ratio`",[Purchase To View Ratio],`"brand_purchase_events`",[Brand Purchase Events],`"brand_purchase_value`",[Brand Purchase Value]),TREATAS({$runLiteral},DimRun[run_id]))"
    $results.events = Read-Dax "EVALUATE CALCULATETABLE(SELECTCOLUMNS(event_metrics_30s,`"window_end`",event_metrics_30s[window_end],`"run_id`",event_metrics_30s[run_id],`"event_type`",event_metrics_30s[event_type],`"event_count`",event_metrics_30s[event_count],`"revenue`",event_metrics_30s[revenue]),TREATAS({$runLiteral},DimRun[run_id]))"
    $results.brands = Read-Dax "EVALUATE SUMMARIZECOLUMNS(brand_sales_1m[brand],TREATAS({$runLiteral},DimRun[run_id]),`"purchase_events`",[Brand Purchase Events],`"purchase_value`",[Brand Purchase Value],`"share`",[Brand Value Share])"
    $results.brand_windows = Read-Dax "EVALUATE CALCULATETABLE(SELECTCOLUMNS(brand_sales_1m,`"window_end`",brand_sales_1m[window_end],`"run_id`",brand_sales_1m[run_id],`"brand`",brand_sales_1m[brand],`"purchase_events`",brand_sales_1m[purchase_events],`"revenue`",brand_sales_1m[revenue]),TREATAS({$runLiteral},DimRun[run_id]))"
    $results.mock_kpis = Read-Dax 'EVALUATE CALCULATETABLE(ROW("total_events",[Total Events],"view_events",[View Events],"purchase_events",[Purchase Events],"purchase_value",[Purchase Value],"brand_purchase_events",[Brand Purchase Events],"brand_purchase_value",[Brand Purchase Value]),TREATAS({"mock-seed"},DimRun[run_id]))'
    $results.event_filter_test = Read-Dax "EVALUATE CALCULATETABLE(ROW(`"total_events`",[Total Events],`"purchase_events`",[Purchase Events]),TREATAS({$runLiteral},DimRun[run_id]),TREATAS({`"view`"},DimEvent[event_type]))"
    $results.empty_test = Read-Dax 'EVALUATE CALCULATETABLE(ROW("total_events",[Total Events],"purchase_value",[Purchase Value],"ratio",[Purchase To View Ratio],"last_window",[Last Window UTC]),TREATAS({"__tv4_nonexistent_run__"},DimRun[run_id]))'
    $results.operation = 'validate_kpi_results'
    $k = $results.kpis[0]
    if ($RunId -eq 'integration-261113' -and ($k.total_events -ne 10000 -or $k.purchase_events -ne 118 -or [Math]::Abs($k.purchase_value-35757.22) -gt 0.01)) { throw 'Integration run does not match the saved 10,000-event handoff.' }
    if ($k.total_events -le 0) { throw 'Selected run has no event data.' }
    if ($RunId -ne 'mock-seed' -and ($k.purchase_events -ne $k.brand_purchase_events -or [Math]::Abs($k.purchase_value-$k.brand_purchase_value) -gt 0.01)) { throw 'Selected run cross-table KPI reconciliation failed.' }
    $eventDuplicates = @($results.events | Group-Object window_end,run_id,event_type | Where-Object Count -gt 1)
    $brandDuplicates = @($results.brand_windows | Group-Object window_end,run_id,brand | Where-Object Count -gt 1)
    $invalidEvents = @($results.events | Where-Object { $_.event_count -lt 0 -or $_.revenue -lt 0 -or $_.event_type -notin @('view','cart','remove_from_cart','purchase') -or ($_.event_type -ne 'purchase' -and [Math]::Abs($_.revenue) -gt 0.01) })
    $invalidBrands = @($results.brand_windows | Where-Object { $_.purchase_events -lt 0 -or $_.revenue -lt 0 -or [string]::IsNullOrWhiteSpace($_.brand) })
    $results.integrity = [ordered]@{event_duplicate_grains=$eventDuplicates.Count; brand_duplicate_grains=$brandDuplicates.Count; invalid_event_rows=$invalidEvents.Count; invalid_brand_rows=$invalidBrands.Count}
    if ($eventDuplicates.Count -or $brandDuplicates.Count -or $invalidEvents.Count -or $invalidBrands.Count) { throw 'Aggregate grain or value integrity failed.' }
    if ($results.event_filter_test[0].total_events -ne $k.view_events -or $results.event_filter_test[0].purchase_events -ne $k.purchase_events) { throw 'Event slicer semantics failed.' }
    if ($results.empty_test[0].total_events -ne 0 -or $results.empty_test[0].purchase_value -ne 0 -or $null -ne $results.empty_test[0].ratio -or $null -ne $results.empty_test[0].last_window) { throw 'Empty-run behavior failed.' }
    $results.status = 'pass'
} catch {
    $results.status='failed'
    $results.error=$_.Exception.Message
    $results.failed_operation = $results.operation
    if ($results.operation -eq 'execute_dax_in_desktop_model') { $results.failed_dax = $results.active_dax }
    if ($queryLog.Count -gt 0 -and $queryLog[$queryLog.Count-1].status -eq 'running') { $queryLog[$queryLog.Count-1].status='failed' }
    if ($results.error -match "IP address '([^']+)'") { $results.rejected_client_ip=$Matches[1] }
    if ($results.error -match 'is not allowed to access the server') { $results.failure_category='azure_sql_ip_firewall_from_directquery_source' }
}
finally {
    $results.query_log=$queryLog.ToArray()
    $connection.Dispose()
    [void](New-Item -ItemType Directory -Path $OutputDirectory -Force)
    [IO.File]::WriteAllText((Join-Path ([IO.Path]::GetFullPath($OutputDirectory)) 'model_validation.json'),($results|ConvertTo-Json -Depth 15),[Text.UTF8Encoding]::new($false))
}
Write-Output "Desktop model QA status: $($results.status)"
if ($results.kpis) { $results.kpis | Format-List }
if ($results.error) { Write-Output $results.error }
if ($results.status -ne 'pass') { exit 1 }
