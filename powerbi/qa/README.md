# Kiểm thử Power BI

Chạy các lệnh từ thư mục gốc repo. Các script SQL/DAX chỉ đọc dữ liệu; cần Power BI Desktop trên Windows để kiểm model đang mở.

## Kiểm cấu trúc PBIP

```powershell
python -m pip install -r powerbi/qa/requirements-qa.txt
python powerbi/qa/validate_project.py
python powerbi/qa/validate_artifacts.py
```

Script kiểm schema JSON, binding trường, phạm vi canvas, bốn bảng DirectQuery và ba relationship. Kết quả lưu tại [project_validation.json](../evidence/project_validation.json).

Sprint 2 kiểm 103/103 file, gồm 44 mobile layout, không ghi nhận lỗi binding/bounds/overlap/model/role. URL Microsoft `visualContainer/2.14.0` trả 404; validator dùng schema công khai 2.13.0 và ghi rõ ánh xạ trong `compatible_published_schemas`. Đây là kiểm tính tương thích, không phải xác nhận schema chính xác 2.14.0.

## Kiểm Azure SQL

Tài khoản BI cần SELECT và không có INSERT/UPDATE/DELETE trên cả hai fact. Nhập mật khẩu qua prompt:

```powershell
$pbiSecret = Read-Host 'SQL password' -AsSecureString
$pbiCredential = [PSCredential]::new('pbi_reader', $pbiSecret)
$env:PBI_SQL_PASSWORD = $pbiCredential.GetNetworkCredential().Password
try {
    & ./powerbi/qa/validate_sql.ps1 -RunId 'integration-261113'
} finally {
    Remove-Item Env:\PBI_SQL_PASSWORD -ErrorAction SilentlyContinue
    $pbiSecret.Dispose()
    $pbiCredential = $null
}
```

Script kiểm quyền, schema, khóa trùng, giá trị bất hợp lệ và tổng KPI. Với run tích hợp, tổng purchase/count/value của hai fact phải khớp, sai số value tối đa 0,01. Hai fact của `mock-seed` được kiểm riêng vì seed độc lập.

## Kiểm DAX trong Desktop

Xác định engine của đúng cửa sổ Power BI đang mở:

```powershell
Get-Process PBIDesktop | Select-Object Id, MainWindowTitle
Get-CimInstance Win32_Process -Filter "Name='msmdsrv.exe'" |
    Select-Object ProcessId, ParentProcessId, CommandLine
```

Đối chiếu `ParentProcessId` với PID của cửa sổ cần kiểm. Từ `CommandLine`, lấy thư mục `AnalysisServicesWorkspace_...\Data` của engine đó, thay vào đường dẫn dưới đây:

```powershell
$pbiWorkspaceData = '<thu muc Data cua dung engine>'
$pbiPort = [IO.File]::ReadAllText(
    (Join-Path $pbiWorkspaceData 'msmdsrv.port.txt')
).Replace([string][char]0, '')
& ./powerbi/qa/validate_model.ps1 -Port ([int]$pbiPort) -RunId 'integration-261113'
```

Port đổi mỗi lần mở file. Nếu kiểm snapshot, chọn đúng engine và thêm `-ModelKind Snapshot`. Tham số `-DesktopBin` dùng khi thư mục cài Power BI Desktop khác mặc định.

Script kiểm KPI, bộ lọc event và trường hợp không có dữ liệu. DAX có thể dùng cache; nghiệm thu tự cập nhật cần [kiểm thử E2E](../e2e_test_guide.md).

## Kiểm RLS bằng quyền thật của semantic model

```powershell
& ./powerbi/qa/validate_rls.ps1 -Port ([int]$pbiPort) -RunId 'integration-261117'
```

Script mở từng kết nối ADOMD với `Roles=Manager` hoặc `Roles=Brand Analyst`, kiểm count/value, danh sách brand, bảng event bị chặn và truy vấn thử gỡ filter. Không dùng bộ lọc DAX thông thường thay cho RLS. Kết quả `rls_validation.json` phải có 6 kiểm tra PASS. Vẫn cần View as trong Desktop để kiểm visual; hướng dẫn tại [RLS/mobile](../rls_mobile.md).

`prepare_sprint2.py` tái tạo role mẫu Apple và 44 file mobile; thêm `--mobile-only` để chỉ cập nhật bố cục. Đóng dự án trong Desktop trước khi chạy, sau đó mở PBIP và xuất lại PBIX. Không chạy chế độ ghi role trên model đã tùy chỉnh phân quyền.

## Lưu bằng chứng

SQL/DAX mặc định ghi vào `powerbi/evidence/local-check/`, được Git bỏ qua. Dùng `-OutputDirectory` để lưu riêng bằng chứng của một run nghiệm thu. Kết quả kiểm tra đã lưu nằm trong [evidence/](../evidence/README.md); các tiêu chí UI và cập nhật live nằm trong [checklist](../dashboard_test_cases.md).
