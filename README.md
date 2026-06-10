# Zaneva PoseGen

Web app internal Zaneva untuk generate 25 pose model virtual menggunakan Google Vertex AI Imagen.

## Setup

1. Buka app di browser
2. Pergi ke `/setup` → upload `service-account.json` dari Google Cloud Console
3. Test koneksi → jika OK, login dengan password
4. Upload foto produk → konfigurasi → Generate 25 Pose

## Environment Variables

| Variable | Keterangan | Default |
|---|---|---|
| `APP_PASSWORD` | Password login | `zaneva2024` |
| `SECRET_KEY` | Flask session secret | random |

## Deploy (Easypanel)

1. Buat app baru di Easypanel
2. Source: GitHub repo ini
3. Port: `5003`
4. Set env vars `APP_PASSWORD` dan `SECRET_KEY`
5. Deploy
6. Buka `/setup` → upload service account JSON

## Struktur Output

```
NamaProduk_poses_20240101_120000.zip
├── A_standing/    # 5 pose berdiri
├── B_sports/      # 5 pose olahraga
├── C_casual/      # 5 pose casual
├── D_detail/      # 5 pose detail produk
└── E_candid/      # 5 pose candid
```

## Catatan Vertex AI

- Model: `imagegeneration@006`
- Region: `us-central1`
- Auth: Service Account JSON (upload via `/setup`)
- Estimasi biaya: ~$0.05 per 25 foto
