# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên: Nguyễn Thành Duy**
- **MSSV: 2A202602804**
- **Lớp: K4-L3A**
- **Repository URL: https://github.com/duynguy3n2916/K4-L3A-Day13-NguyenThanhDuy-2A202602804-Monitoring-LLMOps**
- **Commit SHA cuối:**
- **Challenge ID: day13-k4-l3a-monitoring-llmops-v1**
- **Tên project Langfuse cá nhân: day13-k4-l3a-2A202602804**

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | [01-pytest.png](evidence/01-pytest.png) |
| Log validator | [02-log-validator.png](evidence/02-log-validator.png) |
| Dashboard validator | [03-dashboard-validator.png](evidence/03-dashboard-validator.png) |
| Structured log | [04-structured-log.png](evidence/04-structured-log.png) |
| PII redaction | [05-pii-redaction.png](evidence/05-pii-redaction.png) |
| Trace list | [06-trace-list.png](evidence/06-trace-list.png) |
| Trace waterfall | [07-trace-waterfall.png](evidence/07-trace-waterfall.png) |
| Trace metadata | [08-trace-metadata.png](evidence/08-trace-metadata.png) |
| Prompt versions | [09-prompt-versions.png](evidence/09-prompt-versions.png) |
| Prompt rollback | [10-prompt-rollback.png](evidence/10-prompt-rollback.png) |
| Dashboard runtime | [11-dashboard-overview.png](evidence/11-dashboard-overview.png) |
| Incident metric | [12-incident-metric.png](evidence/12-incident-metric.png) |
| Incident log | [13-incident-log.png](evidence/13-incident-log.png) |
| Incident trace | [14-incident-trace.png](evidence/14-incident-trace.png) |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 100/100 tại đầu phiên hoàn thiện | 100/100 | Đủ schema, correlation ID, enrichment và PII scrubbing |
| `validate_dashboard.py` | 6/6 | 6/6 | Contract có đúng sáu panel |
| `pytest` | 28 passed | 30 passed | Bổ sung test cho generation trace và dashboard runtime |
| Số traces hợp lệ | Chưa đo | 36 root traces | Vượt yêu cầu tối thiểu 10 trace |
| Số PII leak | 0 | 0 | Validator không phát hiện PII thô |
| Latency P95 / TTFT P95 | 5888 ms / 69 ms trong log trước khi hoàn thiện CP2 | 3793 ms / 66 ms trong cửa sổ challenge | Challenge làm retrieval chậm; TTFT vẫn ổn định |
| Retrieval success rate | 100% | 100% | Incident gây chậm nhưng retrieval không thất bại |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware xóa context cũ, nhận header `x-request-id` hoặc sinh ID dạng `req-<8-hex>`, bind ID vào structlog contextvars, đặt vào `request.state` và trả lại qua header `x-request-id`. Header `x-response-time-ms` ghi thời gian xử lý phía API.
- **Các metadata được ghi vào structured log:** `correlation_id`, `user_id_hash`, `session_id`, `feature`, `model`, `env`, cùng latency, TTFT, token, cost, quality, tool name/success và error type khi có lỗi.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor `scrub_event` chạy trước `JsonlFileProcessor` và `JSONRenderer`. Nó scrub đệ quy string trong payload/dict/list bằng các pattern email, điện thoại Việt Nam, CCCD, thẻ thanh toán và hộ chiếu. User ID chỉ được ghi dưới dạng SHA-256 rút gọn.
- **Cách kiểm chứng kết quả:** Public tests kiểm tra correlation ID, context isolation và các loại PII; log validator đạt 100/100, evidence runtime cho thấy giá trị `[REDACTED_*]` và không còn PII mẫu nguyên văn.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Tôi chạy workload từ repository này với Langfuse key trong `.env` cá nhân. Observations API ghi nhận 31 trace trong 24 giờ gần nhất, vượt yêu cầu tối thiểu 10 trace.
- **Cấu trúc root/retrieval/generation observations:** Root `lab-agent-run` có hai child observation là `rag-retrieval` và `llm-generation`. Retrieval chỉ lưu query preview đã scrub cùng số document; generation lưu model, token usage, cost và TTFT.
- **Cách nối trace với log:** `correlation_id` được bind vào structured log và đồng thời truyền vào trace metadata. Hai request so sánh prompt dùng `req-cp2base` và `req-cp2cand`.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** Version 1, labels `baseline` và `production`.
- **Version/label candidate:** Version 2, label `candidate`.
- **Trace ID của mỗi version:** baseline/v1: `815db1a1ec1fc780c923d69632d83cd6`; candidate/v2: `4c37e9ea48fb00284cb472c606a88b86`.
- **Cách promote và rollback `production`:** Tôi chuyển label `production` từ v1 sang v2 và xác minh fetch theo label trả về v2; sau đó chuyển `production` về v1 và xác minh lại. Trạng thái cuối là v1=`baseline,production`, v2=`candidate`.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Dashboard runtime tại `/dashboard` đọc `data/logs.jsonl` trong cửa sổ 60 phút, tự refresh 30 giây và hiển thị đúng sáu panel: latency/TTFT, traffic, errors/retrieval success, cost, tokens và quality. Mỗi panel có đơn vị và threshold.
- **SLO và lý do chọn:** Trong cửa sổ 28 ngày, 99.5% request phải có `response_sent` với latency không vượt 3000 ms. Ngưỡng này đo trải nghiệm người dùng và không phụ thuộc implementation nội bộ.
- **Cách tính error budget:** `100% - 99.5% = 0.5%`. Ví dụ với 10.000 request, tối đa 50 request được phép lỗi hoặc chậm hơn 3000 ms trong cửa sổ SLO.
- **Ba alert và runbook tương ứng:** `High user-visible latency` (P95 > 3000 ms trong 5 phút), `Elevated request error rate` (>2% trong 5 phút), và `Low answer quality` (quality trung bình <0.75 trong 10 phút). Cả ba là symptom-based, có severity, Slack channel, owner và hướng dẫn điều tra/mitigation trong `docs/alerts.md`.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Khoảng thời gian điều tra:** 16:17:42–16:17:57 ngày 29/09/2026 (Asia/Ho_Chi_Minh), tương ứng 09:17:42–09:17:57 UTC.
- **Triệu chứng từ metrics:** Năm request challenge đều có application latency lớn hơn ngưỡng challenge 2000 ms. Dashboard sau workload ghi nhận latency P95 = 3793 ms, vượt SLO 3000 ms; error rate vẫn là 0%, retrieval success 100% và TTFT P95 chỉ 66 ms.
- **Log line và correlation ID liên quan:** Request đại diện `req-4c83c184`, event `response_sent` lúc `2026-09-29T09:17:46.660039Z`, `latency_ms=3793`, `ttft_ms=50`, `feature=monitoring`, `tool_success=true`.
- **Trace ID và span gây ảnh hưởng:** Trace `fa0d2dd9ee73741cf12f58d97d6f7d53`. Root `lab-agent-run` mất 3.794 giây; child `rag-retrieval` mất 2.501 giây, trong khi `llm-generation` chỉ mất 0.153 giây.
- **Root cause:** Incident `rag_slow` làm bước retrieval chờ khoảng 2.5 giây. Retrieval vẫn thành công nên error rate không tăng, nhưng latency vượt ngưỡng. Generation không phải bottleneck vì chỉ mất khoảng 153 ms.
- **Fix action:** Tắt incident bằng `python scripts/inject_incident.py --disable` và xác nhận `/health` trả `rag_slow=false`.
- **Preventive measure:** Duy trì alert P95 latency, đặt timeout và fallback cho retrieval, cache tài liệu thường dùng, đồng thời theo dõi riêng retrieval span để phát hiện regression trước khi ảnh hưởng toàn bộ request.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Không capture raw input/output trong root và retrieval observations. Trace chỉ lưu preview đã qua `summarize_text`, trong khi generation vẫn ghi usage và cost; cách này giữ khả năng điều tra mà giảm nguy cơ lộ PII.
- **Một lỗi/blocker đã gặp:** Dashboard contract ban đầu đạt 6/6 nhưng chưa có dashboard runtime, và trace chỉ có root/retrieval nên chưa thể xác định đầy đủ thời gian LLM.
- **Cách tìm nguyên nhân và xử lý:** Tôi bổ sung dashboard đọc trực tiếp `data/logs.jsonl`, thêm generation observation bằng API Langfuse v4, ghi model/token/cost/TTFT, bổ sung tests rồi xác minh lại bằng trace thật trên project cá nhân.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics phát hiện triệu chứng và khoảng thời gian; log xác định request cụ thể qua `correlation_id`; trace cùng ID cho biết child span nào chiếm thời gian hoặc phát sinh lỗi; chỉ khi ba lớp khớp nhau mới kết luận root cause.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Prompt version giúp truy xuất cấu hình đã tạo câu trả lời và rollback nhanh khi candidate gây regression. Token/cost kiểm soát ngân sách, còn SLO/error budget định lượng mức độ tin cậy được phép trước khi cần hành động.
- **Điều quan trọng nhất đã học:** Một metric xấu chỉ là triệu chứng; cần correlation ID để nối log với trace và chứng minh nguyên nhân ở đúng span.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Dashboard phục vụ lab bằng dữ liệu JSONL cục bộ và in-memory API metrics, chưa có persistent metrics backend hoặc hệ thống gửi Slack thật. Alert hiện là contract/runbook để triển khai trên hệ thống monitoring thực tế.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA được ghi trong báo cáo.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
