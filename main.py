from source.parser import Parser
from source.checker import Checker
from source.lexer import Lexer
from source.ircode import IRCode
from source.stack_machine import StackMachine
from rich import print
import json
import os

def load_config():
    """
    Carga la configuración desde 'settings/config.json'. 
    Si no existe o es inválido, devuelve configuración por defecto.
    """
    config_path = os.path.join(os.path.dirname(__file__), 'settings', 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Advertencia: config.json no encontrado, se usarán ajustes por defecto.")
        return {"Debug": False, "GenerateOutputFile": False}
    except json.JSONDecodeError:
        print("Advertencia: JSON inválido en config.json, se usarán ajustes por defecto.")
        return {"Debug": False, "GenerateOutputFile": False}

CONFIG = load_config()

def read_file(file_path):
    """
    Lee y devuelve el contenido de un archivo como texto.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def create_output_directory(filePath):
    """
    Crea un directorio de salida basado en el nombre del archivo,
    si la configuración 'GenerateOutputFile' está activa.
    """
    fileName = filePath.split('/')[-1].split('\\')[-1].split('.')[0]
    if CONFIG.get("GenerateOutputFile", False):
        output_dir = os.path.join(os.path.dirname(__file__), 'output', fileName)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    return fileName

def compile(file):
    """
    Función principal que ejecuta el proceso de compilación:
    análisis léxico, sintáctico, chequeo semántico, generación de código
    intermedio y ejecución en la máquina virtual.
    Muestra mensajes explicativos indicando por qué cada etapa es correcta.
    """
    debug = CONFIG.get("Debug", False)
    print(f"[bold green]Compilando {file}...[/bold green]")
    content = read_file(file)
    fileName = create_output_directory(file)
    try:
        # Análisis léxico
        lex = Lexer(fileName)
        fileTokens = lex.tokenize(content)
        if debug:
            print(f"[bold yellow]Tokens generados:[/bold yellow] {fileTokens}")
        print(f"[bold blue]Análisis léxico correcto:[/bold blue] Se detectaron {len(fileTokens)} tokens válidos en el archivo.")
        
        # Análisis sintáctico
        parser = Parser(fileTokens, fileName)
        top = parser.parse()
        statements = top.stmts
        if debug:
            print(f"[bold yellow]Árbol sintáctico generado:[/bold yellow] {statements}")
        print(f"[bold blue]Análisis sintáctico correcto:[/bold blue] El parser pudo construir un árbol sintáctico con {len(statements)} declaraciones sin errores.")
        
        # Chequeo semántico
        systab = Checker.check(top, fileName)
        if debug:
            systab.print()
        print(f"[bold blue]Chequeo semántico correcto:[/bold blue] Todas las variables, tipos y expresiones cumplen con las reglas del lenguaje, sin errores detectados.")
        
        # Generación de código intermedio (IR)
        module = IRCode.gencode(statements, fileName)
        if debug:
            module.dump()
        print(f"[bold blue]Generación de código intermedio correcta:[/bold blue] El módulo IR fue generado exitosamente y está listo para su ejecución.")
        
        # Ejecución en la máquina virtual
        vm = StackMachine()
        vm.load_module(module)
        vm.run()
        print(f"[bold green]Ejecución correcta:[/bold green] El código IR se ejecutó sin errores, finalizando el proceso de compilación exitosamente.")
    except Exception as e:
        print(f"[bold red]Error durante la compilación:[/bold red] {e}")

def run_tests():
    """Ejecuta una serie de pruebas de compilación sobre archivos GOX predefinidos.
    Cada archivo se compila y se muestra un mensaje indicando el resultado de la compilación.
    """
    base_dir = './tests'
    test_files = []

    for i in range(12):
        if i == 0:
            test_files.append('Jhosuar.gox')
        else:
            test_files.append(f'Jhosuar{i}.gox')

    test_files += ['criba.gox', 'mandelplot.gox', 'Mauro.gox', 'Mauro1.gox', 'Mauro2.gox']

    for test_file in test_files:
        file_path = os.path.join(base_dir, test_file)
        if os.path.exists(file_path):
            print(f"\n[bold magenta]=== Ejecutando test: {test_file} ===[/bold magenta]")
            compile(file_path)
        else:
            print(f"[bold red]Archivo no encontrado:[/bold red] {file_path}")

if __name__ == '__main__':
    run_tests()

