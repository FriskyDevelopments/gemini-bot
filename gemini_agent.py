import os
import subprocess
import google.generativeai as genai

# Forzamos Flash para evitar el 404 de la versión Pro en algunas regiones
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT)
    except Exception as e:
        return f"Error: {str(e)}"

def audit_project():
    print("🔍 Fase 1: Escaneando ClipFLOW (Mty Edition)...")
    structure = run_cmd("find . -maxdepth 2 -not -path '*/.*'")
    return structure

def generate_full_plan(context):
    print("📝 Fase 2: Diseñando arquitectura Frisky Ghost + Producción...")
    prompt = f"""
    CONTEXTO: {context}
    TAREA: Auditoría total para producción.
    REQUERIMIENTOS ESPECIALES:
    1. Implementar Watermark dinámica en ClipFLOW.
    2. Lógica de 'Frisky Ghost': Encriptado AES-256 para protección de archivos sensibles.
    3. Guía de despliegue para Render/GitHub.
    
    Genera un archivo 'IMPLEMENTATION_PLAN.md' con los pasos técnicos.
    """
    response = model.generate_content(prompt)
    with open("IMPLEMENTATION_PLAN.md", "w") as f:
        f.write(response.text)
    return response.text

if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ Error: La API Key no se detectó. Ejecuta 'export GEMINI_API_KEY=tu_llave'")
    else:
        ctx = audit_project()
        plan = generate_full_plan(ctx)
        print("✅ ¡Plan de batalla listo en IMPLEMENTATION_PLAN.md!")
        print("\nPróximo paso: Revisa el archivo .md y dime 'ejecutar' para generar el código.")
