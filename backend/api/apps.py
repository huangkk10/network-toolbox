from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    
    def ready(self):
        """
        Django App 啟動時執行
        
        註冊 Signals 以啟用自動化任務觸發
        """
        # 導入 signals 模組以註冊信號處理器
        try:
            import api.signals  # noqa: F401
        except ImportError:
            pass
