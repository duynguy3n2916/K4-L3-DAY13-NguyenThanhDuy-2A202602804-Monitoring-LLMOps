# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: High user-visible latency
- Severity: critical
- Duration: 5 phút
- Kênh thông báo: Slack
- SLI/SLO liên quan: 99.5% request có `response_sent` trong tối đa 3000 ms trên cửa sổ 28 ngày.
- Điều kiện và thời gian duy trì: latency P95 lớn hơn 3000 ms liên tục 5 phút.
- Ảnh hưởng tới người dùng: câu trả lời xuất hiện chậm và có thể khiến client timeout.
- Ba bước kiểm tra đầu tiên:
  1. Xác nhận khoảng thời gian P95 vượt ngưỡng trên panel Latency.
  2. Lọc các log `response_sent` chậm và lấy một `correlation_id`.
  3. Mở trace cùng `correlation_id`, so sánh thời gian retrieval và generation.
- Mitigation tạm thời: giảm concurrency, dùng prompt local khi prompt fetch chậm, hoặc vô hiệu incident practice đang bật.
- Owner: `llm-platform-oncall`

## Alert 2

- Tên: Elevated request error rate
- Severity: critical
- Duration: 5 phút
- Kênh thông báo: Slack
- SLI/SLO liên quan: error rate không vượt quá 2%.
- Điều kiện và thời gian duy trì: tỷ lệ `request_failed/request_received` lớn hơn 2% liên tục 5 phút.
- Ảnh hưởng tới người dùng: request trả HTTP 500 và không có câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Xem breakdown theo `error_type` và retrieval success trên panel Errors.
  2. Lấy `correlation_id` từ một log `request_failed` đại diện.
  3. Mở trace tương ứng để tìm observation lỗi và status message.
- Mitigation tạm thời: tắt incident practice, retry có giới hạn hoặc chuyển sang đường fallback an toàn.
- Owner: `llm-platform-oncall`

## Alert 3

- Tên: Low answer quality
- Severity: warning
- Duration: 10 phút
- Kênh thông báo: Slack
- SLI/SLO liên quan: quality score trung bình tối thiểu 0.75.
- Điều kiện và thời gian duy trì: quality score trung bình nhỏ hơn 0.75 liên tục 10 phút.
- Ảnh hưởng tới người dùng: câu trả lời thiếu ngữ cảnh, quá ngắn hoặc không liên quan.
- Ba bước kiểm tra đầu tiên:
  1. Xác nhận thời điểm quality giảm và traffic cùng thời điểm.
  2. Lấy mẫu các log `response_sent` có quality thấp và correlation ID tương ứng.
  3. Kiểm tra trace, retrieval result và prompt version/label đang dùng.
- Mitigation tạm thời: rollback label `production` về prompt baseline đã xác minh.
- Owner: `llm-quality-oncall`
