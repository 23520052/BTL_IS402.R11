param(
    [Parameter(Mandatory=$true)][int]$Port,
    [string]$RunId = 'integration-261117',
    [string]$DesktopBin = 'C:\Program Files\Microsoft Power BI Desktop\bin',
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '../evidence/local-check')
)
# Roles= applies semantic-model security, unlike simulating RLS with a WHERE filter.
$ErrorActionPreference = 'Stop'
[void][Reflection.Assembly]::LoadFrom((Join-Path $DesktopBin 'Microsoft.PowerBI.AdomdClient.dll'))
$result = [ordered]@{checked_at_utc=[DateTime]::UtcNow.ToString('o'); run_id=$RunId; method='ADOMD Roles connection property / Desktop'; status='running'; tests=@()}
$run = '"' + $RunId.Replace('"','""') + '"'
function Query([string]$Role, [string]$Dax) {
    $connection = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection "Data Source=localhost:$Port;Roles=$Role"
    try {
        $connection.Open()
        $command = $connection.CreateCommand()
        $command.CommandText = $Dax
        $command.CommandTimeout = 60
        $reader = $command.ExecuteReader()
        $rows = [System.Collections.Generic.List[object]]::new()
        while ($reader.Read()) {
            $row = [ordered]@{}
            for ($i=0; $i -lt $reader.FieldCount; $i++) {
                $value=$reader.GetValue($i)
                if ($value -is [DBNull]) { $value=$null }
                $row[$reader.GetName($i).Trim('[',']')]=$value
            }
            $rows.Add([pscustomobject]$row)
        }
        return ,$rows.ToArray()
    } finally {if ($reader) {$reader.Dispose()}; if ($command) {$command.Dispose()}; $connection.Dispose()}
}
function Check([string]$Name, [bool]$Condition, $Actual) {
    $result.tests += [pscustomobject]@{name=$Name; pass=$Condition; actual=$Actual}
    if (!$Condition) { throw "RLS assertion failed: $Name" }
}
try {
    $kpi = "EVALUATE CALCULATETABLE(ROW(`"events`",[Total Events],`"purchase`",[Purchase Events],`"value`",[Purchase Value],`"brand_events`",[Brand Purchase Events],`"brand_value`",[Brand Purchase Value]),TREATAS({$run},DimRun[run_id]))"
    $manager = (Query 'Manager' $kpi)[0]
    Check 'Manager can read both facts' ($manager.events -gt 0 -and $manager.brand_events -eq $manager.purchase -and [Math]::Abs($manager.brand_value-$manager.value) -le 0.01) $manager
    $baseline = (Query 'Manager' "EVALUATE CALCULATETABLE(ROW(`"count`",[Brand Purchase Events],`"value`",[Brand Purchase Value]),TREATAS({$run},DimRun[run_id]),TREATAS({`"apple`"},brand_sales_1m[brand]))")[0]
    Check 'Allowed brand fixture exists' ($baseline.count -gt 0) $baseline
    $analyst = (Query 'Brand Analyst' $kpi)[0]
    Check 'Analyst sees only allowed-brand totals' ($analyst.brand_events -eq $baseline.count -and [Math]::Abs($analyst.brand_value-$baseline.value) -le 0.01) $analyst
    Check 'Brandless event aggregate is denied' ($analyst.events -eq 0 -and $analyst.purchase -eq 0 -and $analyst.value -eq 0) $analyst
    $brands = Query 'Brand Analyst' 'EVALUATE SELECTCOLUMNS(VALUES(brand_sales_1m[brand]),"brand",brand_sales_1m[brand])'
    Check 'Slicer and raw brand rows contain only apple' ($brands.Count -eq 1 -and $brands[0].brand -eq 'apple') $brands
    $bypass = (Query 'Brand Analyst' "EVALUATE ROW(`"forbidden`",CALCULATE([Brand Purchase Events],REMOVEFILTERS(brand_sales_1m),TREATAS({`"samsung`"},brand_sales_1m[brand])),`"raw_event_rows`",COUNTROWS(ALL(event_metrics_30s)))")[0]
    Check 'Removing filters cannot expose forbidden brand or event rows' ($bypass.forbidden -eq 0 -and (!$bypass.raw_event_rows -or $bypass.raw_event_rows -eq 0)) $bypass
    $result.status='pass'
} catch {$result.status='failed'; $result.error=$_.Exception.Message}
New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
[IO.File]::WriteAllText((Join-Path ([IO.Path]::GetFullPath($OutputDirectory)) 'rls_validation.json'),($result|ConvertTo-Json -Depth 15),[Text.UTF8Encoding]::new($false))
Write-Output "RLS: $($result.status)"
if ($result.error) {Write-Output $result.error}
if ($result.status -ne 'pass') {exit 1}
