# symtab.py
from rich.table   import Table
from rich.console import Console
from rich         import print

class Symtab:
	'''
	Una tabla de símbolos.  Este es un objeto simple que sólo
	mantiene una hashtable (dict) de nombres de simbolos y los
	nodos de declaracion o definición de funciones a los que se
	refieren.
	Hay una tabla de simbolos separada para cada elemento de
	código que tiene su propio contexto (por ejemplo cada función,
	clase, tendra su propia tabla de simbolos). Como resultado,
	las tablas de simbolos se pueden anidar si los elementos de
	código estan anidados y las búsquedas de las tablas de
	simbolos se repetirán hacia arriba a través de los padres
	para representar las reglas de alcance léxico.
	'''
	class SymbolDefinedError(Exception):
		'''
		Se genera una excepción cuando el código intenta agregar
		un simbol a una tabla donde el simbol ya se ha definido.
		Tenga en cuenta que 'definido' se usa aquí en el sentido
		del lenguaje C, es decir, 'se ha asignado espacio para el
		simbol', en lugar de una declaración.
		'''
		def __init__(self, message="Symbol already defined in the table."):
			super().__init__(message)
		
	class SymbolConflictError(Exception):
		'''
		Se produce una excepción cuando el código intenta agregar
		un símbolo a una tabla donde el símbolo ya existe y su tipo
		difiere del existente previamente.
		'''
		def __init__(self, message="Symbol type conflict in the table."):
			super().__init__(message)
		
	def __init__(self, name, parent=None, owner=None):
		'''
		Crea una tabla de símbolos vacia con la tabla de
		simbolos padre dada.
		'''
		self.owner = owner
		self.name = name
		self.entries = {}
		self.parent = parent
		if self.parent:
			self.parent.children.append(self)
		self.children = []
		
	def add(self, name, value):
		'''
		Agrega un simbol con el valor dado a la tabla de simbolos.
		El valor suele ser un nodo AST que representa la declaración
		o definición de una función, variable (por ejemplo, Declaración
		o FuncDeclaration)
		'''
		if name in self.entries:
			if self.entries[name].dtype != value.dtype:
				raise Symtab.SymbolConflictError()
			else:
				raise Symtab.SymbolDefinedError()
		self.entries[name] = value
		
	def get(self, name):
		'''
		Recupera el símbol con el nombre dado de la tabla de
		simbol, recorriendo hacia arriba a traves de las tablas
		de simbol principales si no se encuentra en la actual.
		'''
		if name in self.entries:
			return self.entries[name]
		elif self.parent:
			return self.parent.get(name)
		return None
		
	def print(self):
		table = Table(title = f"Symbol Table: '{self.name}'")
		table.add_column('key', style='cyan')
		table.add_column('value', style='bright_green')
		
		for k,v in self.entries.items():
			value = f"{v.__class__.__name__}({k})"
			table.add_row(k, value)
		if len(self.entries)>0:print(table, '\n')
		
		for child in self.children:
			child.print()

	def save_to_text_file(self, file_path):
		"""
		Guarda la representación de la tabla de símbolos en un archivo de texto
		"""
		with open(file_path, 'w', encoding='utf-8') as f:
			console = Console(file=f, width=120, legacy_windows=False)
			self._print_to_console(console)

	def _print_to_console(self, console):
		"""
		Método auxiliar para imprimir usando un console específico
		"""
		table = Table(title=f"Symbol Table: '{self.name}'")
		table.add_column('key', style='cyan')
		table.add_column('value', style='bright_green')
		
		for k, v in self.entries.items():
			value = f"{v.__class__.__name__}({k})"
			table.add_row(k, value)
		
		if len(self.entries) > 0:
			console.print(table)
			console.print()  # Línea en blanco
		
		for child in self.children:
			child._print_to_console(console)

	def to_dict(self):
		'''
		Convierte la tabla de símbolos a un diccionario serializable para JSON
		'''
		result = {
			'name': self.name,
			'owner': self.owner.__class__.__name__ if self.owner else None,
			'entries': {},
			'children': []
		}

		# Convertir las entradas
		for k, v in self.entries.items():
			entry_info = {
				'type': v.__class__.__name__,
				'name': k
			}
			
			# Agregar información específica según el tipo
			if hasattr(v, 'type'):
				entry_info['data_type'] = v.type
			if hasattr(v, 'is_const'):
				entry_info['is_const'] = v.is_const
			if hasattr(v, 'func_type'):
				entry_info['func_type'] = v.func_type
			if hasattr(v, 'params'):
				entry_info['params'] = [{'name': p.name, 'type': p.type} for p in v.params]
			if hasattr(v, 'value') and v.value is not None:
				entry_info['value'] = str(v.value)
				
			result['entries'][k] = entry_info

		# Convertir las tablas hijas recursivamente
		for child in self.children:
			result['children'].append(child.to_dict())

		return result

