
from rich   import print
from typing import List, Union
from functools import singledispatchmethod
from source.model  import *
from source.symtab import Symtab
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
# Todo el código IR se empaquetará en un módulo. Un 
# módulo es un conjunto de funciones.

class IRModule:
	def __init__(self):
		self.functions = { }       # Dict de funciones IR 
		self.globals = { }         # Dict de variables global
		
	def dump(self):
		print("MODULE:::")
		for glob in self.globals.values():
			glob.dump()
			
		for func in self.functions.values():
			func.dump()
			
# Variables Globales
class IRGlobal:
	def __init__(self, name, ir_type, gox_type=None):
		self.name = name
		self.type = ir_type      # Tipo IR
		self.gox_type = gox_type # Tipo GoxLang original
		
	def dump(self):
		print(f"GLOBAL::: {self.name}: {self.type}")

# Las funciones sirven como contenedor de las 
# instrucciones IR de bajo nivel específicas de cada
# función. También incluyen metadatos como el nombre 
# de la función, los parámetros y el tipo de retorno.

class IRFunction:
	def __init__(self, module, name, parmnames, parmtypes, return_type, return_type_gox, imported=False):
		# Agreguemos la lista de funciones del módulo adjunto
		self.module = module
		module.functions[name] = self
		
		self.name = name
		self.parmnames = parmnames
		self.parmtypes = parmtypes
		self.return_type = return_type
		self.return_type_gox = return_type_gox
		self.imported = imported
		self.locals = { }        # Variables Locales (tipo IR)
		self.locals_gox = { }    # Tipos GoxLang originales
		self.code = [ ]          # Lista de Instrucciones IR 
		
	def new_local(self, name, ir_type, gox_type=None):
		self.locals[name] = ir_type
		if gox_type:
			self.locals_gox[name] = gox_type
		
	def append(self, instr):
		self.code.append(instr)
		
	def extend(self, instructions):
		self.code.extend(instructions)
		
	def dump(self):
		print(f"FUNCTION::: {self.name}, {self.parmnames}, {self.parmtypes} {self.return_type}")
		print(f"locals: {self.locals}")
		for instr in self.code:
			print(instr)
			
# Mapeo de tipos de GoxLang a tipos de IR
_typemap = {
	'int'  : 'I',
	'float': 'F',
	'bool' : 'I',
	'char' : 'I',
}

# Generar un nombre de variable temporal único
def new_temp(n=[0]):
	n[0] += 1
	return f'$temp{n[0]}'

# Una función de nivel superior que comenzará a generar IRCode

