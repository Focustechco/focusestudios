import os
import hashlib
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from app.adapters.drive.base import BaseDriveAdapter, DriveFileMetadata


class MockDriveAdapter(BaseDriveAdapter):
    """
    Adaptador simulado para modo DEMO.
    Gera arquivos de teste com metadados realistas para demonstrar o fluxo completo
    de sincronização, inspeção, calendário de 10 posts/dia e consentimento.
    """

    SAMPLE_VIDEOS = [
        ("focus_tech_01_produtividade.mp4", 15_240_000, "2026-11-01T08:00:00Z"),
        ("focus_tech_02_atalhos_vscode.mp4", 18_100_000, "2026-11-01T09:30:00Z"),
        ("focus_tech_03_python_dicas.mp4", 14_500_000, "2026-11-01T11:00:00Z"),
        ("focus_tech_04_docker_pratico.mp4", 22_400_000, "2026-11-01T12:30:00Z"),
        ("focus_tech_05_foco_profundo.mp4", 16_800_000, "2026-11-01T14:00:00Z"),
        ("focus_tech_06_automacao_scripts.mp4", 19_200_000, "2026-11-01T15:30:00Z"),
        ("focus_tech_07_postgresql_tips.mp4", 17_400_000, "2026-11-01T17:00:00Z"),
        ("focus_tech_08_rotina_dev.mp4", 13_900_000, "2026-11-01T18:30:00Z"),
        ("focus_tech_09_fastapi_performance.mp4", 21_100_000, "2026-11-01T20:00:00Z"),
        ("focus_tech_10_resumo_semanal.mp4", 25_000_000, "2026-11-01T21:30:00Z"),
        ("focus_tech_11_git_rebase.mp4", 14_800_000, "2026-11-02T08:00:00Z"),
        ("focus_tech_12_clean_architecture.mp4", 28_300_000, "2026-11-02T09:30:00Z"),
        ("focus_tech_13_celery_redis.mp4", 19_600_000, "2026-11-02T11:00:00Z"),
        ("focus_tech_14_monitoramento_vps.mp4", 16_200_000, "2026-11-02T12:30:00Z"),
        ("focus_tech_15_seguranca_apis.mp4", 20_500_000, "2026-11-02T14:00:00Z"),
    ]

    def list_files(
        self,
        folder_id: str,
        page_token: Optional[str] = None,
        include_subfolders: bool = False
    ) -> Tuple[List[DriveFileMetadata], Optional[str]]:
        results = []
        page_size = 10
        start_idx = int(page_token) if page_token and page_token.isdigit() else 0
        end_idx = min(start_idx + page_size, len(self.SAMPLE_VIDEOS))

        for idx in range(start_idx, end_idx):
            filename, size, mod_time = self.SAMPLE_VIDEOS[idx]
            file_id = f"mock_file_{idx+1:03d}"
            # MD5 determinístico
            md5_hash = hashlib.md5(f"content_{file_id}".encode()).hexdigest()
            results.append(
                DriveFileMetadata(
                    file_id=file_id,
                    name=filename,
                    mime_type="video/mp4",
                    size_bytes=size,
                    md5_checksum=md5_hash,
                    modified_time=mod_time
                )
            )

        next_page = str(end_idx) if end_idx < len(self.SAMPLE_VIDEOS) else None
        return results, next_page

    def download_file(self, file_id: str, target_path: str) -> str:
        """Gera ou copia o arquivo MP4 real específico do item e retorna seu SHA-256 único."""
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        # Mapeia o sample de 1 a 15 de acordo com o file_id
        sample_idx = 1
        if "mock_file_" in file_id:
            try:
                num = int(file_id.split("mock_file_")[1].split("_")[0])
                sample_idx = ((num - 1) % 15) + 1
            except Exception:
                sample_idx = 1

        sample_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "web", "static", "video", "samples")
        )
        sample_path = os.path.join(sample_dir, f"sample_{sample_idx:02d}.mp4")
        if not os.path.exists(sample_path):
            sample_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "web", "static", "video", "sample_preview.mp4")
            )
        
        if os.path.exists(sample_path):
            with open(sample_path, "rb") as sf:
                sample_bytes = sf.read()
            # Trailer seguro para diferenciar o hash SHA-256 de cada vídeo de exemplo
            content = sample_bytes + f"\n<!-- file_id:{file_id} -->\n".encode("utf-8")
        else:
            content = f"FOCUS_PUBLISHER_SYNTHETIC_MEDIA_PAYLOAD_FOR_{file_id}".encode("utf-8") * 100
        
        with open(target_path, "wb") as f:
            f.write(content)
        
        return hashlib.sha256(content).hexdigest()

