#!/usr/bin/env python3
"""
Script de ejecución multiplataforma para Gestor de Notas
Compatible con Windows, macOS y Linux
"""

import platform
import sys

def verificar_dependencias():
    """Verifica que todas las dependencias estén instaladas"""
    faltantes = []
    
    try:
        import customtkinter
        print("✓ customtkinter")
    except ImportError:
        faltantes.append("customtkinter")
        print("✗ customtkinter")
    
    try:
        import pandas
        print("✓ pandas")
    except ImportError:
        faltantes.append("pandas")
        print("✗ pandas")
    
    try:
        import openpyxl
        print("✓ openpyxl")
    except ImportError:
        faltantes.append("openpyxl")
        print("✗ openpyxl")
    
    try:
        import googleapiclient
        print("✓ google-api-python-client")
    except ImportError:
        faltantes.append("google-api-python-client")
        print("✗ google-api-python-client")
    
    if faltantes:
        print(f"\n❌ Faltan dependencias: {', '.join(faltantes)}")
        print("Instala con: pip install " + " ".join(faltantes))
        return False
    
    return True

def main():
    print(f"🖥️  Sistema: {platform.system()} {platform.release()}")
    print(f"🐍 Python: {platform.python_version()}")
    print("🔍 Verificando dependencias...\n")
    
    if not verificar_dependencias():
        sys.exit(1)
    
    print("\n🚀 Iniciando aplicación...\n")
    
    from main import GestorNotasApp
    
    app = GestorNotasApp()
    app.mainloop()

if __name__ == "__main__":
    main()