# Lab 16 — Báo cáo LightGBM trên GCP (CPU)

**Học viên:** Nguyễn Thanh Phong — 2A202602843

## Tóm tắt

1. Tôi dùng GCP, `us-central1-a`, máy `e2-medium` (2 vCPU, 4 GB RAM), source commit `55539f67d7c78b43afe334a2ec3271c4bfdbbe2d`. Hạ tầng dựng bằng Terraform trong `infra/`.
2. Dataset có 284.807 dòng × 31 cột. Tôi chia train/test 80/20 có stratify, rồi tách 10% tập train làm validation cho early stopping. Seed là 42.
3. Load dữ liệu mất 2.52 giây, training mất 6.18 giây, best iteration là 52.
4. Trên tập test: AUC 0.9767, Accuracy 0.9994, F1 0.8242, Precision 0.8929, Recall 0.7653.
5. Latency 1 dòng là 1.32 ms (median của 100 lần, sau 10 lần warm-up). Batch 1.000 dòng mất 3.29 ms, tức khoảng 303.788 dòng/giây (median của 10 lần).
6. Trong lúc training, `python3` dùng 178% CPU và khoảng 494 MB RAM ([ảnh 02](screenshots/02_top_during_training.png)). Sau khi chạy xong, RAM dùng 492 Mi / 3.8 Gi và RX tích lũy khoảng 257 MB ([ảnh 04](screenshots/04_free_iplink_after_benchmark.png)). Biểu đồ trên Console ở [ảnh 05](screenshots/05_monitoring_cpu.png) và [ảnh 06](screenshots/06_monitoring_network.png).
7. Billing ngày 02/10/2026 chưa cập nhật, vẫn hiển thị ₫0 ([ảnh 07](screenshots/07_billing_not_updated_yet.png)). Ước tính riêng khoảng $0.07 cho cả hai lần dựng hạ tầng.
8. Tôi đã tải kết quả về rồi xóa tài nguyên bằng `terraform destroy` lúc 17:58 (UTC+7) ngày 02/10/2026. Bằng chứng dọn dẹp: `terraform state list` trống, và `gcloud compute instances/disks/routers/forwarding-rules/addresses/backend-services list` đều trả về 0 mục (kiểm tra lại lúc ~22:45).

## Môi trường đo

| Mục | Giá trị |
|---|---|
| Cloud | Google Cloud Platform (Project `ai-infras-510409`) |
| Instance | `e2-medium` — 2 vCPU, 4 GB RAM, Debian 12, x86_64 |
| Region / Zone | `us-central1` / `us-central1-a` |
| Truy cập | SSH qua IAP (VM nằm trong private subnet, ra internet qua Cloud NAT) |
| Hạ tầng | Terraform (`terraform-gcp/`), `gpu_count=0` |
| Thời điểm đo | 02/10/2026, ~17:50 (UTC+7) |

## Dataset

Kaggle `mlg-ulb/creditcardfraud`, kiểm tra trên VM ([ảnh 01](screenshots/01_dataset_check.png)):

- Shape: 284.807 dòng × 31 cột
- Missing: 0
- Class: `{0: 284315, 1: 492}`, tức 0.17% là giao dịch gian lận

## Cách đo

- **Split:** train/test 80/20, `stratify=y`, `random_state=42`. Tách tiếp 10% tập train làm validation (stratify) cho early stopping. Tập test chỉ dùng cho đánh giá cuối.
- **Model:** `LGBMClassifier` (lr 0.05, num_leaves 31, subsample/colsample 0.8), tối đa 1000 vòng, early stopping 100 vòng theo AUC trên validation.
- **Đánh giá:** AUC-ROC dùng xác suất từ `predict_proba`; Accuracy/F1/Precision/Recall dùng nhãn với ngưỡng 0.5.
- **Latency (1 dòng):** 10 lần warm-up, đo 100 lần, lấy median (ms). Chỉ tính `predict_proba` trên dữ liệu đã nằm trong bộ nhớ.
- **Throughput (1000 dòng):** đo 10 lần, lấy median; throughput = 1000 / thời gian (giây), đơn vị dòng/giây.

## Kết quả ([`benchmark_result.json`](benchmark_result.json), [ảnh 03](screenshots/03_benchmark_output.png))

| Metric | Kết quả |
|---|---|
| Thời gian load data | 2.52 s |
| Thời gian training | 6.18 s |
| Best iteration | 52 |
| AUC-ROC | 0.9767 |
| Accuracy | 0.9994 |
| F1-Score | 0.8242 |
| Precision | 0.8929 |
| Recall | 0.7653 |
| Inference latency (1 row) | 1.32 ms |
| Inference throughput (1000 rows) | 3.29 ms → ~303.788 dòng/giây |

## Tài nguyên trên VM

| Ảnh | Nội dung |
|---|---|
| [02 — `top` trong lúc training](screenshots/02_top_during_training.png) | Tiến trình `python3` dùng 178% CPU (gần hết 2 vCPU), RES ~494 MB (12.6% RAM) |
| [04 — `free -h`, `ip -s link`](screenshots/04_free_iplink_after_benchmark.png) | Chụp **sau khi chạy benchmark**: RAM dùng 492 Mi / 3.8 Gi, không có swap. `ens4` nhận tích lũy ~257 MB (RX), gửi ~1.2 MB (TX); đây là số byte cộng dồn từ lúc boot (pip packages + dataset), không phải tốc độ mạng tức thời |
| [05 — Console Monitoring: CPU](screenshots/05_monitoring_cpu.png) | Biểu đồ CPU Utilization của VM |
| [06 — Console Monitoring: Network](screenshots/06_monitoring_network.png) | Kết nối và lưu lượng mạng của VM |

