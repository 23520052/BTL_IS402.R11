# DAX measures

## Total Events

```dax
Total Events = COALESCE(SUM('event_metrics_30s'[event_count]), 0)
```

Format: `#,0`.

## Events In Window

```dax
Events In Window = SUM('event_metrics_30s'[event_count])
```

Format: `#,0`.

## Purchase Events

```dax
Purchase Events = CALCULATE([Total Events], REMOVEFILTERS(DimEvent), 'event_metrics_30s'[event_type] = "purchase")
```

Format: `#,0`.

## View Events

```dax
View Events = CALCULATE([Total Events], REMOVEFILTERS(DimEvent), 'event_metrics_30s'[event_type] = "view")
```

Format: `#,0`.

## Cart Events

```dax
Cart Events = CALCULATE([Total Events], REMOVEFILTERS(DimEvent), 'event_metrics_30s'[event_type] = "cart")
```

Format: `#,0`.

## Remove Events

```dax
Remove Events = CALCULATE([Total Events], REMOVEFILTERS(DimEvent), 'event_metrics_30s'[event_type] = "remove_from_cart")
```

Format: `#,0`.

## Purchase Value

```dax
Purchase Value = COALESCE(CALCULATE(SUM('event_metrics_30s'[revenue]), REMOVEFILTERS(DimEvent), 'event_metrics_30s'[event_type] = "purchase"), 0)
```

Format: `#,0.00`.

## Purchase Value In Window

```dax
Purchase Value In Window = CALCULATE(SUM('event_metrics_30s'[revenue]), REMOVEFILTERS(DimEvent), 'event_metrics_30s'[event_type] = "purchase")
```

Format: `#,0.00`.

## Purchase To View Ratio

```dax
Purchase To View Ratio = DIVIDE([Purchase Events], [View Events])
```

Format: `0.00%`.

## Cart To View Ratio

```dax
Cart To View Ratio = DIVIDE([Cart Events], [View Events])
```

Format: `0.00%`.

## Brand Purchase Events

```dax
Brand Purchase Events = COALESCE(SUM('brand_sales_1m'[purchase_events]), 0)
```

Format: `#,0`.

## Brand Purchase Value

```dax
Brand Purchase Value = COALESCE(SUM('brand_sales_1m'[revenue]), 0)
```

Format: `#,0.00`.

## Brand Value Share

```dax
Brand Value Share = DIVIDE([Brand Purchase Value], CALCULATE([Brand Purchase Value], ALLSELECTED('brand_sales_1m'[brand])))
```

Format: `0.00%`.

## Last Window UTC

```dax
Last Window UTC = MAX('event_metrics_30s'[window_end])
```

Format: `yyyy-MM-dd HH:mm:ss`.

## Window Age Seconds

```dax
Window Age Seconds = VAR LastWindow = [Last Window UTC] RETURN IF(NOT ISBLANK(LastWindow), DATEDIFF(LastWindow, UTCNOW(), SECOND))
```

Format: `#,0`.

## Data Scope

```dax
Data Scope = VAR R = SELECTEDVALUE(DimRun[run_id]) RETURN IF(ISBLANK(R), "MULTIPLE RUNS / select one run", IF(R = "mock-seed", "MOCK / simulated data", "RUN / " & R))
```

Format: `text`.

Các measure theo loại event bỏ lọc DimEvent để KPI purchase/view giữ nguyên khi chọn event khác trên Monitoring. Total Events vẫn tôn trọng slicer. Tỷ lệ trả BLANK khi mẫu số bằng 0. Brand Value Share dùng ALLSELECTED nên mẫu số là tổng các brand đang được chọn; không gỡ RLS.

Trend dùng Events In Window và Purchase Value In Window giữ BLANK cho cửa sổ ngoài run đang chọn; tránh vẽ số 0 giả trên các ngày của run khác. Card dùng measure COALESCE để hiển thị 0 khi không có dữ liệu.
