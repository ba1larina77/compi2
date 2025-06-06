

from rich import print
import json,os

def load_config():
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, '..', 'settings', 'config.json')
        if not os.path.exists(config_path): 
             config_path = os.path.join(os.path.dirname(__file__), '..', 'settings', 'config.json')
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: config.json not found (tried {config_path}), using default settings")
        return {"Debug": True, "GenerateOutputFile": False} 
    except json.JSONDecodeError:
        print(f"Warning: Invalid JSON in config.json (at {config_path}), using default settings")
        return {"Debug": True, "GenerateOutputFile": False}
    except Exception as e:
        print(f"Warning: Error loading config.json (at {config_path}): {e}, using default settings")
        return {"Debug": True, "GenerateOutputFile": False}

CONFIG = load_config()

class StackMachine:
    def __init__(self):
        self.stack = []                       
        self.memory = bytearray([0] * 1024)   
        self.globals = {}                     
        self.locals_stack = []                
        self.call_stack = []                  
        self.functions = {}                  
        self.pc = 0                          
        self.programInst = []              
        self.running = False
        self.current_function_name = None

        self.debug = CONFIG.get("Debug", True)
        self.INT_SIZE = CONFIG.get("IntSize", 4)
        self.FLOAT_SIZE = CONFIG.get("FloatSize", 4)

        self.control_flow_stack = []
        self.pc_modified_by_operation = False 


    def _log_debug(self, message, flush=False):
        if self.debug:
            print(f"[DEBUG SM]: {message}", flush=flush)

    def load_program(self, program): 
        self.pc = 0
        self.running = False 

    def load_module(self, ir_module):
        self.functions = {}
        for name, func_def in ir_module.functions.items():
            self.functions[name] = {
                'name': func_def.name,
                'params': func_def.parmnames,
                'param_types': func_def.parmtypes, 
                'code': func_def.code,
                'locals_spec': func_def.locals, 
                'locals_gox': func_def.locals_gox, 
                'return_type': func_def.return_type, 
                'return_type_gox': func_def.return_type_gox,
                'is_imported': func_def.imported
            }
        self.globals = { name: (None, ir_module.globals[name].type) for name in ir_module.globals } # Store as (value, IR_type)
        if 'main' not in self.functions:
            raise RuntimeError("No 'main' function found in IR module to start execution.")
        self._log_debug(f"Module loaded. Functions: {list(self.functions.keys())}. Globals: {list(self.globals.keys())}")

    def _initialize_execution(self):
        if not self.functions or 'main' not in self.functions:
            print("Error: Program not loaded or 'main' function is missing.")
            return False

        self.op_CALL('main', is_initial_call=True)
        return True

    def run(self):
        if not self._initialize_execution():
            return

        self.running = True
        instruction_count = 0

        max_instructions = CONFIG.get("MaxInstructions", 10 * 10000*100)  

        self._log_debug(f"--- Starting execution from '{self.current_function_name}' ---")

        while self.running:
            self._log_debug(f"TOP OF RUN LOOP: PC={self.pc}, Current Function={self.current_function_name}") 
            if self.pc < 0 or self.pc >= len(self.programInst):
                if self.current_function_name == 'main' and not self.call_stack :
                     self._log_debug(f"Execution finished: PC ({self.pc}) out of bounds for main's program instructions ({len(self.programInst)}).")
                     self.running = False
                     break
                elif not self.programInst: 
                    self._log_debug(f"Warning: Program instructions list is empty for function '{self.current_function_name}'. Attempting RET.")
                    if not self.call_stack:
                        self.running = False
                        break
                    self.op_RET() 
                    continue 
                else:
                    raise RuntimeError(f"PC ({self.pc}) out of bounds. Program length: {len(self.programInst)} for function '{self.current_function_name}'. Call Stack: {self.call_stack}")

            instr = self.programInst[self.pc]
            opname = instr[0]
            args = instr[1:] if len(instr) > 1 else []

            self._log_debug(f"PC: {self.pc}, Func: {self.current_function_name}, Instr: {opname} {args}, Stack: {self.stack}, Locals: {self.locals_stack[-1] if self.locals_stack else 'N/A'}")

            method = getattr(self, f"op_{opname}", None)
            if method:
                original_pc = self.pc
                self.pc_modified_by_operation = False 
                method(*args)
                if not self.pc_modified_by_operation:

                    if self.pc == original_pc:
                        self.pc += 1
                self._log_debug(f"END OF ITERATION: Next PC will be {self.pc}")

            else:
                raise RuntimeError(f"Unknown instruction: {opname}")

            instruction_count += 1
            if instruction_count >= max_instructions:
                self.running = False 
                print(f"Stack: {self.stack}")
                print(f"Locals: {self.locals_stack[-1] if self.locals_stack else 'N/A'}")
                print(f"Globals: {self.globals}")
                raise RuntimeError(f"Instruction limit ({max_instructions}) reached, possible infinite loop or very long program. Last instruction: {opname} {args} at PC {self.pc-1 if self.pc > 0 else 0} in {self.current_function_name}")

        self._log_debug("--- Execution halted ---")
        if self.stack:
            self._log_debug(f"Final stack (non-empty): {self.stack}")



    def _pop_int(self):
        val_type, value = self.stack.pop()
        if val_type != 'I':
            raise TypeError(f"Expected integer ('I') on stack, got {val_type}")
        return int(value)

    def _pop_float(self):
        val_type, value = self.stack.pop()
        if val_type != 'F':
            raise TypeError(f"Expected float ('F') on stack, got {val_type}")
        return float(value)

    def _pop_any(self):
        self._log_debug(f"DEBUG POP_ANY: Stack BEFORE pop: {self.stack}, id(self.stack): {id(self.stack)}")
        if not self.stack:
            self._log_debug("DEBUG POP_ANY: Stack is empty!")
            raise IndexError("Pop from empty stack")
        item = self.stack.pop()
        self._log_debug(f"DEBUG POP_ANY: Popped item: {item}, Stack AFTER pop: {self.stack}")
        return item


    def op_CONSTI(self, value):
        self.stack.append(('I', int(value)))

    def op_ADDI(self):
        b = self._pop_int()
        a = self._pop_int()
        self.stack.append(('I', a + b))

    def op_SUBI(self):
        b = self._pop_int()
        a = self._pop_int()
        self.stack.append(('I', a - b))

    def op_MULI(self):
        b = self._pop_int()
        a = self._pop_int()
        self.stack.append(('I', a * b))

    def op_DIVI(self):
        b = self._pop_int()
        a = self._pop_int()
        if b == 0:
            raise ZeroDivisionError("Integer division by zero")
        self.stack.append(('I', a // b)) 

    def op_CONSTF(self, value):
        self.stack.append(('F', float(value)))

    def op_ADDF(self):
        b = self._pop_float()
        a = self._pop_float()
        self.stack.append(('F', a + b))

    def op_SUBF(self):
        b = self._pop_float()
        a = self._pop_float()
        self.stack.append(('F', a - b))

    def op_MULF(self):
        b = self._pop_float()
        a = self._pop_float()
        self.stack.append(('F', a * b))

    def op_DIVF(self):
        b = self._pop_float()
        a = self._pop_float()
        if b == 0.0:
            raise ZeroDivisionError("Floating point division by zero")
        self.stack.append(('F', a / b))

    def op_ANDI(self): 
        b = self._pop_int()
        a = self._pop_int()
        self.stack.append(('I', a & b))

    def op_ORI(self): 
        b = self._pop_int()
        a = self._pop_int()
        self.stack.append(('I', a | b))

    def op_LTI(self):
        b = self._pop_int()
        a = self._pop_int()
        self.stack.append(('I', 1 if a < b else 0))

    def op_LEI(self):
        b = self._pop_int()
        a = self._pop_int()
        self.stack.append(('I', 1 if a <= b else 0))

    def op_GTI(self):
        b = self._pop_int()
        a = self._pop_int()
        self.stack.append(('I', 1 if a > b else 0))

    def op_GEI(self):
        b = self._pop_int()
        a = self._pop_int()
        self.stack.append(('I', 1 if a >= b else 0))

    def op_EQI(self):
        b = self._pop_int()
        a = self._pop_int()
        self.stack.append(('I', 1 if a == b else 0))

    def op_NEI(self):
        b = self._pop_int()
        a = self._pop_int()
        self.stack.append(('I', 1 if a != b else 0))

    def op_LTF(self):
        b = self._pop_float()
        a = self._pop_float()
        self.stack.append(('I', 1 if a < b else 0)) 

    def op_LEF(self):
        b = self._pop_float()
        a = self._pop_float()
        self.stack.append(('I', 1 if a <= b else 0))

    def op_GTF(self):
        b = self._pop_float()
        a = self._pop_float()
        self.stack.append(('I', 1 if a > b else 0))

    def op_GEF(self):
        b = self._pop_float()
        a = self._pop_float()
        self.stack.append(('I', 1 if a >= b else 0))

    def op_EQF(self):
        b = self._pop_float()
        a = self._pop_float()
        self.stack.append(('I', 1 if a == b else 0))

    def op_NEF(self):
        b = self._pop_float()
        a = self._pop_float()
        self.stack.append(('I', 1 if a != b else 0))


    def op_ITOF(self):
        val_type, value = self._pop_any()
        if val_type != 'I':
            raise TypeError(f"ITOF requires an integer, got {val_type}")
        self.stack.append(('F', float(value)))

    def op_FTOI(self):
        val_type, value = self._pop_any()
        if val_type != 'F':
            raise TypeError(f"FTOI requires a float, got {val_type}")
        self.stack.append(('I', int(value)))


    def op_LOCAL_GET(self, name):
        if not self.locals_stack:
            raise RuntimeError("LOCAL_GET: No local scope available.")
        current_locals = self.locals_stack[-1]
        if name not in current_locals:
            raise NameError(f"Local variable '{name}' not found in current scope.")
        value, var_type = current_locals[name]
        if value is None :
            raise ValueError(f"Local variable '{name}' accessed before assignment.")
        self.stack.append((var_type, value))

    def op_LOCAL_SET(self, name):
        if not self.locals_stack:
            raise RuntimeError("LOCAL_SET: No local scope available.")
        val_type, value = self._pop_any()
        current_locals = self.locals_stack[-1]

        current_locals[name] = (value, val_type)


    def op_GLOBAL_GET(self, name):
        if name not in self.globals:
            raise NameError(f"Global variable '{name}' not found.")
        value, var_type = self.globals[name]
        if value is None :
            raise ValueError(f"Global variable '{name}' accessed before assignment.")
        self.stack.append((var_type, value))

    def op_GLOBAL_SET(self, name):
        self._log_debug(f"DEBUG GLOBAL_SET: Called for name='{name}'. Globals BEFORE: {self.globals.get(name)}")
        val_type, value = self._pop_any()
        self.globals[name] = (value, val_type)

    def op_CALL(self, func_name, is_initial_call=False):
        if func_name not in self.functions:
            raise NameError(f"Function '{func_name}' not defined.")

        func_def = self.functions[func_name]
        if func_def['is_imported']:

            self._log_debug(f"CALL: Imported function '{func_name}' handled.")
            return

        new_locals = {}
        for local_name, local_ir_type in func_def['locals_spec'].items():
            new_locals[local_name] = (None, local_ir_type)

        for i in range(len(func_def['params']) -1, -1, -1):
            param_name = func_def['params'][i]
            if not self.stack:
                raise ValueError(f"Stack underflow when passing arguments to '{func_name}'. Expected {len(func_def['params'])} args.")
            arg_type, arg_val = self._pop_any()
            new_locals[param_name] = (arg_val, arg_type)
        
        self.locals_stack.append(new_locals)

        if not is_initial_call:

            caller_control_flow_depth = len(self.control_flow_stack)
            self.call_stack.append({
                'pc_return': self.pc + 1,
                'locals_frame_index': len(self.locals_stack) - 2, 
                'previous_function_name': self.current_function_name,
                'previous_programInst': self.programInst,
                'previous_control_flow_depth': caller_control_flow_depth 
            })
            self._log_debug(f"CALL: Pushed {self.call_stack[-1]} to call_stack.")

        self.current_function_name = func_name
        self.programInst = func_def['code']
        self.pc = 0
        self.pc_modified_by_operation = True
        self._log_debug(f"CALL: Jumping to {func_name}. New PC=0. Locals frame created. Program instructions loaded for {func_name}.")

    def op_RET(self):
        if not self.locals_stack: 
             if not (self.current_function_name == 'main' and not self.call_stack):
                 raise RuntimeError("RET: Locals stack is empty, cannot restore  (or was already popped).")
        else:
            self.locals_stack.pop()

        if not self.call_stack:
            self._log_debug(f"RET: No call stack frame. Assuming return from '{self.current_function_name_or_none()}' or initial context. Halting.")
            self.running = False
            self.pc = -1 
            self.pc_modified_by_operation = True
            self.control_flow_stack.clear() # Clear any loop contexts from main
            self._log_debug(f"RET: Cleared control_flow_stack as returning from last function. Stack: {self.control_flow_stack}")
            return


        return_frame = self.call_stack.pop()
        self.pc = return_frame['pc_return']
        self.current_function_name = return_frame['previous_function_name']
        self.programInst = return_frame['previous_programInst']
        self.pc_modified_by_operation = True 

        if 'previous_control_flow_depth' in return_frame:
            target_depth = return_frame['previous_control_flow_depth']
            if len(self.control_flow_stack) > target_depth:
                self._log_debug(f"RET: Truncating control_flow_stack from {len(self.control_flow_stack)} (top: {self.control_flow_stack[-1] if self.control_flow_stack else 'N/A'}) to depth {target_depth}.")
                self.control_flow_stack = self.control_flow_stack[:target_depth]
            # else:
                # self._log_debug(f"RET: control_flow_stack depth ({len(self.control_flow_stack)}) already at or below target caller depth ({target_depth}). No change needed.")
        else:

            self._log_debug(f"RET: Warning - 'previous_control_flow_depth' not in return_frame. control_flow_stack not explicitly truncated by this mechanism for function {self.current_function_name}.")

        self._log_debug(f"RET: Returning to {self.current_function_name} at PC {self.pc}. Locals restored. Call stack size: {len(self.call_stack)}. Control_flow_stack: {self.control_flow_stack}")
        # ... (rest of your RET logic, e.g., for halting if main was empty) ...
        if not self.programInst and self.current_function_name == 'main': # Edge case: main was empty
            self.running = False
            self.pc = -1


    def current_function_name_or_none(self):
        return self.current_function_name if self.current_function_name else "global/unknown context"


    # --- Control de flujo estructurado ---
    # These require careful management of PC.
    # The IR generator should produce labels or relative jumps.
    # For this stack machine, we'll assume jump targets are absolute PCs
    # or that IF/LOOP etc. implicitly manage blocks.
    # A common way is IF jumps to ELSE or ENDIF if false.
    # LOOP marks start, CBREAK jumps to ENDLOOP, ENDLOOP jumps to LOOP.

    # For structured IF/ELSE/ENDIF, LOOP/CBREAK/ENDLOOP, the IR usually includes
    # jump targets (labels that are resolved to PC values).
    # If the IR has ('IF_FALSE_JUMP', label_else), ('JUMP', label_endif)
    # For simplicity here, let's assume a block-based approach where the
    # StackMachine finds matching ENDIF/ENDLOOP. This is harder to do efficiently
    # without pre-calculating jump targets.

    # A simpler model for IF: if condition is false, skip to matching ELSE or ENDIF.
    # For now, IF will pop condition. If false, it will scan forward for ELSE or ENDIF.
    # This is inefficient but demonstrates the logic. A real compiler would use labels/addresses.

    # In class StackMachine:
    def op_IF(self):
        condition_type, condition_value = self._pop_any()
        if condition_type != 'I':
            raise TypeError("IF condition must be an integer (boolean).") #
        
        if condition_value == 0: # Condition is False
            nesting_level = 1
            scan_pc = self.pc + 1 # Start scanning instructions after the current IF
            
            while scan_pc < len(self.programInst):
                instr_name = self.programInst[scan_pc][0]
                if instr_name == 'IF':
                    nesting_level += 1
                elif instr_name == 'ENDIF':
                    nesting_level -= 1
                    if nesting_level == 0: 
                        # Found the ENDIF for this IF, and no ELSE was found for this IF block.
                        # This means it was an IF without an ELSE.
                        self.pc = scan_pc # Jump to the ENDIF instruction.
                        self.pc_modified_by_operation = True
                        return
                elif instr_name == 'ELSE' and nesting_level == 1:
                    # Found the ELSE that matches the current IF.
                    # Jump to the instruction *after* this ELSE instruction.
                    self.pc = scan_pc + 1 
                    self.pc_modified_by_operation = True
                    return
                scan_pc += 1
            # If the loop finishes, a matching ENDIF (or ELSE if expected) was not found.
            raise RuntimeError(f"IF(false) at PC {self.pc-1} did not find matching ELSE or ENDIF.")
        else: # Condition is True
            # Do nothing; self.pc_modified_by_operation remains False.
            # The main run() loop will increment self.pc to execute the next instruction (the true-block).
            # The ELSE instruction (if present) later on will handle skipping the else-block.
            pass

    def op_ELSE(self):
        # This instruction implies the 'IF' block was executed.
        # We need to skip to the matching ENDIF.
        nesting_level = 1
        target_pc = self.pc + 1
        while target_pc < len(self.programInst):
            instr_name = self.programInst[target_pc][0]
            if instr_name == 'IF': # Should not happen if IFs are properly nested with ELSE
                nesting_level +=1
            elif instr_name == 'ENDIF':
                nesting_level -= 1
                if nesting_level == 0:
                    self.pc = target_pc # Will be incremented by main loop, so ENDIF is executed next
                    self.pc_modified_by_operation = True
                    return
            target_pc += 1
        raise RuntimeError("ELSE without matching ENDIF.")

    def op_ENDIF(self):
        # ENDIF is a marker, no specific action other than being a jump target.
        # PC will be incremented by the main loop.
        pass

    def op_LOOP(self):
        # Mark the start of the loop for ENDLOOP and CONTINUE.
        # We push the current PC (address of LOOP instruction) onto a control flow stack.
        self._log_debug(f"LOOP instruction at PC={self.pc}. Pushing {{'type': 'LOOP_START', 'pc': {self.pc}}} to control_flow_stack.")
        self.control_flow_stack.append({'type': 'LOOP_START', 'pc': self.pc})
        # PC will be incremented by the main loop to enter the loop body.

    def op_CBREAK(self): # Conditional Break
        condition_type, condition_value = self._pop_any()
        if condition_type != 'I':
            raise TypeError("CBREAK condition must be an integer (boolean).")

        if condition_value != 0: # True, so break
            # Find matching ENDLOOP
            scan_pc = self.pc + 1 # Start scanning from instruction after CBREAK
            temp_nesting = 0
            found_endloop = False
            
            while scan_pc < len(self.programInst):
                instr_name = self.programInst[scan_pc][0]
                if instr_name == 'LOOP':
                    temp_nesting += 1
                elif instr_name == 'ENDLOOP':
                    if temp_nesting == 0: # This ENDLOOP matches our current CBREAK's loop level
                        # Set PC to instruction AFTER this ENDLOOP
                        self.pc = scan_pc + 1 
                        self.pc_modified_by_operation = True
                        found_endloop = True
                        break
                    else: # This ENDLOOP belongs to an inner, nested loop
                        temp_nesting -= 1
                scan_pc += 1
            
            if not found_endloop:
                raise RuntimeError("CBREAK without matching ENDLOOP or loop structure error.")

            # Clean up the control_flow_stack for the loop being exited.
            # CBREAK exits the innermost loop it's part of, so its LOOP_START marker should be at the top.
            if self.control_flow_stack and self.control_flow_stack[-1]['type'] == 'LOOP_START':
                self.control_flow_stack.pop() # Pop the LOOP_START of the broken loop
            else:
                # This signifies a problem, as CBREAK should be within a loop
                # context that has placed its marker on the control_flow_stack.
                self._log_debug("Critical Warning: CBREAK executed but control_flow_stack was empty or its top was not a LOOP_START marker. This could indicate a prior issue.")
            
            return # PC is set to after ENDLOOP, control_flow_stack adjusted. Main run loop will continue from new PC.
        
        # If condition_value is 0 (false), do nothing. 
        # PC will be incremented by the main run loop to the next instruction.


    def op_CONTINUE(self):
        # Jump to the beginning of the current (innermost) loop.
        # The beginning is the instruction *after* the LOOP instruction.
        if not self.control_flow_stack:
            raise RuntimeError("CONTINUE without active LOOP.")

        loop_start_info = None
        for i in range(len(self.control_flow_stack) - 1, -1, -1):
            if self.control_flow_stack[i]['type'] == 'LOOP_START':
                loop_start_info = self.control_flow_stack[i]
                break
        
        if not loop_start_info:
            raise RuntimeError("CONTINUE found no LOOP_START on control_flow_stack.")

        self.pc = loop_start_info['pc'] # PC of the LOOP instruction. Main loop will increment it.
                                        # So effectively jumps to instruction *after* LOOP.
                                        # No, it should jump TO the LOOP instruction itself, which then proceeds.
                                        # The run loop increments PC *after* instruction execution.
                                        # So, setting PC to loop_start_info['pc'] means LOOP will be re-executed.
                                        # This might be okay if LOOP itself doesn't have side effects other than marking.
                                        # Or, it should be loop_start_info['pc'] and LOOP does nothing on re-entry if already marked.
                                        # Let's set it to loop_start_info['pc'] - 1 so after increment it's the LOOP instr.
                                        # No, set to loop_start_info['pc'] directly. The LOOP instruction should be idempotent or simply a marker.

        self.pc = loop_start_info['pc'] # The run() loop will execute this LOOP instruction next, then increment PC.
        self.pc_modified_by_operation = True
    def op_ENDLOOP(self):
        # Jump back to the corresponding LOOP instruction.
        if not self.control_flow_stack or self.control_flow_stack[-1]['type'] != 'LOOP_START':
            raise RuntimeError("ENDLOOP without matching LOOP or malformed control_flow_stack.")
        
        loop_start_info = self.control_flow_stack.pop() # Remove this loop's mark
        self._log_debug(f"ENDLOOP at PC={self.pc}. Popped loop_start_info: {loop_start_info}. Jumping to PC={loop_start_info['pc']}.")
        self.pc = loop_start_info['pc'] # Jump to the LOOP instruction itself.
                                        # The run loop will execute LOOP, then increment PC to enter body.
        self.pc_modified_by_operation = True

    # --- Expansión de memoria ---
    # In class StackMachine:
    def op_GROW(self):
        num_bytes_type, num_bytes = self._pop_any()
        if num_bytes_type != 'I':
            raise TypeError("GROW expects an integer (number of bytes) on stack.")
        if num_bytes < 0:
            raise ValueError("Cannot grow memory by a negative amount.")

        base_address_of_new_block = len(self.memory) # This is current_size before growth
        
        try:
            self.memory.extend(bytearray(num_bytes))
        except MemoryError: # It's good practice to catch potential MemoryError during extend
            current_total_size = len(self.memory) # Get current size before erroring
            raise MemoryError(f"Failed to grow memory by {num_bytes} bytes. Current total size: {current_total_size}")
        
        # Push ONLY the base address of the newly allocated block
        self.stack.append(('I', base_address_of_new_block)) 
        
        self._log_debug(f"Memory grown by {num_bytes} bytes. Base of new block: {base_address_of_new_block}, New total size: {len(self.memory)}. Pushed base address of new block.")


    # --- Entrada/salida ---
    def op_PRINTI(self):
        val_type, value = self._pop_any()
        if val_type != 'I':
            raise TypeError(f"PRINTI requires an integer, got {val_type}")
        print(f"[bold dark_green][OUTPUT][/bold dark_green] {int(value)}")

    def op_PRINTF(self):
        val_type, value = self._pop_any()
        if val_type != 'F':
            raise TypeError(f"PRINTF requires a float, got {val_type}")
        print(f"[bold dark_green][OUTPUT][/bold dark_green] {float(value)}")

    def op_PRINTB(self): # Prints byte as integer value, or as char? "PRINTB ; Imprimir el elemento superior de la pila" (value presented as integer)
        val_type, value = self._pop_any()
        if val_type != 'I': # Bytes are usually represented as integers 0-255
            raise TypeError(f"PRINTB requires an integer (representing a byte), got {val_type}")
        # Assuming it prints the integer value of the byte.
        # If it should print as a character: print(chr(int(value)))
        print(f"[bold dark_green][OUTPUT][/bold dark_green] {int(value)}")

    # --- Acceso a memoria ---
    # PEEKI, POKEI, PEEKF, POKEF, PEEKB, POKEB 
    
    def op_PEEKI(self): # Address is on stack
        """Read 4-byte integer from memory at address (little-endian)"""
        address = self._pop_int()
        if address < 0 or address + self.INT_SIZE > len(self.memory):
            raise IndexError(f"PEEKI: Memory access out of bounds. Address: {address}, Memory size: {len(self.memory)}")
        
        # Read 4 bytes in little-endian order
        bytes_data = self.memory[address:address + self.INT_SIZE]
        value = int.from_bytes(bytes_data, byteorder='little', signed=True)
        self.stack.append(('I', value))
        self._log_debug(f"PEEKI: Read integer {value} from address {address}")

    def op_POKEI(self): # Value, then Address on stack
        """Write 4-byte integer to memory at address (little-endian)"""
        value = self._pop_int()  # El valor está en el tope de la pila
        address = self._pop_int()  # La dirección está debajo del valor
        
        if address < 0 or address + self.INT_SIZE > len(self.memory):
            raise IndexError(f"POKEI: Memory access out of bounds. Address: {address}, Memory size: {len(self.memory)}")
        
        # Write 4 bytes in little-endian order
        bytes_data = value.to_bytes(self.INT_SIZE, byteorder='little', signed=True)
        self.memory[address:address + self.INT_SIZE] = bytes_data
        self._log_debug(f"POKEI: Wrote integer {value} to address {address}")


    def op_PEEKF(self): # Address is on stack
        """Read 4-byte float from memory at address (little-endian)"""
        import struct
        address = self._pop_int()
        
        if address < 0 or address + self.FLOAT_SIZE > len(self.memory):
            raise IndexError(f"PEEKF: Memory access out of bounds. Address: {address}, Memory size: {len(self.memory)}")
        
        # Read 4 bytes and convert to float using IEEE 754 format
        bytes_data = self.memory[address:address + self.FLOAT_SIZE]
        value = struct.unpack('<f', bytes_data)[0]  # '<f' = little-endian float
        self.stack.append(('F', value))
        self._log_debug(f"PEEKF: Read float {value} from address {address}")

    def op_POKEF(self): # Value, then Address on stack
        """Write 4-byte float to memory at address (little-endian)"""
        import struct
        value = self._pop_float()  # El valor está en el tope de la pila
        address = self._pop_int()  # La dirección está debajo del valor
        
        if address < 0 or address + self.FLOAT_SIZE > len(self.memory):
            raise IndexError(f"POKEF: Memory access out of bounds. Address: {address}, Memory size: {len(self.memory)}")
        
        # Convert float to 4 bytes using IEEE 754 format
        bytes_data = struct.pack('<f', value)  # '<f' = little-endian float
        self.memory[address:address + self.FLOAT_SIZE] = bytes_data
        self._log_debug(f"POKEF: Wrote float {value} to address {address}")

    def op_PEEKB(self): # Address is on stack
        """Read 1 byte from memory at address"""
        address = self._pop_int()
        
        if address < 0 or address >= len(self.memory):
            raise IndexError(f"PEEKB: Memory access out of bounds. Address: {address}, Memory size: {len(self.memory)}")
        
        value = self.memory[address]
        self.stack.append(('I', value))  # Bytes are represented as integers
        self._log_debug(f"PEEKB: Read byte {value} from address {address}")

    def op_POKEB(self): # Value, then Address on stack
        """Write 1 byte to memory at address"""
        value = self._pop_int()  # El valor está en el tope de la pila
        address = self._pop_int()  # La dirección está debajo del valor
        
        if address < 0 or address >= len(self.memory):
            raise IndexError(f"POKEB: Memory access out of bounds. Address: {address}, Memory size: {len(self.memory)}")
        
        if value < 0 or value > 255:
            raise ValueError(f"POKEB: Byte value must be 0-255, got {value}")
        
        self.memory[address] = value
        self._log_debug(f"POKEB: Wrote byte {value} to address {address}")