## Tài nguyên và chi phí

### Thời gian tồn tại của tài nguyên (theo Cloud Audit Logs, giờ UTC+7)

Hạ tầng được dựng hai lần. Lần 2 dùng để chạy lại benchmark và chụp ảnh tài nguyên.

| Lần | Tài nguyên | Tạo | Xóa | Tồn tại |
|---|---|---|---|---|
| 1 | Cloud Router + NAT | 16:35 | 17:05 | ~30 phút |
| 1 | VM `ai-gpu-node` (đĩa 30 GB) | 16:36 | 17:04 | ~28 phút |
| 1 | Load Balancer | 16:39 | 17:02 | ~23 phút |
| 2 | Cloud Router + NAT | 17:43 | 17:58 | ~15 phút |
| 2 | VM `ai-gpu-node` (đĩa 30 GB) | 17:44 | 17:57 | ~13 phút |
| 2 | Load Balancer | 17:47 | 17:55 | ~8 phút |

Sau mỗi lần, toàn bộ tài nguyên đã xóa bằng `terraform destroy`. Đã kiểm tra lại bằng `gcloud compute instances/routers/forwarding-rules/addresses list`: không còn tài nguyên nào của lab.

### Ước tính chi phí (giá niêm yết us-central1, tổng ~0.75 giờ)

| Hạng mục | Cách tính | Ước tính |
|---|---|---|
| VM e2-medium | ~$0.034/giờ × 0.68 giờ | ~$0.023 |
| Đĩa 30 GB pd-standard | $0.04/GB-tháng × 30 GB | < $0.002 |
| Cloud NAT gateway + IP NAT | ~$0.0014/VM-giờ + $0.005/IP-giờ | ~$0.005 |
| Cloud NAT xử lý dữ liệu | $0.045/GB × ~0.6 GB (2 lần pip packages + dataset, ~257 MB/lần theo `ip -s link`) | ~$0.027 |
| Load Balancer forwarding rule | $0.025/giờ × ~0.52 giờ | ~$0.013 |
| **Tổng ước tính** | | **~$0.07** |

Đây là con số ước tính, không phải hóa đơn.

### Chi phí đã ghi nhận trên Billing

Billing chưa cập nhật tại thời điểm 02/10/2026 ([ảnh 07](screenshots/07_billing_not_updated_yet.png): Billing → Reports, tháng hiện tại, group by Product, hiển thị ₫0). GCP có thể trễ hơn 24 giờ mới hiện chi phí. Sẽ chụp bổ sung ảnh Billing (lọc project `ai-infras-510409`, Last 7 days, group by Service/SKU) sau khi dữ liệu cập nhật. Nếu tài khoản đang dùng Free Trial, chi phí được trừ vào credit.

## Nhận xét

Trên máy `e2-medium` chỉ có CPU (2 vCPU, 4 GB RAM), LightGBM đọc 284.807 giao dịch trong 2.5 giây và huấn luyện trong 6.2 giây. Early stopping dừng ở vòng 52. Trong lúc training, tiến trình dùng khoảng 178% CPU (gần hết 2 vCPU) nhưng chỉ khoảng 500 MB RAM. Như vậy với dữ liệu dạng bảng cỡ này, máy CPU nhỏ là đủ và không cần GPU. AUC-ROC đạt 0.977, cho thấy mô hình xếp hạng giao dịch gian lận và hợp lệ rất tốt. Accuracy 99.94% không có nhiều ý nghĩa, vì giao dịch gian lận chỉ chiếm 0.17% (492/284.807): một mô hình đoán mọi giao dịch là bình thường cũng đạt khoảng 99.83%. Các chỉ số đáng xem hơn là Precision 0.89, Recall 0.77 và F1 0.82. Mô hình bắt được khoảng 77% giao dịch gian lận, và cứ 10 lần cảnh báo thì khoảng 9 lần đúng. Muốn tăng Recall có thể hạ ngưỡng phân loại xuống dưới 0.5, đổi lại sẽ giảm Precision. Dự đoán một giao dịch mất khoảng 1.32 ms, còn 1000 giao dịch mất 3.29 ms (khoảng 300 nghìn dòng/giây). Thời gian dự đoán một dòng chủ yếu là chi phí gọi hàm cố định, nên chạy theo lô hiệu quả hơn rất nhiều. Toàn bộ bài lab (hai lần dựng hạ tầng) ước tính tốn dưới $0.1. Starter vẫn tạo Cloud NAT và Load Balancer trong luồng CPU, nên chi phí không chỉ là giá VM.

**Ghi chú:** lần chạy đầu tiên cho AUC 0.04 và best iteration 2. Nguyên nhân là `scale_pos_weight` quá lớn (khoảng 578) làm logloss tăng ngay từ đầu, trong khi early stopping theo dõi cả logloss nên dừng sớm. Sau khi bỏ `scale_pos_weight` và chỉ dừng sớm theo AUC, mô hình học bình thường. Lần chạy lần 1 (sau khi sửa) và lần 2 cho cùng metrics chất lượng (cùng seed); thời gian chỉ chênh nhẹ (training 6.47 s so với 6.18 s). Kết quả ở trên là của lần 2.