class IRCode(Visitor):
	INT_SIZE = CONFIG.get("IntSize", 4)  # Tamaño de un entero en bytes
	FLOAT_SIZE = CONFIG.get("FloatSize", 4)  # Tamaño de un flotante en bytes
	CHAR_SIZE = CONFIG.get("CharSize", 1)  # Tamaño de un carácter en bytes
	_binop_code = {
		('int', '+', 'int')  : 'ADDI',
		('int', '-', 'int')  : 'SUBI',
		('int', '*', 'int')  : 'MULI',
		('int', '/', 'int')  : 'DIVI',
		('int', '<', 'int')  : 'LTI',
		('int', '<=', 'int') : 'LEI',
		('int', '>', 'int')  : 'GTI',
		('int', '>=', 'int') : 'GEI',
		('int', '==', 'int') : 'EQI',
		('int', '!=', 'int') : 'NEI',
		
		('float', '+',  'float') : 'ADDF',
		('float', '-',  'float') : 'SUBF',
		('float', '*',  'float') : 'MULF',
		('float', '/',  'float') : 'DIVF',
		('float', '<',  'float') : 'LTF',
		('float', '<=', 'float') : 'LEF',
		('float', '>',  'float') : 'GTF',
		('float', '>=', 'float') : 'GEF',
		('float', '==', 'float') : 'EQF',
		('float', '!=', 'float') : 'NEF',
		
		('char', '<', 'char')  : 'LTI',
		('char', '<=', 'char') : 'LEI',
		('char', '>', 'char')  : 'GTI',
		('char', '>=', 'char') : 'GEI',
		('char', '==', 'char') : 'EQI',
		('char', '!=', 'char') : 'NEI',
	}
	_unaryop_code = {
		('+', 'int')   : [],
		('+', 'float') : [],
		('-', 'int')   : [('CONSTI', -1), ('MULI',)],
		('-', 'float') : [('CONSTF', -1.0), ('MULF',)],
		('!', 'bool') : [('CONSTI', 0), ('EQI',)],
		('^', 'int')   : [ ('GROW',) ]
	}
	_typecast_code = {
		# (from, to) : [ ops ]
		('int', 'float') : [ ('ITOF',) ],
		('float', 'int') : [ ('FTOI',) ],
	}

	@classmethod
	def gencode(cls, node:List[Statement], fileName:str):
		'''
		El nodo es el nodo superior del árbol de 
		modelo/análisis.
		La función inicial se llama "_init". No acepta 
		argumentos. Devuelve un entero.
		'''
		ircode = cls()
		ircode.debug = CONFIG.get("Debug", False)
		ircode.createOutputFile = CONFIG.get("GenerateOutputFile", False)
		ircode.module = IRModule()

		func = IRFunction(ircode.module, 'main', [], [], 'I', 'int')
		# Then process statements in main function
		if ircode.debug:
			print(f"[bold green][DEBUG][/bold green] Iniciando generacion de codigo intermedio del archivo: {fileName}")
		for item in node:
			item.accept(ircode, func)
		if '_actual_main' in ircode.module.functions:
			func.append(('CALL', '_actual_main'))
		else:
			func.append(('CONSTI', 0))
		func.append(('RET',))
		if ircode.debug:
			print(f"[bold green][DEBUG][/bold green] Generacion de codigo intermedio finalizada con {len(func.code)} instrucciones")
		if ircode.createOutputFile:
			# Guardar el código IR en un archivo
			output_file = os.path.join(os.path.dirname(__file__), '..', 'output',f'{fileName}', f'{fileName}.ir')
			with open(output_file, 'w') as f:
				# Write MODULE header
				f.write("MODULE:::\n")
				# Write globals
				for glob in ircode.module.globals.values():
					f.write(f"GLOBAL::: {glob.name}: {glob.type}\n")
				# Write functions
				for func_obj in ircode.module.functions.values():
					f.write(f"FUNCTION::: {func_obj.name}, {func_obj.parmnames}, {func_obj.parmtypes} {func_obj.return_type}\n")
					f.write(f"locals: {func_obj.locals}\n")
					for instr in func_obj.code:
						f.write(f"{instr}\n")
			print(f"[bold blue][OUTPUT][/bold blue] Código IR guardado en: {output_file}")
		return ircode.module

	# --- Statements
	@singledispatchmethod
	def visit(self, n, func):
		# Si no se encuentra un nodo, se lanza una excepción
		raise Exception(f"Error: No se puede visitar el nodo {n.__class__.__name__} en IRCode")
	
	@visit.register
	def _(self, n: Assignment, func: IRFunction):
		# Visitar n.expr
		# Visitar n.loc (tener en cuenta set/get)
		n.location.usage = 'store'
		n.expression.usage = 'load'
		n.location.store_value = n.expression
		n.location.accept(self, func)
	
	@visit.register
	def _(self, n: Print, func: IRFunction):
		type = n.expr.accept(self, func)
		if type == 'int' or type in ['bool','true', 'false']:
			func.append(('PRINTI',))
		elif type == 'float':
			func.append(('PRINTF',))
		elif type == 'char':
			func.append(('PRINTB',))

	@visit.register
	def _(self, n: If, func: IRFunction):
		# Visitar n.condition
		n.condition.accept(self, func)
		func.append(('IF',))
		# Procesar las instrucciones en la parte de la consecuencia (then)
		for stmt in n.if_statements:
			stmt.accept(self, func)
		func.append(('ELSE',))
		# Procesar las instrucciones en la parte alternativa (else)
		for stmt in n.else_statements:
			stmt.accept(self, func)
		func.append(('ENDIF',))

	@visit.register
	def _(self, n: While, func: IRFunction):
		func.append(('LOOP',))
		func.append(('CONSTI', 1))
		# Visitar n.test
		n.condition.accept(self, func)
		func.append(('SUBI',))
		func.append(('CBREAK',))
		# Visitar n.body
		for stmt in n.statements:
			stmt.accept(self, func)
		func.append(('ENDLOOP',))

	@visit.register
	def _(self, n: Break, func: IRFunction):
		func.append(('CONSTI', 1))
		func.append(('CBREAK',))

	@visit.register
	def _(self, n: Continue, func: IRFunction):
		func.append(('CONTINUE',))

	@visit.register
	def _(self, n: Return, func: IRFunction):
		# First visit the return expression to push its value onto the stack
		if n.expr:
			n.expr.accept(self, func)
		else:
			# If there's no return expression, push a default value (0)
			func.append(('CONSTI', 0))
		# Then append the return instruction
		func.append(('RET',))

	# --- Declaration
		
	@visit.register
	def _(self, n: Variable, func: IRFunction):
		irtype = _typemap.get(n.type, 'I')
		if func.name == 'main':  # Variables globales
			self.module.globals[n.name] = IRGlobal(n.name, irtype, n.type)
			if n.value:
				n.value.accept(self, func)
				func.append(('GLOBAL_SET', n.name))
			return
		func.new_local(n.name, irtype, n.type)
		# Visit the initializer if it exists
		if n.value:
			n.value.accept(self, func)
			func.append(('LOCAL_SET', n.name))
		
	@visit.register
	def _(self, n: Function, func: IRFunction):
		'''
		Si encontramos una nueva función, tenemos que suspender la
		generación de código para la función actual "func" y crear
		una nueva función
		'''
		parmnames = [p.name for p in n.params]
		parmtypes = [_typemap[p.type] for p in n.params]
		rettype   = _typemap.get(n.func_type, 'int') if n.func_type else 'I'

		if n.name == 'main':
			name = '_actual_main'
		else:
			name = n.name
		
		newfunc = IRFunction(
			func.module,
			name,
			parmnames,
			parmtypes,
			rettype,
			n.func_type,
			n.imported
		)
		for p in n.params:newfunc.new_local(p.name, _typemap[p.type],p.type)
		if not n.imported:
			# Visitar n.stmts
			for stmt in n.statements:
				stmt.accept(self, newfunc)
			# Verificar si la última instrucción es RET
            # Si no lo es, agregar un return por defecto
			if not newfunc.code or newfunc.code[-1][0] != 'RET':
				# Agregar valor de retorno por defecto según el tipo de retorno
				if rettype == 'I':  # int, bool, char
					newfunc.append(('CONSTI', 0))
				elif rettype == 'F':  # float
					newfunc.append(('CONSTF', 0.0))
				else:
					# Tipo desconocido, usar entero por defecto
					newfunc.append(('CONSTI', 0))
				
				newfunc.append(('RET',))
				
				if self.debug:
					print(f"[bold yellow][DEBUG_WARN][/bold yellow] Función '{name}' no tenía return explícito. Se agregó return por defecto.")
	
	# --- Expressions
	
	@visit.register
	def _(self, n: Integer, func: IRFunction):
		func.append(('CONSTI', n.value))
		return "int"

	@visit.register
	def _(self, n: Float, func: IRFunction):
		func.append(('CONSTF', n.value))
		return "float"

	@visit.register
	def _(self, n: Char, func: IRFunction):
		func.append(('CONSTI', ord(n.value)))
		#func.append(('CONSTI', ord('\\xff')))
		return "char"
		
	@visit.register
	def _(self, n: Bool, func: IRFunction):
		boolValue = 1 if n.value == "true" else 0
		func.append(('CONSTI', boolValue))
		return "bool"
	
	@visit.register
	def _(self, n: BinOp, func: IRFunction):
		if n.operator == '&&':
			# short-circuit: Si n.left es false, hasta aca llega
			n.left.accept(self, func)  # Leaves L_result on stack
			func.append(('IF',))       # Consumes L_result. If L_result is true:
			n.right.accept(self, func) # Evaluate R. Stack has R_result (value of L && R)
			func.append(('ELSE',))     # If L_result was false:
			func.append(('CONSTI', 0)) # Value of L && R is 0
			func.append(('ENDIF',))
			# Return type is bool (mapped to 'I')
			return "bool"
		
		elif n.operator == '||':
			# short-circuit: si n.left es true, hasta aca llega
			n.left.accept(self, func)  # Leaves L_result on stack
			func.append(('IF',))       # Consumes L_result. If L_result is true:
			func.append(('CONSTI', 1)) # Value of L || R is 1
			func.append(('ELSE',))     # If L_result was false:
			n.right.accept(self, func) # Evaluate R. Stack has R_result (value of L || R)
			func.append(('ENDIF',))
			# Return type is bool (mapped to 'I')
			return "bool"
		else:
			leftT = n.left.accept(self, func)
			rightT = n.right.accept(self, func)
			func.append((self._binop_code[leftT, n.operator, rightT],))
			return check_binop(n.operator, leftT, rightT)
		
	@visit.register
	def _(self, n: UnaryOp, func: IRFunction):
		# Visitar n.expr
		type = n.operand.accept(self, func)
		if n.operator == '^' and type == 'int':
			# This is our special allocation operator for an array of integers.
			# The number of elements is now on the stack.
			# Multiply it by INT_SIZE (assuming 4 bytes for an int).
			func.append(('CONSTI', 4))  # Or use a way to get self.INT_SIZE if available/consistent
			func.append(('MULI',))
			# Now the total number of bytes to allocate is on the stack.
			# Proceed to emit the GROW instruction from _unaryop_code.
			func.extend(self._unaryop_code[(n.operator, type)])
		else:
			# Original logic for other unary operators
			func.extend(self._unaryop_code[(n.operator, type)])
		return type
		
	@visit.register
	def _(self, n: TypeCast, func: IRFunction):
		# Visitar n.expr
		_type = n.expr.accept(self, func)
		if _type != n.cast_type:
			func.extend(self._typecast_code[_type, n.cast_type])
		return n.cast_type

	@visit.register
	def _(self, n: FunctionCall, func: IRFunction):
		# Visitar n.args
		arg_gox_types = []
		for arg_expr in n.args:
			arg_gox_type = arg_expr.accept(self, func) # Evalúa el argumento y deja el valor en la pila
			arg_gox_types.append(arg_gox_type)
		# 2. Emitir la instrucción CALL
		func.append(('CALL', n.name))
		# 3. Determinar el tipo de retorno GoxLang de la función
		target_func_info = self.module.functions.get(n.name)
		if not target_func_info:
			if self.debug:
				print(f"[bold yellow][DEBUG_WARN][/bold yellow] FunctionCall: No se encontró información para '{n.name}', asumiendo retorno int.")
			return 'int' # Un default peligroso
		return target_func_info.return_type_gox
	
	@visit.register
	def _(self, n: NamedLocation, func: IRFunction):
		# Determinar si la variable es global o local
		is_global = n.name in func.module.globals
		try:
			if n.usage == 'store':
				n.store_value.accept(self, func)
				# Si es una variable global, se almacena en la tabla de símbolos
				if is_global: func.append(('GLOBAL_SET', n.name))
				else: func.append(('LOCAL_SET', n.name))
				return
		except AttributeError:
			pass
		# Si no es una asignación, se carga la variable
		if is_global:
			_type = func.module.globals[n.name].gox_type
			func.append(('GLOBAL_GET', n.name))
		else:
			_type = func.locals_gox[n.name]
			func.append(('LOCAL_GET', n.name))
		# Retornar el tipo de la variable
		return _type

	@visit.register
	def _(self, n: MemoryLocation, func: IRFunction):
		# n.type DEBE ser el tipo GoxLang del *dato en la dirección de memoria*,
		# establecido por el analizador semántico/de tipos.
		# Por ejemplo, para `var x *int; ... *x`, n.type sería 'int'.
		dataType = n.type

		# --- Cálculo de Dirección (una sola vez) ---
		if isinstance(n.expr, BinOp) and n.expr.operator == '+':
			# Probable acceso a array: base + indice
			# n.expr.left es la base, n.expr.right es el índice

			# 1. Evaluar la expresión base (debería resultar en una dirección entera)
			base_addr_type = n.expr.left.accept(self, func) # Empuja la dirección base a la pila
			if base_addr_type == 'float': # Las direcciones deben ser enteras
				func.append(('FTOI',))

			# 2. Evaluar la expresión del índice
			index_val_type = n.expr.right.accept(self, func) # Empuja el valor del índice a la pila
			if index_val_type == 'float': # Los índices suelen ser enteros
				func.append(('FTOI',))

			# 3. Aplicar escalado según el tipo del elemento
			scale_factor = 1
			apply_scaling_op = False # ¿Necesitamos una operación MULI explícita?
			if dataType == 'int' or dataType == 'bool':
				scale_factor = self.INT_SIZE
				if self.INT_SIZE > 1: apply_scaling_op = True
			elif dataType == 'float':
				scale_factor = self.FLOAT_SIZE
				if self.FLOAT_SIZE > 1: apply_scaling_op = True
			elif dataType == 'char':
				scale_factor = self.CHAR_SIZE # Usualmente 1
				if self.CHAR_SIZE > 1: apply_scaling_op = True

			if apply_scaling_op:
				func.append(('CONSTI', scale_factor))
				func.append(('MULI',))          # indice_escalado = indice * factor_escala

			func.append(('ADDI',))              # direccion_final = direccion_base + indice_escalado
		else:
			# Acceso simple a puntero (ej. *p) o dirección ya calculada
			# n.expr debería evaluarse a la dirección de byte final.
			addr_val_type = n.expr.accept(self, func) # Empuja la dirección a la pila
			if addr_val_type == 'float': # La dirección debe ser entera
				func.append(('FTOI',))
		# La dirección de byte final está ahora en la cima de la pila.

		# --- Operación POKE o PEEK ---
		is_store = hasattr(n, 'usage') and n.usage == 'store'

		if is_store:
			if not hasattr(n, 'store_value'):
				raise ValueError(f"MemoryLocation en (línea {n.lineno}) usado en contexto de almacenamiento pero no tiene store_value.")

			# Evaluar el valor a almacenar. Este valor se empuja a la pila.
			# Pila: [direccion_final, valor_a_almacenar]
			val_to_store_type = n.store_value.accept(self, func)

			# Conversión de tipo implícita (simple) para el valor a almacenar.
			# Un compilador más completo insertaría nodos TypeCast explícitos.
			if dataType == 'int' and val_to_store_type == 'float':
				func.append(('FTOI',))
			elif dataType == 'float' and val_to_store_type == 'int':
				func.append(('ITOF',))
			# (char a int es usualmente implícito si el valor está en rango)

			if dataType == 'int' or dataType == 'bool':
				func.append(('POKEI',))
			elif dataType == 'float':
				func.append(('POKEF',))
			elif dataType == 'char': # Asumiendo que char se almacena como byte (int 0-255)
				func.append(('POKEB',))
			else:
				raise NotImplementedError(f"POKE para el tipo GoxLang {dataType} no implementado.")
			return dataType # Retorna el tipo GoxLang de la ubicación
		else: # Operación de carga (PEEK)
			# La dirección ya está en la pila.
			if dataType == 'int' or dataType == 'bool':
				func.append(('PEEKI',))
				return 'int' # Retorna el tipo GoxLang resultante
			elif dataType == 'float':
				func.append(('PEEKF',))
				return 'float'
			elif dataType == 'char':
				func.append(('PEEKB',))
				return 'char'
			else:
				raise NotImplementedError(f"PEEK para el tipo GoxLang {dataType} no implementado.")
