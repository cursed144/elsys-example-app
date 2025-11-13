import io
import random
import time
import uuid

from locust import HttpUser, task, between

class FileStorageUser(HttpUser):
    """
    Simulates a user exercising the File Storage API.
    Targets:
      - POST /files       (upload files)
      - GET /files        (list files)
      - GET /files/{name} (download file)
      - GET /health       (health check)
      - GET /metrics      (metrics)
    """
    wait_time = between(0.5, 2)  # пауза между заявките

    def on_start(self):
        """
        При стартиране на всеки виртуален потребител качваме няколко начални файла,
        за да има какво да теглим по-късно.
        """
        self.filenames = []
        # качваме 1-2 начални файла
        for i in range(2):
            self._upload_initial_file(i)

    def _upload_initial_file(self, idx: int):
        name = f"init-{uuid.uuid4().hex[:8]}-{idx}.txt"
        content = f"initial file {idx} at {time.time()}".encode()
        # използваме BytesIO, защото requests/locust приема файлови-like обекти
        with io.BytesIO(content) as fp:
            files = {"file": (name, fp, "text/plain")}
            # name параметъра прави отчета по-четлив в UI
            resp = self.client.post("/files", files=files, name="POST /files")
            if resp.status_code == 200:
                self.filenames.append(name)

    @task(3)
    def health(self):
        self.client.get("/health", name="GET /health")

    @task(4)
    def upload_file(self):
        """
        Качва нов файл с произволно съдържание и запазва името локално.
        Таргетваме POST /files.
        """
        name = f"user-{uuid.uuid4().hex[:10]}.txt"
        content = f"content {uuid.uuid4().hex} {time.time()}".encode()
        with io.BytesIO(content) as fp:
            files = {"file": (name, fp, "text/plain")}
            resp = self.client.post("/files", files=files, name="POST /files")
            if resp.status_code == 200:
                # добавяме само ако е успешно
                self.filenames.append(name)

    @task(4)
    def download_file(self):
        """
        Ако имаме качени имена — теглим произволен файл (GET /files/{filename}).
        Ако нямаме — извикваме /files за да симулираме друг тип трафик.
        """
        if not self.filenames:
            # няма локални имена → извикай листинга
            self.client.get("/files", name="GET /files")
            return

        name = random.choice(self.filenames)
        # url-encode не е нужно тук защото имената са безопасни (uuid-based)
        self.client.get(f"/files/{name}", name="GET /files/{filename}")

    @task(2)
    def list_files(self):
        self.client.get("/files", name="GET /files")

    @task(1)
    def metrics(self):
        self.client.get("/metrics", name="GET /metrics")
