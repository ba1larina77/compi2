
import re
from rich import print
from dataclasses import dataclass
import json
import os

# Load configuration
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', 'settings', 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Warning: config.json not found, using default settings")
        return {"Debug": False, "GenerateOutputFile": False}
    except json.JSONDecodeError:
        print("Warning: Invalid JSON in config.json, using default settings")
        return {"Debug": False, "GenerateOutputFile": False}

CONFIG = load_config()# Global configuration
KEYWORDS = {"const": "CONST",
            "var": "VAR",
            "print": "PRINT",
            "return": "RETURN",
            "break": "BREAK",
            "continue": "CONTINUE",
            "if": "IF",
            "else": "ELSE",
            "while": "WHILE",
            "func": "FUNC",
            "import": "IMPORT",
            "true": "BOOL",
            "false": "BOOL",
            "int": "TYPE",
            "float": "TYPE",
            "char": "TYPE",
            "bool": "TYPE"}#palabras reservadas
INT_PATTERN = re.compile(r"\d+")
FLOAT_PATTERN = re.compile(r"(\d+\.\d*)|(\d*\.\d+)")
CHAR_PATTERN = re.compile(r"'(\\.|\\x[A-Za-z0-9]+|.)'")#'a' '\\n' '\\x41' '\\''
TWO_CHAR_TOKENS = {"<=": "LE",
                    ">=": "GE",
                    "==": "EQ",
                    "!=": "NE",
                    "&&": "AND",
                    "||": "OR"}
ONE_CHAR_TOKENS = {"^": "CARET",
                    "+": "PLUS",
                    "-": "MINUS",
                    "*": "MUL",
                    "/": "DIV",
                    "<": "LT",
                    ">": "GT",
                    "=": "ASSIGN",
                    ";": "SEMICOLON",
                    "(": "LPAREN",
                    ")": "RPAREN",
                    "{": "LBRACE",
                    "}": "RBRACE",
                    ",": "COMMA",
                    "!": "NOT",
                    "`": "DEREF"}#` es el simbolo de puntero

@dataclass
class Token:
  type  : str
  value : str
  lineno: int = 1

class Lexer:
    def __init__(self, fileName: str):
        self.fileName = fileName
        self.hasErrors = False
        self.debug = CONFIG.get("Debug", False)
        self.createOutputFile = CONFIG.get("GenerateOutputFile", False)

    def scan(self, text):
        if self.debug:
            print(f"[bold green][DEBUG][/bold green] Iniciando análisis lexico de {len(text)} caracteres")
        index = 0 #indice de texto
        lineno = 1 #contador de linea
        while index < len(text):
            if text[index] in " \t":  # caracteres a ignorar (whitespace, tab)
                index += 1
                continue
            elif text[index:index+2] == "//":  # Comentarios de una linea
                index = text.find("\n", index)
                if index == -1:  # If no newline found, we are at the end of text
                    break
                continue
            elif text[index:index+2] == "/*":  # Comentarios de varias lineas
                start = index
                index = text.find("*/", index)
                if index == -1:
                    print(f"ERROR: COMENTARIO NO TERMINADO EN LINEA {lineno}")
                    self.hasErrors = True
                    break
                lineno += text[start:index].count("\n")
                index += 2
                continue
            elif text[index] == "\n":
                index += 1
                lineno += 1
                continue
            elif text[index].isalpha() or text[index] == '_':  # Identificadores
                start = index
                while index < len(text) and (text[index].isalnum() or text[index] == '_'):
                    index += 1
                if text[start:index] in KEYWORDS:
                    yield Token(KEYWORDS[text[start:index]], text[start:index], lineno)
                    continue
                yield Token("ID", text[start:index], lineno)
                continue
            elif text[index].isdigit() or text[index] == '.':  # Literales numericos
                match = FLOAT_PATTERN.match(text, index)
                if match:
                    yield Token("FLOAT", float(match.group()), lineno)
                    index = match.end()
                    continue
                match = INT_PATTERN.match(text, index)
                if match:
                    yield Token("INTEGER", int(match.group()), lineno)
                    index = match.end()
                    continue
            elif text[index] == "'":  # Literales de caracter
                match = CHAR_PATTERN.match(text, index)
                if match:
                    char_value = self.process_char_literal(match.group())
                    yield Token("CHAR", char_value, lineno)
                    index = match.end()
                    continue
                else:
                    print(f"ERROR: Caracter invalido '{text[index]}' en linea {lineno}")
                    self.hasErrors = True
                    index += 1
            elif text[index] in "+-*/<=>!&|^;(){},`!":  # operadores y simbolos
                start = index
                index += 1
                if text[start:index+1] in ["<=", ">=", "==", "!=", "&&", "||"]:  # Operadores de dos caracteres
                    index += 1
                    yield Token(TWO_CHAR_TOKENS[text[start:index]], text[start:index], lineno)
                    continue
                yield Token(ONE_CHAR_TOKENS[text[start]], text[start:index], lineno)
                continue
            else:
                print(f"ERROR: Caracter invalido '{text[index]}' en linea {lineno}")
                self.hasErrors = True
                index += 1
                
    def process_char_literal(self, char_literal):
        """Convert a character literal string to the actual character it represents"""
        # Remove surrounding quotes
        content = char_literal[1:-1]
        # Handle hex escape sequences
        if content.startswith('\\x'):
            hex_value = content[2:]
            return chr(int(hex_value, 16))
        # Handle other escape sequences
        if content.startswith('\\'):
            escape_map = {
                '\\n': '\n',
                '\\t': '\t',
                '\\r': '\r',
                '\\\\': '\\',
                '\\"': '"',
                "\\'": "'"
            }
            return escape_map.get(content, content[1])
        # Regular character
        return content
    
    def tokenize(self, text):
        #scanner = re.Scanner(self.tokens)
        try:
            raw = self.scan(text)
            results = list(raw)
            if self.hasErrors:
                raise SyntaxError("Errores lexicos encontrados!")
            if self.debug:
                print(f"[bold green][DEBUG][/bold green] Análisis lexico completado con {len(results)} tokens")
            if self.createOutputFile:
                output_path = os.path.join(os.path.dirname(__file__), '..', 'output',f'{self.fileName}' , 'tokens.json')
                with open(output_path, 'w') as f:
                    json.dump([token.__dict__ for token in results], f, indent=4)
                print(f"[bold blue][OUTPUT][/bold blue] Tokens written to {output_path}")
            return results
        except SyntaxError as e:
            raise SyntaxError(e)
