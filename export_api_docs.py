"""
Скрипт для экспорта OpenAPI документации API в JSON файл
"""
import json
from app.main import app

def export_openapi_schema(output_file: str = "openapi.json"):
    """
    Экспортирует OpenAPI схему в JSON файл
    
    Args:
        output_file: Путь к выходному файлу
    """
    openapi_schema = app.openapi()
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    
    print(f"✅ OpenAPI схема успешно экспортирована в {output_file}")
    print(f"📄 Размер файла: {len(json.dumps(openapi_schema))} байт")
    return output_file

if __name__ == "__main__":
    export_openapi_schema()
