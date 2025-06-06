# parse.py



from rich import print
from typing import List
from dataclasses import dataclass
from source.model import (
    Integer, Float, Char, Bool, TypeCast, BinOp, 
    UnaryOp, Assignment, Variable, NamedLocation, MemoryLocation, 
    Break, Continue, Return, Print, If, While, 
    Function, Parameter, FunctionCall, Program,
)
import json,os
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
# -------------------------------
@dataclass
class Token:
	type  : str
	value : str
	lineno: int = 1
# -------------------------------
# Implementación del Parser
# -------------------------------
class Parser:
	def __init__(self, tokens: List[Token], fileName: str):
		self.tokens = tokens
		self.current = 0
		self.fileName = fileName
		self.debug = CONFIG.get("Debug", False)
		self.createOutputFile = CONFIG.get("GenerateOutputFile", False)

	def parse(self) -> Program:
		statements = []
		if self.debug:
			print(f"[bold green][DEBUG][/bold green] Iniciando analisis sintactico del archivo file: {self.fileName}")
		while self.peek() and self.peek().type != "EOF":
			statements.append(self.statement())
		if self.debug:
			print(f"[bold green][DEBUG][/bold green] Analisis sintactico completado. Se procesaron {len(statements)} declaraciones.")
		if self.createOutputFile:
			ast_file_path = os.path.join(os.path.dirname(__file__), '..', 'output',f'{self.fileName}' , f'{self.fileName}_ast.json')# Guardar el AST como JSON
			ASTSerializer.save_ast_to_json(statements, ast_file_path)
			print(f"[bold blue][OUTPUT][/bold blue] AST saved to: {ast_file_path}")
		return Program(statements)

	# -------------------------------
	# Análisis de declaraciones
	# -------------------------------
	def statement(self):
		token = self.peek()
		if token and (token.type == "ID" or token.type == "DEREF"):
			return self.assignment_or_funcCall()
		elif token and (token.type == "VAR" or token.type == "CONST"):
			return self.vardecl()
		elif token and (token.type == "IMPORT" or token.type == "FUNC"):
			return self.funcdecl()
		elif token and token.type == "IF":
			return self.if_stmt()
		elif token and token.type == "WHILE":
			return self.while_stmt()
		elif token and token.type == "BREAK":
			self.consume("BREAK", "Se esperaba 'break'")
			self.consume("SEMICOLON", "Se esperaba ';' al final de la declaración 'break'")
			return Break()
		elif token and token.type == "CONTINUE":
			self.consume("CONTINUE", "Se esperaba 'continue'")
			self.consume("SEMICOLON", "Se esperaba ';' al final de la declaración 'continue'")
			return Continue()
		elif token and token.type == "RETURN":
			return self.return_stmt()
		elif token and token.type == "PRINT":
			return self.print_stmt()
		else:
			print(f"ERROR: Token {token}: Declaración inesperada")
			raise SystemExit()
	
	def assignment_or_funcCall(self):
		loc = self.location()
		if self.match("LPAREN"):
			args = self.arguments()
			self.consume("SEMICOLON", "Se esperaba ';' al final de la llamada a la función")
			return FunctionCall(loc.name, args)
		else:
			self.consume("ASSIGN", "Se esperaba '=' en la asignación")
			expr = self.expression()
			self.consume("SEMICOLON", "Se esperaba ';' al final de la asignación")
			return Assignment(loc, expr)
		
	def assignment(self):
		# assignment <- location '=' expression ';'
		loc = self.location()
		self.consume("ASSIGN", "Se esperaba '=' en la asignación")
		expr = self.expression()
		self.consume("SEMICOLON", "Se esperaba ';' al final de la asignación")
		return Assignment(loc, expr)
		
	def vardecl(self):
		# vardecl <- ('var'/'const') ID type? ('=' expression)? ';'
		is_const = self.match("CONST")
		if not is_const:
			self.consume("VAR", "Se esperaba 'var' o 'const'")
		var_name = self.consume("ID", "Se esperaba un identificador para la variable").value
		var_type = None
		if self.match("TYPE"):
			var_type = self.tokens[self.current - 1].value
		initial_value = None
		if self.match("ASSIGN"):
			initial_value = self.expression()
		self.consume("SEMICOLON", "Se esperaba ';' al final de la declaración de variable")
		return Variable(var_name, var_type, initial_value, is_const)
		
	def funcdecl(self):
		# funcdecl <- 'import'? 'func' ID '(' parameters ')' type '{' statement* '}'
		imported = self.match("IMPORT")
		self.consume("FUNC", "Se esperaba 'func'")
		func_name = self.consume("ID", "Se esperaba un identificador para el nombre de la función").value
		self.consume("LPAREN", "Se esperaba '('")
		params = self.parameters()
		self.consume("RPAREN", "Se esperaba ')'")
		func_type = None
		if self.match("TYPE"):
			func_type = self.tokens[self.current - 1].value
		if imported:
			self.consume("SEMICOLON", "Se esperaba ';' al final de la declaración de importación")
			return Function(imported, func_name, params, func_type, [])
		self.consume("LBRACE", "Se esperaba '{' después de la declaración de la función")
		statements = []
		while not self.match("RBRACE"):
			if not self.peek():  # Check if end of file is reached
				print("ERROR: Se esperaba '}' al final de la declaración de la función")
				raise SystemExit()
			statements.append(self.statement())
		return Function(imported, func_name, params, func_type, statements)
		
	def if_stmt(self):
		# if_stmt <- 'if' expression '{' statement* '}'
		#         /  'if' expression '{' statement* '}' else '{' statement* '}'
		self.consume("IF", "Se esperaba 'if'")
		condition = self.expression()
		self.consume("LBRACE", "Se esperaba '{' después de la condición del 'if'")
		if_statements = []
		while not self.match("RBRACE"):
			if_statements.append(self.statement())
		else_statements = []
		if self.match("ELSE"):
			self.consume("LBRACE", "Se esperaba '{' después de 'else'")
			while not self.match("RBRACE"):
				else_statements.append(self.statement())
		return If(condition, if_statements, else_statements)

	def while_stmt(self):
		# while_stmt <- 'while' expression '{' statement* '}'
		self.consume("WHILE", "Se esperaba 'while'")
		condition = self.expression()
		self.consume("LBRACE", "Se esperaba '{' después de la condición del 'while'")
		statements = []
		while not self.match("RBRACE"):
			statements.append(self.statement())
		return While(condition, statements)
		
	def return_stmt(self):
		# return_stmt <- 'return' expression ';'
		self.consume("RETURN", "Se esperaba 'return'")
		expr = self.expression()
		self.consume("SEMICOLON", "Se esperaba ';' al final de la declaración")
		return Return(expr)
		
	def print_stmt(self):
		# print_stmt <- 'print' expression ';'
		self.consume("PRINT", "Se esperaba 'print'")
		expr = self.expression()
		self.consume("SEMICOLON", "Se esperaba ';' al final de la declaración")
		return Print(expr)
		
	# -------------------------------
	# Análisis de expresiones
	# -------------------------------
	def expression(self):
		# expression <- orterm ('||' orterm)*
		return self.binary_op(["OR"], "orterm")
		
	def orterm(self):
		# orterm <- andterm ('&&' andterm)*
		return self.binary_op(["AND"], "andterm")
		
	def andterm(self):
		# andterm <- relterm (('<' / '>' / '<=' / '>=' / '==' / '!=') relterm)*
		return self.binary_op(["LT", "GT", "LE", "GE", "EQ", "NE"], "relterm")
		
	def relterm(self):
		# relterm <- addterm (('+' / '-') addterm)*
		return self.binary_op(["PLUS", "MINUS"], "addterm")
		
	def addterm(self):
		# addterm <- factor (('*' / '/') factor)*
		return self.binary_op(["MUL", "DIV"], "factor")
	
	def binary_op(self, operators, next_rule):
		# binary_op <- next_rule (operators next_rule)*
		left = getattr(self, next_rule)()
		while self.peek() and self.peek().type in operators:
			operator = self.advance().value
			right = getattr(self, next_rule)()
			left = BinOp(operator, left, right)
		return left
		
	def factor(self):
		# factor <- literal
		#        / ('+' / '-' / '^') expression
		#        / '(' expression ')'
		#        / type '(' expression ')'
		#        / ID '(' arguments ')'
		#        / location
		if self.match("INTEGER"):
			return Integer(self.tokens[self.current - 1].value)
		elif self.match("FLOAT"):
			return Float(self.tokens[self.current - 1].value)
		elif self.match("CHAR"):
			return Char(self.tokens[self.current - 1].value)
		elif self.match("BOOL"):
			return Bool(self.tokens[self.current - 1].value)
		elif self.match("PLUS") or self.match("MINUS") or self.match("CARET") or self.match("NOT"):
			operator = self.tokens[self.current - 1].value
			expr = self.factor()
			return UnaryOp(operator, expr)
		elif self.match("LPAREN"):
			expr = self.expression()
			self.consume("RPAREN", "Se esperaba ')' después de la expresión")
			return expr
		elif self.match("TYPE"):
			cast_type = self.tokens[self.current - 1].value
			self.consume("LPAREN", "Se esperaba '(' después del tipo")
			expr = self.expression()
			self.consume("RPAREN", "Se esperaba ')' después de la expresión")
			return TypeCast(cast_type, expr)
		elif self.match("ID"):
			func_or_loc = self.tokens[self.current - 1].value
			if self.match("LPAREN"):
				args = self.arguments()
				return FunctionCall(func_or_loc, args)
			else:
				return NamedLocation(func_or_loc)
		else:
			return self.location()
		
	def parameters(self):
		# parameters <- ID type (',' ID type)*
		#            /  empty
		params = []
		if self.peek() and self.peek().type != "RPAREN":  # Check if parameters are empty
			while True:
				param_name = self.consume("ID", "Se esperaba un identificador para el parámetro").value
				param_type = self.consume("TYPE", "Se esperaba un tipo para el parámetro").value
				params.append(Parameter(param_name, param_type))
				if not self.match("COMMA"):  # If no comma, break the loop
					break
		return params
		
	def arguments(self): 
		# arguments <- expression (',' expression)*
		#          / empty
		args = []
		if not self.match("RPAREN"):  # Check if arguments are empty
			while True:
				args.append(self.expression())
				if not self.match("COMMA"):  # If no comma, break the loop
					break
			self.consume("RPAREN", "Se esperaba ')' después de los argumentos")
		return args
	
	def location(self):
		# location <- ID
		#          /  '`' expression
		if self.match("ID"):
			return NamedLocation(self.tokens[self.current - 1].value)
		elif self.match("DEREF"):
			if self.peek() and self.peek().type == "LPAREN":
				self.consume("LPAREN", "Se esperaba '(' después de la expresión")
				expr = self.expression()
				self.consume("RPAREN", "Se esperaba ')' después de la expresión")
			else:
				expr = NamedLocation(self.consume("ID", "Se esperaba un identificador después de '`'").value)
			return MemoryLocation(expr)
		else:
			print(f"ERROR: {self.peek()}")
			raise SystemExit(f"Se esperaba un identificador o una expresión entre paréntesis")

	# -------------------------------
	# Trate de conservar este codigo
	# -------------------------------

	def peek(self) -> Token:
		return self.tokens[self.current] if self.current < len(self.tokens) else None
		
	def advance(self) -> Token:
		token = self.peek()
		self.current += 1
		return token
		
	def match(self, token_type: str) -> bool:
		token = self.peek()
		if token and token.type == token_type:
			self.advance()
			return True
		return False
		
	def consume(self, token_type: str, message: str):
		if self.match(token_type):
			return self.tokens[self.current - 1]
		print(f"ERROR: {message}, se encontro: Token {self.peek()}")
		raise SystemExit()

# Convertir el AST a una representación JSON para mejor visualización
import json
class ASTSerializer:
	@staticmethod
	def ast_to_dict(node):
		if isinstance(node, list):
			return [ASTSerializer.ast_to_dict(item) for item in node]
		elif hasattr(node, "__dict__"):
			return {key: ASTSerializer.ast_to_dict(value) for key, value in node.__dict__.items()}
		else:
			return node

	@staticmethod
	def save_ast_to_json(ast, file_path="ast_updated.json"):
		ast_json = json.dumps(ASTSerializer.ast_to_dict(ast), indent=4)
		with open(file_path, "w", encoding="utf-8") as f:
			f.write(ast_json)
		return file_path

