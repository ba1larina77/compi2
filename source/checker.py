# check.py

from rich    import print
from typing  import Union
from functools import singledispatchmethod
from source.model   import *
from source.symtab  import Symtab
from source.typesys import typenames, check_binop, check_unaryop
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

class Checker():
	def __init__(self):
		self.hasErrors = False
		self.debug = CONFIG.get("Debug", False)
		self.createOutputFile = CONFIG.get("GenerateOutputFile", False)

	@classmethod
	def check(cls, n:Node, fileName:str):
		'''
		1. Crear una nueva tabla de simbolos
		2. Visitar todas las declaraciones
		'''
		check = cls()
		check.fileName = fileName
		if check.debug:
			print(f"[bold green][DEBUG][/bold green] Iniciando análisis semántico del archivo '{fileName}'.")
		env = Symtab("")
		n.accept(check, env)  # No es necesario pasar la lista de errores
		if check.hasErrors:
			raise SyntaxError("Errores semánticos encontrados!!")
		else:
			if check.debug:
				print(f"[bold green][DEBUG][/bold green] Análisis semántico completado sin errores.")
			if check.createOutputFile:
				output_file_json = os.path.join(os.path.dirname(__file__), '..', 'output',f"{fileName}", f"{fileName}_symtab.json")
				output_file = os.path.join(os.path.dirname(__file__), '..', 'output',f"{fileName}", f"{fileName}_symtab.txt")
				env.save_to_text_file(output_file)
				with open(output_file_json, 'w') as f:
					json.dump(env.to_dict(), f, indent=4)
				print(f"[bold blue][OUTPUT][/bold blue] Tabla de símbolos guardada en: {output_file_json}")
			return env

	@singledispatchmethod
	def visit(self, n, env):
		print(f"Error: Tipo de nodo inesperado: {type(n).__name__}")
	
	@visit.register
	def _(self, n: Program, env:Symtab):
		'''
		1. recorrer la lista de elementos
		'''
		#print(f"Visitando nodo Program con {len(n.stmts)} declaraciones")
		for stmt in n.stmts:
			stmt.accept(self, env)

	# Statements

	@visit.register
	def _(self, n:Assignment, env:Symtab):
		'''
		1. Validar n.loc
		2. Visitar n.expr
		3. Verificar si son tipos compatibles
		'''
		if isinstance(n.location, MemoryLocation):
			# n.location es un nodo MemoryLocation.
			# n.location.accept(self, env) ahora:
			#  1. Valida que n.location.expr (la dirección) sea 'int'.
			#  2. Establece n.location.type = 'int' (tipo del dato en memoria).
			#  3. Retorna 'int' (el tipo del dato en memoria).
			tipo_del_dato_en_memoria = n.location.accept(self, env)

			# Si hubo un error al procesar n.location (ej. la dirección no era 'int')
			if self.hasErrors:
				return # Detener la verificación para esta asignación
			tipo_rhs_expresion = n.expression.accept(self, env)
			if tipo_del_dato_en_memoria == 'void':
				tipo_del_dato_en_memoria = tipo_rhs_expresion
				n.location.type = tipo_rhs_expresion  # Asignar el tipo del dato en memoria

			# Verificar compatibilidad para la asignación: tipo_del_dato_en_memoria = tipo_rhs_expresion
			# Por ejemplo, si tipo_del_dato_en_memoria es 'int', entonces 'int' = tipo_rhs_expresion
			tipo_asignacion_resultante = check_binop('=', tipo_del_dato_en_memoria, tipo_rhs_expresion) #

			if tipo_asignacion_resultante is None:
				print(f"Error: Incompatibilidad de tipos en la asignación a la ubicación de memoria. Se esperaba poder asignar un '{tipo_rhs_expresion}' a una ubicación de tipo '{tipo_del_dato_en_memoria}'.")
				self.hasErrors = True
				return # O retornar un tipo de error
			# El tipo de una expresión de asignación suele ser el tipo del valor asignado,
			# o 'void' si las asignaciones no son expresiones.
			return tipo_asignacion_resultante
		# --- Caso para NamedLocation (variables normales) ---
		# (Tu lógica existente para NamedLocation)
		elif isinstance(n.location, NamedLocation):
			loc_symbol = env.get(n.location.name) #
			if not loc_symbol:
				print(f"Error: Variable '{n.location.name}' no definida.")
				self.hasErrors = True
				return # O tipo de error
			if isinstance(loc_symbol, Variable) and loc_symbol.is_const: #
				print(f"Error: La variable '{n.location.name}' es constante (de solo lectura) y no se puede modificar.")
				self.hasErrors = True
				return
			tipo_lhs_variable = loc_symbol.type #
			tipo_rhs_expresion = n.expression.accept(self, env) #
			tipo_asignacion_resultante = check_binop('=', tipo_lhs_variable, tipo_rhs_expresion) #
			if tipo_asignacion_resultante is None:
				line_info = f"en la línea {n.lineno}" if hasattr(n, 'lineno') else ""
				print(f"Error: Incompatibilidad de tipos en la asignación a la variable '{n.location.name}' {line_info}. Se esperaba '{tipo_lhs_variable}', pero se intentó asignar un valor de tipo '{tipo_rhs_expresion}'.")
				self.hasErrors = True
				return
			return tipo_asignacion_resultante
		else:
			# Manejar otros tipos de location si existieran
			print(f"Error: Tipo de 'location' desconocido en la asignación: {type(n.location).__name__}")
			self.hasErrors = True
			return

	@visit.register
	def _(self, n:Print, env:Symtab):
		'''
		1. visitar n.expr
		2. validar el tipo de n.expr
		'''
		expr_type = n.expr.accept(self, env)
		if isinstance(n.expr, MemoryLocation):
			expr_type = 'int'
			n.expr.type = 'int'  # Asignar el tipo de la dereferencia
		if expr_type not in typenames:
			print(f"Error: Tipo inválido para la declaración print: {expr_type}")
			self.hasErrors = True
			return

	@visit.register
	def _(self, n:If, env:Symtab):
		'''
		1. Visitar n.test (validar tipos)
		2. Crear una nueva TS para n.then y visitar Statement por n.then
		3. Si existe opcion n.else_, crear una nueva TS y visitar
		'''
		# Validate the condition type
		condition_type = n.condition.accept(self, env)
		if condition_type != 'bool':
			print(f"Error: La condición en la declaración if debe ser de tipo 'bool', se obtuvo '{condition_type}'")
			self.hasErrors = True
			return
		# Create a new symbol table for the 'then' block and visit it
		then_env = Symtab(env.name+"_if_then", env, n)
		for stmt in n.if_statements:
			stmt.accept(self, then_env)
		# If there is an 'else' block, create a new symbol table and visit it
		if n.else_statements:
			else_env = Symtab(env.name+"_if_else", env, n)
			for stmt in n.else_statements:
				stmt.accept(self, else_env)
			
	@visit.register
	def _(self, n:While, env:Symtab):
		'''
		1. Visitar n.test (validar tipos)
		2. visitar n.body
		'''
		# Validate the condition type
		condition_type = n.condition.accept(self, env)
		if condition_type != 'bool':
			print(f"Error: La condición en la declaración while debe ser de tipo 'bool', se obtuvo '{condition_type}'")
			self.hasErrors = True
			return

		# Create a new symbol table for the 'while' body and visit it
		body_env = Symtab(env.name+"_while_body", env, n)
		for stmt in n.statements:
			stmt.accept(self, body_env)
		
	@visit.register
	def _(self, n:Union[Break, Continue], env:Symtab):
		'''
		1. Verificar que esta dentro de un ciclo while
		'''
		current_env = env
		in_loop = False
		while current_env:
			# Verificar si el 'owner' de algún entorno padre es un nodo While
			if current_env.owner and isinstance(current_env.owner, While):
				in_loop = True
				break
			current_env = current_env.parent
		
		if not in_loop:
			op_name = type(n).__name__.lower()
			print(f"Error: La declaración '{type(n).__name__.lower()}' debe estar dentro de un ciclo 'while'.")
			self.hasErrors = True
		return # break/continue no tienen tipo

	@visit.register
	def _(self, n:Return, env:Symtab):
		'''
		1. Si se ha definido n.expr, validar que sea del mismo tipo de la función
		'''
		# Find the function scope
		current_env = env
		while current_env and not isinstance(current_env.owner, Function):
			current_env = current_env.parent
		if not current_env or not isinstance(current_env.owner, Function):
			print("Error: La declaración 'return' debe estar dentro de una función.")
			self.hasErrors = True
			return
		func = current_env.owner
		# If the return expression exists, validate its type
		if n.expr:
			return_type = n.expr.accept(self, env)
			if return_type != func.func_type:
				print(f"Error: Incompatibilidad de tipos en 'return': se esperaba '{func.func_type}', se obtuvo '{return_type}'.")
				self.hasErrors = True
				return

		env.add("return", n)  # Add the return statement to the function's return list

	# Declarations
	@visit.register
	def _(self, n:Variable, env:Symtab):
		'''
		1. Agregar n.name a la TS actual
		'''
		if env.get(n.name):
			print(f"Error: La variable '{n.name}' ya está definida.")
			self.hasErrors = True
			return
		if n.value:
			value_type = n.value.accept(self, env)
			if isinstance(n.value, MemoryLocation) and n.value.type == 'void':
				value_type = n.type
				n.value.type = value_type
			if n.type and n.type != value_type:
				print(f"Error: Incompatibilidad de tipos para la variable '{n.name}': se esperaba {n.type}, se obtuvo {value_type}")
				self.hasErrors = True
				return
			n.type = value_type
		env.add(n.name, n)
		
	@visit.register
	def _(self, n:Function, env:Symtab):
		'''
		1. Guardar la función en la TS actual
		2. Crear una nueva TS para la función
		3. Agregar todos los n.params dentro de la TS
		4. Visitar n.stmts
		5. Verificar que haya un return en cada camino posible
		'''
		if env.get(n.name):
			print(f"Error: Funcion '{n.name}' ya esta definida.")
			self.hasErrors = True
			return
		# Ensure the function is not defined inside another function
		if env.owner != None:
			print(f"Error: La función '{n.name}' no puede definirse dentro de otra función.")
			self.hasErrors = True
			return
		env.add(n.name, n)
		func_env = Symtab(n.name, env, n)
		for param in n.params:
			param.accept(self, func_env)
		for stmt in n.statements:
			stmt.accept(self, func_env)
		# Check if the function has a return statement in all possible paths
		if n.func_type and not self.has_return_in_all_paths(n.statements) and not n.imported:
			print(f"Error: La función '{n.name}' debe tener una declaración 'return' en todos los caminos posibles o ser de tipo 'void'.")
			self.hasErrors = True
			return

	def has_return_in_all_paths(self, statements):
		'''
		Verifica si hay una declaración de retorno en todos los caminos posibles.
		'''
		for stmt in statements:
			if isinstance(stmt, Return):
				return True
			elif isinstance(stmt, If):
				then_has_return = self.has_return_in_all_paths(stmt.if_statements)
				else_has_return = self.has_return_in_all_paths(stmt.else_statements) if stmt.else_statements else False
				if then_has_return and else_has_return:
					return True
			elif isinstance(stmt, While):
				# Loops may not always guarantee a return, so skip them
				continue
		return False

	@visit.register
	def _(self, n:Parameter, env:Symtab):
		'''
		1. Guardar el parametro (name, type) en TS
		'''
		if env.get(n.name):
			print(f"Error: El parámetro '{n.name}' ya está definido en este ámbito.")
			self.hasErrors = True
			return
		env.add(n.name, n)
		
	# Expressions

	@visit.register
	def _(self, n:Literal, env:Symtab):
		'''
		1. Retornar el tipo de la literal
		'''
		pass

	@visit.register
	def _(self, n:BinOp, env:Symtab):
		'''
		1. visitar n.left y luego n.right
		2. Verificar compatibilidad de tipos
		'''
		type1 = n.left.accept(self, env)
		type2 = n.right.accept(self, env)
		# Caso de memoria, dolor de cabeza
		if isinstance(n.left, MemoryLocation):
			type1 = type2
			n.left.type = type2  # Asignar el tipo de la dereferencia
		if isinstance(n.right, MemoryLocation):
			type2 = type1
			n.right.type = type1
		expr_type = check_binop(n.operator, type1, type2)
		if expr_type is None:
			print(f"Error: Operador '{n.operator}' no es válido para los tipos '{type1}' y '{type2}'")
			self.hasErrors = True
			return
		return expr_type

	@visit.register
	def _(self, n:UnaryOp, env:Symtab):
		'''
		1. visitar n.expr
		2. validar si es un operador unario valido
		'''
		type1 = n.operand.accept(self, env)
		expr_type = check_unaryop(n.operator, type1)
		if expr_type is None:
			print(f"Error: Operador unario '{n.operator}' no es válido para el tipo '{type1}'")
			self.hasErrors = True
			return
		return expr_type
	
	@visit.register
	def _(self, n:TypeCast, env:Symtab):
		'''
		1. Visitar n.expr para validar
		2. retornar el tipo del cast n.type
		'''
		expr_type = n.expr.accept(self, env)
		if expr_type not in typenames:
			print(f"Error: Tipo inválido para el cast: '{expr_type}'")
			self.hasErrors = True
			return
		if n.cast_type not in typenames:
			print(f"Error: Tipo de destino inválido para el cast: '{n.type}'")
			self.hasErrors = True
			return
		# Optionally, you can add rules to restrict certain casts
		return n.cast_type

	@visit.register
	def _(self, n:FunctionCall, env:Symtab):
		'''
		1. Validar si n.name existe
		2. visitar n.args (si estan definidos)
		3. verificar que len(n.args) == len(func.params)
		4. verificar que cada arg sea compatible con cada param de la función
		'''
		# Validate if the function exists in the symbol table
		func = env.get(n.name)
		if not func or not isinstance(func, Function):
			print(f"Error: La función '{n.name}' no está definida.")
			self.hasErrors = True
			return
		# Check if the number of arguments matches the number of parameters
		if len(n.args) != len(func.params):
			print(f"Error: La función '{n.name}' esperaba {len(func.params)} argumentos, pero se recibieron {len(n.args)}.")
			self.hasErrors = True
			return
		# Validate each argument against the corresponding parameter
		for arg, param in zip(n.args, func.params):
			arg_type = arg.accept(self, env)
			if arg_type != param.type:
				print(f"Error: Incompatibilidad de tipos en la llamada a la función '{n.name}': se esperaba '{param.type}', se obtuvo '{arg_type}'.")
				self.hasErrors = True
				return

		# Return the return type of the function
		return func.func_type

	@visit.register
	def _(self, n:NamedLocation, env:Symtab):
		'''
		1. Verificar si n.name existe en TS y obtener el tipo
		2. Retornar el tipo
		'''
		symbol = env.get(n.name)
		if not symbol:
			print(f"Error: La variable '{n.name}' no está definida.")
			self.hasErrors = True
			return
		return symbol.type

	@visit.register
	def _(self, n:MemoryLocation, env:Symtab):
		'''
		1. Visitar n.expr (la expresión que calcula la dirección) para validar que sea 'int'.
		2. Establecer n.type (el tipo del dato *en* la dirección de memoria).
		3. Retornar n.type.
		'''
		# Visitar la expresión que calcula la dirección (ej. 'base' o 'base + i')
		# El tipo resultante de esta expresión debe ser 'int' (una dirección).
		tipo_de_la_expresion_direccion = n.expr.accept(self, env)

		if tipo_de_la_expresion_direccion != 'int':
			print(f"Error: La expresión para una dirección de memoria (dentro de '` `') debe ser de tipo 'int', pero se obtuvo '{tipo_de_la_expresion_direccion}'.")
			self.hasErrors = True
			return 

		# Asignar el tipo del dato EN la dirección de memoria.
		n.type = 'void'  
		# Retornar el tipo del dato al que se accede (el tipo de la dereferencia).
		return n.type

	@visit.register
	def _(self, n:Char, env:Symtab):
		'''
		1. Retornar el tipo de la literal Char
		'''
		return 'char'

	@visit.register
	def _(self, n:Integer, env:Symtab):
		'''
		1. Retornar el tipo de la literal Integer
		'''
		return 'int'

	@visit.register
	def _(self, n:Bool, env:Symtab):
		'''
		1. Retornar el tipo de la literal Bool
		'''
		return 'bool'

	@visit.register
	def _(self, n:Float, env:Symtab):
		'''
		1. Retornar el tipo de la literal Float
		'''
		return 'float'

def main():
	import sys
	from parser import parse  # Assuming you have a parser that generates the AST
	if len(sys.argv) != 2:
		print('Uso: python3 check.py <archivo>')
		sys.exit(1)
	file = sys.argv[1]
	# Parse the file and wrap the AST in a Program node
	ast_data = parse(file)
	program = Program(ast_data)  # Ensure ast_data is passed as a list of statements
	try:
		systab = Checker.check(program)  # Perform semantic checks
		systab.print()  # Print the symbol table
		print("El programa es semánticamente correcto.")
	except Exception as e:
		print(f"Error semántico: {e}")

def debug():
	from parser import parse 
	file = "Tests/mandelplot.gox"
	ast_data = parse(file)# Parse the file and wrap the AST in a Program node
	program = Program(ast_data)
	print(program)
	try:
		systab = Checker.check(program)  # Perform semantic checks
		systab.print()  # Print the symbol table
		print("El programa es semánticamente correcto.")
	except Exception as e:
		print(f"Error semántico: {e}")

