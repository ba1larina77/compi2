# typesys.py

typenames = { 'int', 'float', 'char', 'bool' }

# Capabilities
bin_ops = {
	# Integer operations
	('int', '+', 'int') : 'int',
	('int', '-', 'int') : 'int',
	('int', '*', 'int') : 'int',
	('int', '/', 'int') : 'int',

	('int', '<', 'int')  : 'bool',
	('int', '<=', 'int') : 'bool',
	('int', '>', 'int')  : 'bool',
	('int', '>=', 'int') : 'bool',
	('int', '==', 'int') : 'bool',
	('int', '!=', 'int') : 'bool',

	# Assignment operations
	('int', '=', 'int') : 'int',
	('float', '=', 'float') : 'float',
	('char', '=', 'char') : 'char',
	('bool', '=', 'bool') : 'bool',

	# Float operations
	('float', '+', 'float') : 'float',
	('float', '-', 'float') : 'float',
	('float', '*', 'float') : 'float',
	('float', '/', 'float') : 'float',

	('float', '<', 'float')  : 'bool',
	('float', '<=', 'float') : 'bool',
	('float', '>', 'float')  : 'bool',
	('float', '>=', 'float') : 'bool',
	('float', '==', 'float') : 'bool',
	('float', '!=', 'float') : 'bool',
	# Bools
	('bool', '&&', 'bool') : 'bool',
	('bool', '||', 'bool') : 'bool',
	('bool', '==', 'bool') : 'bool',
	('bool', '!=', 'bool') : 'bool',

	# Char
	('char', '<', 'char')  : 'bool',
	('char', '<=', 'char') : 'bool',
	('char', '>', 'char')  : 'bool',
	('char', '>=', 'char') : 'bool',
	('char', '==', 'char') : 'bool',
	('char', '!=', 'char') : 'bool',
}

# Check if a binary operator is supported. Returns the
# result type or None (if not supported). Type checker
# uses this function.

def check_binop(op, left_type, right_type):
	return bin_ops.get((left_type, op, right_type))

unary_ops = {
	('+', 'int') : 'int',
	('-', 'int') : 'int',
	('^', 'int') : 'int',
    
	('+', 'float') : 'float',
	('-', 'float') : 'float',

	('!', 'bool') : 'bool',
}

def check_unaryop(op, operand_type):
	return unary_ops.get((op, operand_type))

